"""
Simple GPT Processor v1.0.0 - Упрощённая архитектура без паттернов

Архитектура:
┌─────────────────────────────────────────────────────┐
│              SIMPLE GPT PROCESSOR v1.0              │
├─────────────────────────────────────────────────────┤
│                                                     │
│  1. Schema Extraction (локально, 0 tokens)          │
│     → Типы колонок, уникальные значения             │
│                                                     │
│  2. GPT-4o генерирует Pandas код (ВСЕГДА)           │
│     → Без классификации, без паттернов              │
│                                                     │
│  3. Execute + Self-Correction (до 3 попыток)        │
│                                                     │
│  4. POST-VALIDATION                                 │
│     → GPT проверяет релевантность ответа            │
│     → Если нет → retry с уточнением                 │
│                                                     │
└─────────────────────────────────────────────────────┘

Преимущества:
- Нет ограничений паттернов
- GPT понимает любые запросы
- Self-correction при ошибках
- Post-validation для качества
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from openai import AsyncOpenAI
import os
import time
import logging
import re
import ast

from .schema_extractor import SchemaExtractor, get_schema_extractor

logger = logging.getLogger(__name__)


def format_number_for_sheets(value):
    """Format number for Google Sheets (comma as decimal separator for Russian locale)"""
    if isinstance(value, float):
        if value == int(value):
            return int(value)  # 480.0 -> 480
        return str(round(value, 2)).replace('.', ',')
    return value


def format_data_for_sheets(data):
    """Recursively format data for Google Sheets"""
    if isinstance(data, list):
        return [format_data_for_sheets(item) for item in data]
    elif isinstance(data, dict):
        return {k: format_data_for_sheets(v) for k, v in data.items()}
    else:
        return format_number_for_sheets(data)




def clean_explanation_text(text: str) -> str:
    """Clean explanation text from weird formatting."""
    if not text:
        return text

    import re

    # Replace tabs
    text = text.replace('\t', ' ')

    # Fix СтрокаN -> Строка N:
    text = re.sub(r'Строка(\d+)', r'Строка \1:', text)
    # Fix Строка N without colon
    text = re.sub(r'Строка (\d+)(?!:)', r'Строка \1:', text)
    # Fix double colons
    text = text.replace('::', ':')

    # Fix СтрокаWord (wrong format) -> just Word
    # Pattern: Строка followed by Cyrillic word (not number) = AI mistake
    text = re.sub(r'Строка([А-Яа-яЁё][А-Яа-яЁёA-Za-z0-9_]*)', r'\1', text)

    # Remove equals: Продукт='X' -> Продукт: X
    text = re.sub(r"(\w+)='([^']+)'", r'\1: \2', text)
    text = re.sub(r'(\w+)=([^,\n\s]+)', r'\1: \2', text)

    # Clean lines
    lines = text.split('\n')
    cleaned = []
    for line in lines:
        line = line.strip()
        while '  ' in line:
            line = line.replace('  ', ' ')
        cleaned.append(line)

    text = '\n'.join(cleaned)
    while '\n\n\n' in text:
        text = text.replace('\n\n\n', '\n\n')

    return text.strip()

class SimpleGPTProcessor:
    """
    Упрощённый процессор на базе GPT-4o.
    Всё через LLM, без паттернов и классификации.
    """

    MODEL = "gpt-4o"  # Best quality
    MAX_RETRIES = 2

    # Безопасность: разрешённые модули
    ALLOWED_IMPORTS = {'pandas', 'pd', 'numpy', 'np', 'datetime', 'timedelta', 're', 'math'}

    # Запрещённые паттерны
    FORBIDDEN_PATTERNS = [
        r'\bexec\b', r'\beval\b', r'\bcompile\b',
        r'\b__\w+__\b', r'\bopen\b', r'\bfile\b',
        r'\bos\b', r'\bsys\b', r'\bsubprocess\b',
        r'\brequests\b', r'\burllib\b', r'\bsocket\b', r'\bpickle\b',
    ]

    SYSTEM_PROMPT = """Ты эксперт-аналитик данных. Твоя задача - помогать с данными.

ВЫБЕРИ ФОРМАТ ОТВЕТА:

1. Если нужен АНАЛИЗ ДАННЫХ (посчитать, найти, сравнить, показать) -> Напиши Python код
2. Если это УТОЧНЯЮЩИЙ ВОПРОС (что значит? почему? объясни) -> Ответь текстом БЕЗ кода

ДЛЯ ТЕКСТОВОГО ОТВЕТА (без кода):
```python
result = None
explanation = "Твой текстовый ответ здесь"
```

ДЛЯ АНАЛИЗА ДАННЫХ (с кодом):
ПРАВИЛА:
1. DataFrame уже загружен в переменную `df`
2. Используй ТОЛЬКО pandas, numpy, datetime, math
3. Результат сохрани в переменную `result`
4. ОБЯЗАТЕЛЬНО создай переменную `explanation` с ЧЁТКИМ СТРУКТУРИРОВАННЫМ ответом
5. НЕ используй print(), просто присвой результат
6. Обрабатывай NaN значения (dropna() или fillna())
7. Для чисел: pd.to_numeric(df[col], errors='coerce')
8. ВАЖНО: Для explanation НЕ используй тройные кавычки! Используй обычные строки с + для конкатенации
9. ВАЖНО: НЕ конвертируй в числа колонки: телефон, phone, id, код, артикул, номер, инн, паспорт, счет - это ТЕКСТ!

КРИТИЧНО - БЕЗОПАСНАЯ РАБОТА С NaN:
- ВСЕГДА проверяй pd.notna(value) перед int() или форматированием
- Для подсчёта используй: int(col.sum()) ТОЛЬКО после dropna()
- Безопасное преобразование: int(val) if pd.notna(val) else 0
- Для вывода чисел: f"{val:.0f}" только если pd.notna(val)
- НИКОГДА не делай int() на значении которое может быть NaN!

КРИТИЧНО - КОНКРЕТНЫЕ ПРИМЕРЫ:
- При любом анализе ВСЕГДА показывай КОНКРЕТНЫЕ примеры из данных
- НЕ ПРОСТО "найдено 21 записей" - покажи КАКИЕ ИМЕННО записи (первые 3-5)
- Для каждой аномалии/проблемы показывай: номер строки, значения ключевых колонок
- Пользователь должен ВИДЕТЬ конкретные данные, а не абстрактные числа
- Формат примера: "Строка 15: Товар='Молоко', Количество=-5"

КРИТИЧНО - ФОРМАТ explanation:
- ПЕРВАЯ СТРОКА = ПРЯМОЙ ОТВЕТ на вопрос
- Используй ПРОСТУЮ НУМЕРАЦИЮ для списков: "1.", "2.", "3."
- НЕ используй слово "Строка" - просто номер и точка!
- Формат записи: f"{i}. {row['Продукт']}, {row['Количество']} шт, {row['Цена']} руб"
- ВСЕ данные одной записи на ОДНОЙ строке!
- НЕ используй = или кавычки в выводе
- НЕ разбивай одну запись на несколько строк!

ПРИМЕР ПРАВИЛЬНОГО ФОРМАТА:
explanation = "Корректная выручка - когда выручка > 0 и равна цена * количество.\n\n"
explanation += "Всего корректных: 101 из 200\n\n"
explanation += "Примеры:\n"
for i, (idx, row) in enumerate(correct_rows.head(3).iterrows(), 1):
    explanation += f"{i}. {row['Продукт']}, {row['Количество']} шт, {row['Цена']} руб\n"
# Результат:
# "1. Рюкзак, 12 шт, 4999 руб"
# "2. Кружка, 5 шт, 500 руб"

ШАБЛОНЫ explanation (БЕЗ ТРОЙНЫХ КАВЫЧЕК!):

1. Для "кто лучший/самый продуктивный":
explanation = "Самый продуктивный: Иванов\n"
explanation += "Сумма: 1,417,500 руб.\n"
explanation += "Сделок: 14\n"
explanation += "\nРейтинг:\n"
explanation += "1. Иванов — 1,417,500 руб.\n"
explanation += "2. Петров — 1,106,490 руб.\n"

2. Для СРАВНЕНИЯ:
explanation = "Сравнение: Январь vs Февраль\n\n"
explanation += "Январь: 500,000 руб.\n"
explanation += "Февраль: 650,000 руб.\n"
explanation += "Рост: +150,000 руб. (+30%)\n"
explanation += "\nВывод: Февраль показал рост"

3. Для "сколько/какая сумма":
explanation = "Результат: 1,500,000 руб.\n"
explanation += "Записей: 45 из 50\n"
explanation += "Доля от общего: 35%"

4. Для ЗАМЕНЫ данных:
# Замена значений в колонке
df["Город"] = df["Город"].replace("Омск", "Лондон")
result = df
explanation = "Заменено: Омск → Лондон\n"
explanation += f"Изменено строк: {(df['Город'] == 'Лондон').sum()}"''

5. Для АНАЛИЗА АНОМАЛИЙ (проверь данные, найди ошибки, что не так):
# Используй простую нумерацию! Каждая запись на ОДНОЙ строке!
explanation = "Найдены аномалии:\n\n"
explanation += "Отрицательные значения (5 записей):\n"
for i, (idx, row) in enumerate(negative_rows.head(3).iterrows(), 1):
    explanation += f"  {i}. {row['Товар']}, количество {row['Количество']}\n"
explanation += "\nПустые значения (12 записей):\n"
for i, (idx, row) in enumerate(empty_rows.head(3).iterrows(), 1):
    explanation += f"  {i}. {row['Товар']}, пустое поле {col}\n"
explanation += f"\nИтого проблем: {total_issues}"

ФОРМАТ (КРИТИЧНО):
- НЕ используй ** или * (markdown)
- НЕ используй # для заголовков
- Формат метрики: "Название: значение"
- Числа с разделителем тысяч: 1,417,500
- Пустая строка между блоками

ПЕРВАЯ СТРОКА explanation ВСЕГДА ОТВЕЧАЕТ НА ВОПРОС НАПРЯМУЮ!

ПРИМЕРЫ КОДА:

Запрос: "Топ 5 товаров по сумме"
```python
# Группируем по товарам и суммируем
product_col = None
sum_col = None
for col in df.columns:
    col_lower = col.lower()
    if any(x in col_lower for x in ['товар', 'product', 'название', 'name', 'наименование']):
        product_col = col
    if any(x in col_lower for x in ['сумм', 'sum', 'total', 'amount']):
        sum_col = col

if product_col and sum_col:
    top5 = df.groupby(product_col)[sum_col].sum().sort_values(ascending=False).head(5)
    result = top5.to_dict()
    explanation = f"Топ 5 товаров по сумме:\n\n"
    for i, (name, val) in enumerate(top5.items(), 1):
        explanation += f"{i}. {name}: {val:,.0f} руб.\n"
    total = top5.sum()
    explanation += f"\nИтого топ-5: {total:,.0f} руб."
else:
    result = "Не найдены колонки с товарами и суммами"
    explanation = result
```

Запрос: "Количество заказов по городам" или "Сколько заказов в каждом городе"
```python
# Находим колонку с городами
city_col = None
for col in df.columns:
    col_lower = col.lower()
    if any(x in col_lower for x in ['город', 'city', 'регион', 'region', 'локац']):
        city_col = col
        break

if city_col:
    city_counts = df[city_col].value_counts().sort_values(ascending=False)
    result = city_counts.to_dict()
    explanation = f"Количество заказов по городам:\n\n"
    for city, count in city_counts.head(10).items():
        explanation += f"• {city}: {count}\n"
    if len(city_counts) > 10:
        explanation += f"• ...и ещё {len(city_counts) - 10} городов\n"
    explanation += f"\nВсего городов: {len(city_counts)}"
else:
    result = "Колонка с городами не найдена"
    explanation = result
```

Запрос: "Продажи по менеджерам" или "Сумма по менеджерам"
```python
# Находим колонку с менеджерами
manager_col = None
sum_col = None
for col in df.columns:
    col_lower = col.lower()
    if any(x in col_lower for x in ['менеджер', 'manager', 'продавец', 'seller', 'сотрудник']):
        manager_col = col
    if any(x in col_lower for x in ['сумм', 'sum', 'total', 'amount']):
        sum_col = col

if manager_col and sum_col:
    sales = df.groupby(manager_col)[sum_col].sum().sort_values(ascending=False)
    result = sales.to_dict()
    explanation = f"Продажи по менеджерам:\n\n"
    for manager, total in sales.items():
        pct = (total / sales.sum()) * 100
        explanation += f"• {manager}: {total:,.0f} руб. ({pct:.1f}%)\n"
    explanation += f"\nОбщая сумма: {sales.sum():,.0f} руб."
else:
    result = "Не найдены колонки с менеджерами и суммами"
    explanation = result
```


Запрос: "Какой менеджер самый продуктивный"
```python
# Находим колонку с менеджерами и суммами
manager_col = None
sum_col = None
for col in df.columns:
    col_lower = col.lower()
    if any(x in col_lower for x in ['менеджер', 'manager', 'продавец']):
        manager_col = col
    if any(x in col_lower for x in ['сумм', 'sum', 'total', 'amount']):
        sum_col = col

sales = df.groupby(manager_col)[sum_col].agg(['sum', 'count']).sort_values('sum', ascending=False)
sales['avg_check'] = sales['sum'] / sales['count']
leader = sales.index[0]
leader_sum = sales.loc[leader, 'sum']
leader_count = sales.loc[leader, 'count']
leader_avg = sales.loc[leader, 'avg_check']
total = sales['sum'].sum()
leader_share = (leader_sum / total) * 100

result = leader

# Формируем ЧЁТКИЙ ответ БЕЗ markdown
explanation = f"Самый продуктивный: {leader}\n"
explanation += f"Сумма: {leader_sum:,.0f} руб.\n"
explanation += f"Сделок: {leader_count:.0f}\n"
explanation += f"Средний чек: {leader_avg:,.0f} руб.\n\n"
explanation += "Рейтинг:\n"
for i, (name, row) in enumerate(sales.head(5).iterrows(), 1):
    explanation += f"{i}. {name} — {row['sum']:,.0f} руб.\n"
explanation += f"\nДоля от общего: {leader_share:.1f}%\n"
if len(sales) > 1:
    second_sum = sales.iloc[1]['sum']
    gap = leader_sum - second_sum
    gap_pct = (gap / second_sum) * 100
    explanation += f"Отрыв от 2-го: +{gap:,.0f} руб. (+{gap_pct:.0f}%)\n"
explanation += f"\nВывод: {leader} лидирует по объёму продаж"
```

Запрос: "почему?" (после вопроса о продуктивности)
```python
sales = df.groupby('Менеджер')['Сумма'].sum().sort_values(ascending=False)
counts = df.groupby('Менеджер').size()
leader = sales.index[0]
leader_sum = sales.iloc[0]
leader_count = counts[leader]
second = sales.index[1] if len(sales) > 1 else None
explanation = f"{leader} лидирует потому что:\n\n"
explanation += "Ключевые факты:\n"
explanation += f"• Общая сумма продаж: {leader_sum:,.0f} руб.\n"
explanation += f"• Количество сделок: {leader_count}\n"
if second:
    diff = leader_sum - sales.iloc[1]
    pct = diff / sales.iloc[1] * 100
    explanation += f"• Разница с {second}: +{diff:,.0f} руб. (+{pct:.0f}%)\n"
explanation += f"\nВысокие показатели обеспечены большим объёмом и/или крупными сделками."
result = sales.to_dict()
```

Запрос: "Сколько продаж у Иванова"
```python
ivanov = df[df['Менеджер'].str.contains('Иванов', case=False, na=False)]
result = len(ivanov)
total = ivanov['Сумма'].sum()
avg = ivanov['Сумма'].mean()
explanation = f"Продаж: {result}\n\n"
explanation += "Детали:\n"
explanation += f"• Общая сумма: {total:,.0f} руб.\n"
explanation += f"• Средний чек: {avg:,.0f} руб.\n"
```

Запрос: "Максимальный заказ" или "Какой самый крупный заказ"
```python
# Находим строку с максимальной суммой
sum_col = 'Сумма'  # Определи название колонки с суммой автоматически
if sum_col not in df.columns:
    # Ищем колонку с суммой по названию
    for col in df.columns:
        if any(x in col.lower() for x in ['сумм', 'sum', 'total', 'amount', 'цена', 'price']):
            sum_col = col
            break

numeric_col = pd.to_numeric(df[sum_col], errors='coerce')
max_idx = numeric_col.idxmax()
max_row = df.loc[max_idx]
max_value = numeric_col.max()

# Найти название товара/продукта
product_col = None
for col in df.columns:
    if any(x in col.lower() for x in ['товар', 'product', 'название', 'name', 'наименование']):
        product_col = col
        break

product_name = max_row[product_col] if product_col else "N/A"

result = {"max_value": max_value, "product": product_name, "row": max_row.to_dict()}
explanation = f"Максимальный заказ: {max_value:,.0f} руб.\n\n"
explanation += f"Товар: {product_name}\n"
explanation += f"Детали заказа:\n"
for col, val in max_row.items():
    if pd.notna(val) and str(val).strip():
        explanation += f"• {col}: {val}\n"
```

Запрос: "Минимальный заказ" или "Какой самый маленький заказ"
```python
# Находим строку с минимальной суммой
sum_col = 'Сумма'
if sum_col not in df.columns:
    for col in df.columns:
        if any(x in col.lower() for x in ['сумм', 'sum', 'total', 'amount', 'цена', 'price']):
            sum_col = col
            break

numeric_col = pd.to_numeric(df[sum_col], errors='coerce')
# Фильтруем NaN и нули
valid_mask = (numeric_col > 0) & numeric_col.notna()
min_idx = numeric_col[valid_mask].idxmin()
min_row = df.loc[min_idx]
min_value = numeric_col[valid_mask].min()

product_col = None
for col in df.columns:
    if any(x in col.lower() for x in ['товар', 'product', 'название', 'name', 'наименование']):
        product_col = col
        break

product_name = min_row[product_col] if product_col else "N/A"

result = {"min_value": min_value, "product": product_name, "row": min_row.to_dict()}
explanation = f"Минимальный заказ: {min_value:,.0f} руб.\n\n"
explanation += f"Товар: {product_name}\n"
explanation += f"Детали заказа:\n"
for col, val in min_row.items():
    if pd.notna(val) and str(val).strip():
        explanation += f"• {col}: {val}\n"
```


Запрос: "Найди цену товара по артикулу из справочника" (VLOOKUP между листами)
```python
# reference_df содержит справочник с ценами
# df - основная таблица с артикулами

# Находим ключевые колонки
lookup_col_df = None  # Колонка для поиска в df
lookup_col_ref = None  # Колонка-ключ в reference_df
result_col_ref = None  # Колонка с результатом в reference_df

for col in df.columns:
    if any(x in col.lower() for x in ['артикул', 'sku', 'код', 'id', 'article']):
        lookup_col_df = col
        
for col in reference_df.columns:
    if any(x in col.lower() for x in ['артикул', 'sku', 'код', 'id', 'article']):
        lookup_col_ref = col
    if any(x in col.lower() for x in ['цена', 'price', 'стоимость', 'cost']):
        result_col_ref = col

if lookup_col_df and lookup_col_ref and result_col_ref:
    # Merge - аналог VLOOKUP
    merged = df.merge(
        reference_df[[lookup_col_ref, result_col_ref]], 
        left_on=lookup_col_df, 
        right_on=lookup_col_ref, 
        how='left'
    )
    
    # Считаем статистику
    found = merged[result_col_ref].notna().sum()
    not_found = merged[result_col_ref].isna().sum()
    
    result = merged
    explanation = f"Цены подтянуты из справочника

"
    explanation += f"Найдено: {found} из {len(df)}
"
    if not_found > 0:
        explanation += f"Не найдено: {not_found} артикулов
"
        missing = merged[merged[result_col_ref].isna()][lookup_col_df].head(5).tolist()
        explanation += f"Примеры ненайденных: {missing}"
else:
    result = "Не удалось найти подходящие колонки для VLOOKUP"
    explanation = result
```

Запрос: "Добавь названия категорий из второго листа" (VLOOKUP по ID)
```python
# Определяем колонки для связи
id_col_df = None
id_col_ref = None
name_col_ref = None

for col in df.columns:
    if any(x in col.lower() for x in ['категория_id', 'category_id', 'cat_id', 'id_категории']):
        id_col_df = col

for col in reference_df.columns:
    if any(x in col.lower() for x in ['id', 'код', 'категория_id']):
        id_col_ref = col
    if any(x in col.lower() for x in ['название', 'name', 'наименование', 'категория']):
        name_col_ref = col

if id_col_df and id_col_ref and name_col_ref:
    # Создаём словарь для быстрого поиска
    lookup_dict = reference_df.set_index(id_col_ref)[name_col_ref].to_dict()
    
    # Применяем VLOOKUP через map
    df['Категория'] = df[id_col_df].map(lookup_dict)
    
    found = df['Категория'].notna().sum()
    result = df
    explanation = f"Добавлены названия категорий

"
    explanation += f"Найдено: {found} из {len(df)}
"
    explanation += f"Новая колонка: Категория"
else:
    result = "Не удалось определить колонки для связи"
    explanation = result
```

Запрос: "Проверь данные на ошибки" или "Найди аномалии" или "Что не так с данными"
```python
# Анализ данных на аномалии с КОНКРЕТНЫМИ примерами
explanation = "Анализ данных:\n\n"
issues_found = []

# 1. Проверка на отрицательные значения в числовых колонках
for col in df.columns:
    if df[col].dtype in ['int64', 'float64']:
        # Безопасно проверяем отрицательные
        numeric_col = pd.to_numeric(df[col], errors='coerce')
        negative_mask = numeric_col < 0
        negative_rows = df[negative_mask]
        if len(negative_rows) > 0:
            issues_found.append(('negative', col, negative_rows))

# 2. Проверка на пустые значения
for col in df.columns:
    empty_mask = df[col].isna() | (df[col].astype(str).str.strip() == '')
    empty_rows = df[empty_mask]
    if len(empty_rows) > 0:
        issues_found.append(('empty', col, empty_rows))

# 3. Проверка на дубликаты
duplicates = df[df.duplicated(keep=False)]
if len(duplicates) > 0:
    issues_found.append(('duplicates', 'all', duplicates))

# Формируем ответ с КОНКРЕТНЫМИ примерами
total_issues = 0
for issue_type, col, rows in issues_found:
    count = len(rows)
    total_issues += count

    if issue_type == 'negative':
        explanation += f"Отрицательные в '{col}': {count} записей\n"
        for idx, row in rows.head(3).iterrows():
            # idx+2 потому что +1 для 0-based и +1 для заголовка
            val = row[col]
            if pd.notna(val):
                explanation += f"   Строка {idx+2}: {col}={val}\n"
    elif issue_type == 'empty':
        explanation += f"Пустые в '{col}': {count} записей\n"
        for idx, row in rows.head(3).iterrows():
            # Показываем первую непустую колонку для идентификации
            first_val = next((row[c] for c in df.columns if pd.notna(row[c])), 'N/A')
            explanation += f"   Строка {idx+2}: пусто (ID: {first_val})\n"
    elif issue_type == 'duplicates':
        explanation += f"Дубликаты: {count} записей\n"
        for idx, row in rows.head(3).iterrows():
            vals = ', '.join(str(row[c])[:20] for c in df.columns[:3] if pd.notna(row[c]))
            explanation += f"   Строка {idx+2}: {vals}\n"
    explanation += "\n"

if total_issues == 0:
    explanation = "Данные проверены - аномалий не найдено!\n"
    explanation += f"Всего строк: {len(df)}\n"
    explanation += f"Колонок: {len(df.columns)}"
else:
    explanation += f"Итого проблемных записей: {total_issues}"

result = {"issues": total_issues, "details": issues_found}
```


Возвращай ТОЛЬКО код внутри ```python ... ``````python ... ```
"""

    VALIDATION_PROMPT = """Ты проверяешь качество ответа на запрос пользователя.

ЗАПРОС ПОЛЬЗОВАТЕЛЯ: {query}

РЕЗУЛЬТАТ: {result}

ЗАДАЧА: Ответь одним словом:
- "OK" - если результат отвечает на запрос пользователя
- "BAD" - если результат НЕ отвечает на запрос (неправильный тип данных, не та информация, пустой ответ)

Примеры:
- Запрос "какие продукты" → Результат ["Телефон", "Ноутбук"] → OK
- Запрос "какие продукты" → Результат 5 (число) → BAD (нужен список, не число)
- Запрос "сколько продаж" → Результат 42 → OK
- Запрос "сколько продаж" → Результат ["продукт1", "продукт2"] → BAD (нужно число)

Ответь ТОЛЬКО "OK" или "BAD":
"""

    # Ключевые слова для действий над данными (не анализ, а модификация)
    SORT_KEYWORDS = ['отсортируй', 'сортируй', 'сортировка', 'упорядочь', 'упорядочи', 'sort', 'order by']
    SORT_DESC_KEYWORDS = ['убыван', 'desc', 'z-a', 'я-а', 'больш к меньш', 'от большего', 'по убыванию']
    SORT_ASC_KEYWORDS = ['возраст', 'asc', 'a-z', 'а-я', 'меньш к больш', 'от меньшего', 'по возрастанию']

    # Freeze keywords
    FREEZE_KEYWORDS = ['заморозь', 'заморозить', 'закрепи', 'закрепить', 'freeze', 'pin']
    UNFREEZE_KEYWORDS = ['разморозь', 'разморозить', 'открепи', 'открепить', 'unfreeze', 'unpin']

    # Format keywords
    FORMAT_BOLD_KEYWORDS = ['жирн', 'bold', 'выдели жирным']
    FORMAT_HEADER_KEYWORDS = ['заголов', 'header', 'шапк', 'первую строку']
    FORMAT_COLOR_KEYWORDS = ['цвет', 'color', 'покрась', 'закрась']

    # Chart keywords
    CHART_KEYWORDS = ['диаграмм', 'график', 'chart', 'graph', 'построй', 'визуализ', 'plot']
    CHART_TYPES = {
        # Line charts
        'линейн': 'LINE', 'line': 'LINE', 'линия': 'LINE', 'тренд': 'LINE',
        # Bar charts (horizontal)
        'горизонтальн': 'BAR', 'bar': 'BAR',
        # Column charts (vertical bars) - default
        'столбч': 'COLUMN', 'column': 'COLUMN', 'столбик': 'COLUMN', 'гистограмм': 'COLUMN',
        # Pie charts
        'кругов': 'PIE', 'pie': 'PIE', 'пирог': 'PIE', 'долей': 'PIE', 'процент': 'PIE', 'долями': 'PIE', 'доли': 'PIE',
        # Area charts
        'область': 'AREA', 'area': 'AREA', 'заливк': 'AREA',
        # Scatter plots
        'точечн': 'SCATTER', 'scatter': 'SCATTER', 'разброс': 'SCATTER', 'корреляц': 'SCATTER',
        # Combo charts
        'комбинир': 'COMBO', 'combo': 'COMBO', 'смешан': 'COMBO',
    }

    # Conditional formatting keywords
    CONDITIONAL_FORMAT_KEYWORDS = ['условн', 'conditional', 'где больше', 'где меньше', 'где равно',
                                    'больше чем', 'меньше чем', 'если больше', 'если меньше',
                                    'красным где', 'зелёным где', 'зеленым где', 'жёлтым где', 'желтым где',
                                    'выдели где', 'покрась где', 'отметь где',
                                    # Additional patterns for color-based formatting
                                    'покрась красн', 'покрась зелен', 'покрась жёлт', 'покрась желт',
                                    'выдели красн', 'выдели зелен', 'выдели жёлт', 'выдели желт',
                                    'если цена', 'если сумма', 'если значение',
                                    'красным ячейки', 'зелёным ячейки', 'зеленым ячейки',
                                    'пустые значения', 'пустые ячейки', 'желтым пуст', 'жёлтым пуст']

    # Color scale / gradient keywords (MUST be checked BEFORE conditional formatting)
    COLOR_SCALE_KEYWORDS = ['цветовая шкала', 'color scale', 'градиент', 'gradient',
                            'тепловая карта', 'heatmap', 'heat map',
                            'от красного к зелёному', 'от красного к зеленому',
                            'от зелёного к красному', 'от зеленого к красному',
                            'шкала цвет', 'раскрась по значени', 'покрась по значени',
                            'условное форматирование по', 'форматирование по',
                            'высокой ценой зеленым', 'высокой ценой зелёным',
                            'низкой ценой красным', 'наоборот цвет', 'инвертируй цвет',
                            'зеленым цветом, а', 'зелёным цветом, а',
                            'красным цветом, а', 'поменяй цвета']

    # Convert to numbers keywords
    CONVERT_TO_NUMBERS_KEYWORDS = ['преобразуй в числ', 'преобразовать в числ', 'конвертируй в числ',
                                    'конвертировать в числ', 'сделай числ', 'формат числ',
                                    'из текста в числ', 'текст в числ', 'convert to number',
                                    'to number format', 'числовой формат', 'на числовой',
                                    'в числовой', 'измени формат', 'сменить формат',
                                    'текстовой формат на', 'текстовый формат на']

    # Color scale presets
    COLOR_SCALE_PRESETS = {
        'red_yellow_green': {
            'min_color': {'red': 0.96, 'green': 0.8, 'blue': 0.8},    # Light red
            'mid_color': {'red': 1, 'green': 0.95, 'blue': 0.8},       # Light yellow
            'max_color': {'red': 0.8, 'green': 0.92, 'blue': 0.8}      # Light green
        },
        'green_yellow_red': {
            'min_color': {'red': 0.8, 'green': 0.92, 'blue': 0.8},     # Light green
            'mid_color': {'red': 1, 'green': 0.95, 'blue': 0.8},       # Light yellow
            'max_color': {'red': 0.96, 'green': 0.8, 'blue': 0.8}      # Light red
        },
        'white_to_blue': {
            'min_color': {'red': 1, 'green': 1, 'blue': 1},            # White
            'mid_color': {'red': 0.8, 'green': 0.9, 'blue': 1},        # Light blue
            'max_color': {'red': 0.4, 'green': 0.6, 'blue': 0.9}       # Blue
        },
        'white_to_green': {
            'min_color': {'red': 1, 'green': 1, 'blue': 1},            # White
            'mid_color': {'red': 0.85, 'green': 0.95, 'blue': 0.85},   # Light green
            'max_color': {'red': 0.6, 'green': 0.85, 'blue': 0.6}      # Green
        }
    }

    # Pivot table / grouping keywords
    PIVOT_KEYWORDS = ['сводн', 'pivot', 'группир', 'group by', 'агрегир', 'итоги по', 'суммы по',
                      'по категори', 'по менеджер', 'по регион', 'по месяц', 'по год',
                      'разбивка по', 'в разрезе']

    # Aggregation functions
    AGG_FUNCTIONS = {
        'сумм': 'sum', 'sum': 'sum', 'итог': 'sum',
        'средн': 'mean', 'avg': 'mean', 'average': 'mean',
        'количеств': 'count', 'count': 'count', 'число': 'count',
        'макс': 'max', 'max': 'max', 'максимум': 'max',
        'мин': 'min', 'min': 'min', 'минимум': 'min'
    }

    # Synonyms for value columns (business terms -> likely column names)
    VALUE_COLUMN_SYNONYMS = {
        'продаж': ['сумма', 'сумм', 'выручка', 'revenue', 'sales', 'amount', 'total'],
        'доход': ['сумма', 'выручка', 'прибыль', 'revenue', 'income'],
        'выручк': ['сумма', 'продажи', 'revenue', 'sales'],
        'оборот': ['сумма', 'выручка', 'revenue'],
        'прибыл': ['прибыль', 'маржа', 'profit', 'margin'],
        'затрат': ['себестоимость', 'расходы', 'cost', 'expenses'],
        'расход': ['себестоимость', 'затраты', 'cost', 'expenses'],
    }


    # Data cleaning keywords
    CLEAN_KEYWORDS = ['очист', 'clean', 'удали дублик', 'remove duplicate', 'дубликат',
                      'удали пуст', 'remove empty', 'пустые строк', 'empty row',
                      'заполни пуст', 'fill empty', 'fill blank', 'fillna',
                      'убери пробел', 'trim', 'strip', 'пробелы',
                      'нормализ', 'normalize', 'стандартиз',
                      # Additional patterns
                      'убери дублик', 'убери повтор', 'убери пуст', 'убери строки',
                      'удали повтор', 'удали строки']

    # CSV Split / Text-to-columns keywords
    CSV_SPLIT_KEYWORDS = ['разбей', 'разбить', 'split', 'разделить', 'разделяй', 
                          'по ячейкам', 'text to columns', 'текст по столбцам',
                          'csv', 'по колонкам', 'по столбцам', 'распарси', 'парсинг',
                          'раздели данные', 'разбей данные', 'разбей csv', 'разбей текст']

    # Cleaning operation types
    CLEAN_OPERATIONS = {
        'duplicate': ['дублик', 'duplicate', 'повтор', 'одинаков', 'дубл'],
        'empty_rows': ['пуст', 'empty', 'blank', 'nan', 'null'],
        'trim': ['пробел', 'trim', 'strip', 'whitespace'],
        'fill': ['заполн', 'fill', 'замен', 'replace'],
    }

    # Data validation keywords
    VALIDATION_KEYWORDS = ['валидац', 'validation', 'выпадающ', 'dropdown', 'список',
                           'ограничь', 'restrict', 'допустим',
                           'разрешённ', 'allowed', 'выбор из', 'select from']

    # Highlight keywords - MUST be checked BEFORE filter keywords
    HIGHLIGHT_KEYWORDS = ['выдели', 'выделить', 'подсвети', 'подсветить', 'подсветь',
                          'highlight', 'mark', 'покрась', 'покрасить', 'раскрась',
                          'отметь', 'отметить', 'пометь', 'пометить']

    # Highlight colors mapping (hex) - more variations
    HIGHLIGHT_COLORS = {
        # Red
        'красн': '#FF6B6B', 'red': '#FF6B6B',
        # Green
        'зелен': '#69DB7C', 'зелён': '#69DB7C', 'green': '#69DB7C',
        # Yellow
        'жёлт': '#FFE066', 'желт': '#FFE066', 'yellow': '#FFE066',
        # Orange
        'оранж': '#FFA94D', 'orange': '#FFA94D',
        # Blue
        'синий': '#74C0FC', 'синим': '#74C0FC', 'blue': '#74C0FC',
        # Light blue
        'голуб': '#99E9F2',
        # Purple
        'фиолет': '#DA77F2', 'purple': '#DA77F2',
        # Pink
        'розов': '#F783AC', 'pink': '#F783AC',
    }

    # Smart color detection by context (status/condition -> color)
    CONTEXT_COLORS = {
        # Negative -> red
        'отмен': '#FF6B6B', 'отказ': '#FF6B6B', 'ошибк': '#FF6B6B',
        'проблем': '#FF6B6B', 'возврат': '#FF6B6B', 'просроч': '#FF6B6B',
        # Positive -> green
        'оплач': '#69DB7C', 'выполн': '#69DB7C', 'доставл': '#69DB7C',
        'завершен': '#69DB7C', 'успеш': '#69DB7C', 'активн': '#69DB7C',
        # Pending -> orange
        'ожидан': '#FFA94D', 'в процесс': '#FFA94D', 'обрабат': '#FFA94D',
        # VIP -> purple
        'vip': '#DA77F2', 'важн': '#DA77F2', 'приорит': '#DA77F2',
    }

    # Filter keywords
    FILTER_KEYWORDS = ['фильтр', 'filter', 'отфильтр', 'покажи только', 'show only',
                       'где ', 'where ', 'выбери где', 'select where', 'строки где',
                       'rows where', 'отбери', 'выбери строки']

    # Filter operators
    FILTER_OPERATORS = {
        '>=': ['>=', '≥', 'больше или равно', 'не меньше'],
        '<=': ['<=', '≤', 'меньше или равно', 'не больше'],
        '!=': ['!=', '≠', '<>', 'не равно', 'не равен', 'кроме'],
        '>': ['>', 'больше', 'выше', 'more than', 'greater', 'более'],
        '<': ['<', 'меньше', 'ниже', 'less than', 'lower', 'менее'],
        '==': ['=', '==', 'равно', 'равен', 'equals', 'is'],
        'contains': ['содержит', 'contains', 'включает', 'includes'],
        'startswith': ['начинается', 'starts with', 'начинает'],
        'endswith': ['заканчивается', 'ends with', 'оканчивается'],
        'empty': ['пуст', 'empty', 'null', 'nan', 'нет значения'],
        'not_empty': ['не пуст', 'not empty', 'заполнен', 'есть значение'],
    }
    # Conversational/follow-up keywords - respond with text, not code
    CONVERSATIONAL_KEYWORDS = [
        'почему', 'why', 'зачем', 'объясни', 'explain', 'расскажи',
        'как ты', 'how did you', 'на основании чего', 'откуда',
        'уточни', 'подробнее', 'more details', 'что значит',
        'а если', 'what if', 'а как', 'можешь ли', 'could you',
        'не понял', "don't understand", 'поясни', 'clarify'
    ]

    # Deep analysis prompt - for thorough anomaly detection
    ANALYSIS_SYSTEM_PROMPT = """Ты аналитик данных. Найди ВСЕ аномалии из запроса.

ФОРМАТ ОТВЕТА - СТРОГО:
```
explanation = "Найдены аномалии:\n\n"
explanation += "ПУСТЫЕ ЦЕНЫ (3 записи):\n"
explanation += "- Строка 5: Наушники\n"
explanation += "- Строка 6: Игровая приставка\n"
explanation += "- Строка 10: Кофта\n\n"
explanation += "ОТРИЦАТЕЛЬНОЕ КОЛИЧЕСТВО (3 записи):\n"
explanation += "- Строка 10: Кофта, кол-во = -2\n"
explanation += "- Строка 17: Пауэрбанк, кол-во = -2\n"
```

ПРАВИЛА:
1. Каждая запись ОДНОЙ строкой после "- "
2. НЕТ табов, только пробелы
3. Формат: "- Строка N: Название, проблема = значение"
4. Между категориями одна пустая строка
5. НИКОГДА не разбивай одну запись на несколько строк!
6. Проверь ВСЕ типы аномалий из запроса пользователя
"""

    # Conversational prompt - for follow-up questions

    # Keywords that trigger deep analysis mode
    DEEP_ANALYSIS_KEYWORDS = [
        'аномал', 'anomal', 'ошибк', 'error', 'проблем', 'problem',
        'странн', 'weird', 'некорректн', 'incorrect', 'неправильн',
        'провер', 'check', 'валидац', 'validat', 'качеств', 'quality',
        'найди ошибк', 'find error', 'что не так', 'what wrong',
        'дубликат', 'duplicate', 'повтор', 'repeat'
    ]

    CONVERSATIONAL_PROMPT = """Ты помощник-аналитик. Пользователь задаёт уточняющий вопрос по предыдущему анализу.

ИСТОРИЯ:
{history}

ТЕКУЩИЙ ВОПРОС: {query}

ЗАДАЧА: Ответь на вопрос развёрнуто и понятно:
- Объясни своё рассуждение
- Приведи конкретные примеры из данных если нужно
- Если нужен дополнительный анализ, скажи что можешь сделать

Отвечай как умный ассистент, а не как робот. Будь готов обсудить результаты.

ОТВЕТ:"""



    # Color keywords for conditional formatting
    CONDITION_COLORS = {
        'красн': {'red': 1, 'green': 0.8, 'blue': 0.8},      # Light red
        'red': {'red': 1, 'green': 0.8, 'blue': 0.8},
        'зелен': {'red': 0.85, 'green': 0.95, 'blue': 0.85}, # Light green
        'green': {'red': 0.85, 'green': 0.95, 'blue': 0.85},
        'жёлт': {'red': 1, 'green': 1, 'blue': 0.7},         # Light yellow
        'желт': {'red': 1, 'green': 1, 'blue': 0.7},
        'yellow': {'red': 1, 'green': 1, 'blue': 0.7},
        'оранж': {'red': 1, 'green': 0.9, 'blue': 0.8},      # Light orange
        'orange': {'red': 1, 'green': 0.9, 'blue': 0.8},
        'синий': {'red': 0.85, 'green': 0.9, 'blue': 1},     # Light blue
        'blue': {'red': 0.85, 'green': 0.9, 'blue': 1},
        'голуб': {'red': 0.85, 'green': 0.95, 'blue': 1},    # Light cyan
    }

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            # Try loading from .env
            from pathlib import Path
            env_path = Path(__file__).parent.parent.parent / ".env"
            if env_path.exists():
                with open(env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.startswith("OPENAI_API_KEY="):
                            api_key = line.split("=", 1)[1].strip()
                            os.environ["OPENAI_API_KEY"] = api_key
                            break

        self.client = AsyncOpenAI(api_key=api_key)
        self.schema_extractor = get_schema_extractor()

    def _detect_sort_action(self, query: str, column_names: List[str]) -> Optional[Dict[str, Any]]:
        """
        Определяет, является ли запрос командой сортировки.
        Возвращает параметры сортировки или None.
        """
        query_lower = query.lower()

        # Проверяем наличие ключевых слов сортировки
        is_sort_query = any(kw in query_lower for kw in self.SORT_KEYWORDS)
        if not is_sort_query:
            return None

        logger.info(f"[SimpleGPT] Sort action detected: {query}")

        # Определяем порядок сортировки
        is_descending = any(kw in query_lower for kw in self.SORT_DESC_KEYWORDS)
        is_ascending = any(kw in query_lower for kw in self.SORT_ASC_KEYWORDS)

        # По умолчанию - по возрастанию, если явно не указано убывание
        sort_order = "DESCENDING" if is_descending and not is_ascending else "ASCENDING"

        # Ищем название колонки в запросе
        sort_column = None
        sort_column_index = None

        # Нормализуем названия колонок для поиска
        for idx, col_name in enumerate(column_names):
            col_lower = col_name.lower()
            # Проверяем точное вхождение или частичное
            if col_lower in query_lower or col_name in query:
                sort_column = col_name
                sort_column_index = idx
                logger.info(f"[SimpleGPT] Found sort column: '{col_name}' at index {idx}")
                break

        # Если колонка не найдена, пробуем найти по частичному совпадению
        if not sort_column:
            for idx, col_name in enumerate(column_names):
                # Разбиваем название колонки на слова
                col_words = col_name.lower().split()
                for word in col_words:
                    if len(word) > 2 and word in query_lower:
                        sort_column = col_name
                        sort_column_index = idx
                        logger.info(f"[SimpleGPT] Found sort column by partial match: '{col_name}' at index {idx}")
                        break
                if sort_column:
                    break

        if not sort_column:
            logger.warning(f"[SimpleGPT] Sort column not found in query. Available columns: {column_names}")
            return None

        return {
            "action_type": "sort",
            "column_name": sort_column,
            "column_index": sort_column_index,
            "sort_order": sort_order,
            "message": f"Сортировка по колонке '{sort_column}' ({('по убыванию' if sort_order == 'DESCENDING' else 'по возрастанию')})"
        }

    def _detect_freeze_action(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Определяет, является ли запрос командой заморозки строк/столбцов.
        """
        query_lower = query.lower()

        # Check for unfreeze first
        is_unfreeze = any(kw in query_lower for kw in self.UNFREEZE_KEYWORDS)
        if is_unfreeze:
            logger.info(f"[SimpleGPT] Unfreeze action detected: {query}")
            return {
                "action_type": "freeze",
                "freeze_rows": 0,
                "freeze_columns": 0,
                "message": "Закрепление снято"
            }

        # Check for freeze
        is_freeze = any(kw in query_lower for kw in self.FREEZE_KEYWORDS)
        if not is_freeze:
            return None

        logger.info(f"[SimpleGPT] Freeze action detected: {query}")

        # Determine what to freeze
        freeze_rows = 0
        freeze_columns = 0

        # Check for row freeze
        if any(word in query_lower for word in ['строк', 'строку', 'row', 'первую', 'шапку', 'заголов']):
            # Try to find number
            import re
            numbers = re.findall(r'(\d+)\s*(?:строк|строку|row)', query_lower)
            if numbers:
                freeze_rows = int(numbers[0])
            else:
                freeze_rows = 1  # Default to 1 row (header)

        # Check for column freeze
        if any(word in query_lower for word in ['столб', 'колонк', 'column', 'первый столб', 'первую колонк']):
            import re
            numbers = re.findall(r'(\d+)\s*(?:столб|колонк|column)', query_lower)
            if numbers:
                freeze_columns = int(numbers[0])
            else:
                freeze_columns = 1  # Default to 1 column

        # If nothing specific mentioned, freeze first row
        if freeze_rows == 0 and freeze_columns == 0:
            freeze_rows = 1

        message_parts = []
        if freeze_rows > 0:
            message_parts.append(f"{freeze_rows} строк" if freeze_rows > 1 else "первая строка")
        if freeze_columns > 0:
            message_parts.append(f"{freeze_columns} столбцов" if freeze_columns > 1 else "первый столбец")

        return {
            "action_type": "freeze",
            "freeze_rows": freeze_rows,
            "freeze_columns": freeze_columns,
            "message": f"Закреплено: {', '.join(message_parts)}"
        }

    def _detect_format_action(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Определяет, является ли запрос командой форматирования.
        """
        query_lower = query.lower()

        # Check for bold formatting
        is_bold = any(kw in query_lower for kw in self.FORMAT_BOLD_KEYWORDS)
        is_header = any(kw in query_lower for kw in self.FORMAT_HEADER_KEYWORDS)

        if not (is_bold or is_header):
            return None

        logger.info(f"[SimpleGPT] Format action detected: {query}")

        # Determine format type
        format_type = "bold_header" if (is_bold and is_header) or is_header else "bold"

        # Check for color
        color = None
        if any(kw in query_lower for kw in self.FORMAT_COLOR_KEYWORDS):
            # Try to detect color
            color_map = {
                'красн': '#FF0000', 'red': '#FF0000',
                'синий': '#0000FF', 'blue': '#0000FF',
                'зелен': '#00FF00', 'green': '#00FF00',
                'желт': '#FFFF00', 'yellow': '#FFFF00',
                'оранж': '#FFA500', 'orange': '#FFA500',
                'серый': '#808080', 'сер': '#808080', 'gray': '#808080', 'grey': '#808080',
            }
            for color_word, color_code in color_map.items():
                if color_word in query_lower:
                    color = color_code
                    break

        return {
            "action_type": "format",
            "format_type": format_type,
            "target_row": 1,  # First row (header)
            "bold": is_bold or is_header,
            "background_color": color,
            "message": f"Заголовки отформатированы" + (f" (цвет: {color})" if color else "")
        }

    async def _gpt_select_chart_columns(self, query: str, column_names: List[str], df: pd.DataFrame) -> Dict[str, Any]:
        """
        Использует GPT для умного выбора колонок диаграммы на основе запроса пользователя.
        """
        # Analyze column types
        column_info = []
        for idx, col in enumerate(column_names):
            if idx >= len(df.columns):
                continue
            col_data = df.iloc[:, idx]

            # Determine type
            col_type = "text"
            try:
                numeric_data = pd.to_numeric(col_data, errors='coerce')
                non_null_ratio = numeric_data.notna().sum() / len(numeric_data) if len(numeric_data) > 0 else 0
                if non_null_ratio > 0.5:
                    col_type = "number"
            except:
                pass

            # Check for date
            col_lower = col.lower()
            if any(d in col_lower for d in ['дата', 'date', 'месяц', 'month', 'год', 'year']):
                col_type = "date"

            # Get sample values
            samples = col_data.dropna().head(3).tolist()
            column_info.append(f"{idx}. {col} ({col_type}): {samples}")

        columns_desc = "\n".join(column_info)

        # Check for duplicates in potential X columns
        unique_counts = {}
        for idx, col in enumerate(column_names):
            if idx < len(df.columns):
                unique_count = df.iloc[:, idx].nunique()
                total_count = len(df)
                unique_counts[col] = f"{unique_count} уникальных из {total_count}"

        unique_info = "\n".join([f"  {col}: {info}" for col, info in unique_counts.items()])

        prompt = f"""Пользователь хочет создать диаграмму.
Запрос: "{query}"

Доступные колонки:
{columns_desc}

Количество уникальных значений:
{unique_info}

Ответь ТОЛЬКО в формате JSON:
{{
  "x_column": <индекс колонки для оси X>,
  "y_columns": [<индексы колонок для оси Y>],
  "title": "<заголовок>",
  "needs_aggregation": <true/false>,
  "aggregation": "<sum/mean/count/null>"
}}

ВАЖНО - АГРЕГАЦИЯ:
- Если X колонка имеет ПОВТОРЯЮЩИЕСЯ значения (уникальных < всего) - needs_aggregation=true
- Например: 5 категорий на 200 строк = НУЖНА агрегация (sum/mean)
- "по категории и выручке" = сумма выручки по каждой категории
- aggregation: "sum" для суммы, "mean" для среднего, "count" для количества
- Если уникальных значений = количеству строк - needs_aggregation=false

Правила выбора колонок:
- X ось: категория или дата (ПО ЧЕМУ группируем)
- Y ось: числовые колонки (ЧТО измеряем)
- title должен отражать запрос"""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=200
            )

            result_text = response.choices[0].message.content.strip()
            # Extract JSON from response
            import json
            if "```" in result_text:
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]

            result = json.loads(result_text)
            logger.info(f"[SimpleGPT] GPT chart selection: {result}")
            return result
        except Exception as e:
            logger.error(f"[SimpleGPT] GPT chart selection failed: {e}")
            return None

    def _detect_chart_action(self, query: str, column_names: List[str], df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        Определяет, является ли запрос командой создания диаграммы.
        Использует GPT для умного выбора колонок.
        """
        query_lower = query.lower()

        # Check for chart keywords
        is_chart_query = any(kw in query_lower for kw in self.CHART_KEYWORDS)
        if not is_chart_query:
            return None

        logger.info(f"[SimpleGPT] Chart action detected: {query}")

        # Determine chart type
        chart_type = 'COLUMN'  # Default
        for type_keyword, type_value in self.CHART_TYPES.items():
            if type_keyword in query_lower:
                chart_type = type_value
                logger.info(f"[SimpleGPT] Chart type detected: {type_value}")
                break

        # Mark that we need GPT selection (will be done in async process method)
        return {
            "action_type": "chart_pending",
            "chart_type": chart_type,
            "query": query,
            "column_names": column_names,
            "df_len": len(df),
            "needs_gpt_selection": True
        }

    async def _finalize_chart_action(self, pending_action: Dict[str, Any], column_names: List[str], df: pd.DataFrame) -> Dict[str, Any]:
        """
        Завершает создание диаграммы с помощью GPT выбора колонок.
        Поддерживает агрегацию данных для повторяющихся категорий.
        """
        query = pending_action["query"]
        chart_type = pending_action["chart_type"]

        # Get GPT selection
        gpt_result = await self._gpt_select_chart_columns(query, column_names, df)

        if gpt_result:
            x_idx = gpt_result.get("x_column", 0)
            y_indices = gpt_result.get("y_columns", [1])
            title = gpt_result.get("title", "Диаграмма")
            needs_aggregation = gpt_result.get("needs_aggregation", False)
            aggregation = gpt_result.get("aggregation", "sum")
        else:
            # Fallback to simple logic
            x_idx = 0
            y_indices = [1] if len(column_names) > 1 else [0]
            title = "Диаграмма"
            needs_aggregation = False
            aggregation = "sum"

        # Validate indices
        x_idx = min(x_idx, len(column_names) - 1)
        y_indices = [min(i, len(column_names) - 1) for i in y_indices if i < len(column_names)]
        if not y_indices:
            y_indices = [1] if len(column_names) > 1 else [0]

        # For PIE charts, use only one Y column
        if chart_type == 'PIE':
            y_indices = y_indices[:1]

        # Handle aggregation if needed
        aggregated_data = None
        if needs_aggregation and x_idx < len(df.columns):
            try:
                x_col_name = column_names[x_idx]
                y_col_names = [column_names[i] for i in y_indices if i < len(column_names)]

                # Create aggregation
                agg_df = df.copy()
                x_col = agg_df.iloc[:, x_idx]

                # Build aggregation dict
                agg_dict = {}
                for y_idx in y_indices:
                    if y_idx < len(df.columns):
                        y_col = df.columns[y_idx]
                        # Convert to numeric
                        agg_df[y_col] = pd.to_numeric(agg_df.iloc[:, y_idx], errors='coerce')
                        if aggregation == "mean":
                            agg_dict[y_col] = 'mean'
                        elif aggregation == "count":
                            agg_dict[y_col] = 'count'
                        else:
                            agg_dict[y_col] = 'sum'

                # Group and aggregate
                grouped = agg_df.groupby(agg_df.iloc[:, x_idx]).agg(agg_dict).reset_index()

                # Prepare data for frontend (list of lists with headers)
                headers = [x_col_name] + y_col_names
                rows = []
                for _, row in grouped.iterrows():
                    row_data = [row.iloc[0]]  # X value
                    for i, y_col in enumerate(y_col_names):
                        val = row.iloc[i + 1]
                        # Round numeric values
                        if pd.notna(val):
                            row_data.append(round(float(val), 2))
                        else:
                            row_data.append(0)
                    rows.append(row_data)

                aggregated_data = {
                    "headers": headers,
                    "rows": rows,
                    "aggregation_type": aggregation
                }

                logger.info(f"[SimpleGPT] Aggregated data: {len(rows)} groups from {len(df)} rows")

            except Exception as e:
                logger.error(f"[SimpleGPT] Aggregation failed: {e}")
                needs_aggregation = False

        chart_spec = {
            "chart_type": chart_type,
            "title": title,
            "x_column_index": x_idx,
            "x_column_name": column_names[x_idx] if x_idx < len(column_names) else column_names[0],
            "y_column_indices": y_indices,
            "y_column_names": [column_names[i] for i in y_indices if i < len(column_names)],
            "row_count": len(df),
            "col_count": len(column_names),
            "needs_aggregation": needs_aggregation,
            "aggregated_data": aggregated_data
        }

        chart_type_names = {
            'LINE': 'линейный график',
            'BAR': 'горизонтальную гистограмму',
            'COLUMN': 'столбчатую диаграмму',
            'PIE': 'круговую диаграмму',
            'AREA': 'диаграмму с областями',
            'SCATTER': 'точечную диаграмму',
            'COMBO': 'комбинированный график'
        }

        message = f"Создаю {chart_type_names.get(chart_type, 'диаграмму')}: {title}"

        return {
            "action_type": "chart",
            "chart_spec": chart_spec,
            "message": message
        }

    def _detect_conditional_format_action(self, query: str, column_names: List[str], df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        Определяет, является ли запрос командой условного форматирования.
        Примеры:
        - "выдели красным где сумма больше 10000"
        - "зелёным где прибыль положительная"
        - "условное форматирование: жёлтым пустые ячейки"
        """
        query_lower = query.lower()

        # Check for conditional format keywords
        is_conditional = any(kw in query_lower for kw in self.CONDITIONAL_FORMAT_KEYWORDS)
        if not is_conditional:
            return None

        logger.info(f"[SimpleGPT] Conditional format action detected: {query}")

        # Detect color
        format_color = {'red': 1, 'green': 1, 'blue': 0.7}  # Default yellow
        color_name = "жёлтый"
        for color_kw, color_value in self.CONDITION_COLORS.items():
            if color_kw in query_lower:
                format_color = color_value
                color_name = color_kw
                break

        # Find column mentioned in query - exact word match first
        target_column = None
        target_column_index = None

        # Split query into words for exact matching
        query_words = set(query_lower.split())

        logger.info(f"[SimpleGPT] Conditional format: looking for column in query: '{query}', columns: {column_names}")

        # First pass: exact match (column name is a word in query)
        for idx, col_name in enumerate(column_names):
            col_lower = col_name.lower().strip()
            if len(col_lower) < 2:
                continue
            if col_lower in query_words:
                target_column = col_name
                target_column_index = idx
                logger.info(f"[SimpleGPT] Found exact match: column '{col_name}' at index {idx}")
                break

        # Second pass: column name is a substring of a query word
        if not target_column:
            for idx, col_name in enumerate(column_names):
                col_lower = col_name.lower().strip()
                if len(col_lower) < 2:
                    continue
                for word in query_words:
                    if len(word) >= len(col_lower) and (word.startswith(col_lower) or col_lower in word):
                        target_column = col_name
                        target_column_index = idx
                        logger.info(f"[SimpleGPT] Found partial match: column '{col_name}' in word '{word}' at index {idx}")
                        break
                if target_column:
                    break

        # Third pass: match by word stems (handle Russian declensions)
        if not target_column:
            # Common word stems: query word stem → column name stems
            stem_mappings = {
                'цен': ['цена', 'price', 'стоимость', 'cost'],
                'сумм': ['сумма', 'sum', 'total', 'итого'],
                'прибыл': ['прибыль', 'profit', 'доход'],
                'количеств': ['количество', 'qty', 'кол-во', 'шт'],
                'остат': ['остаток', 'остатки', 'stock', 'balance'],
                'продаж': ['продажи', 'sales', 'выручка'],
                'расход': ['расходы', 'expenses', 'затраты'],
                'зарплат': ['зарплата', 'salary', 'оклад'],
                'скидк': ['скидка', 'discount'],
                'налог': ['налог', 'tax', 'ндс', 'vat'],
                'марж': ['маржа', 'margin', 'наценка'],
            }
            for query_word in query_words:
                for stem, col_variants in stem_mappings.items():
                    if query_word.startswith(stem):
                        # Found a stem match in query, now look for column
                        for idx, col_name in enumerate(column_names):
                            col_lower = col_name.lower().strip()
                            if any(variant in col_lower for variant in col_variants) or col_lower.startswith(stem):
                                target_column = col_name
                                target_column_index = idx
                                logger.info(f"[SimpleGPT] Found stem match: query '{query_word}' → column '{col_name}' at index {idx}")
                                break
                        if target_column:
                            break
                if target_column:
                    break

        # If no column found, try to find numeric column
        if not target_column:
            for idx, col_name in enumerate(column_names):
                if idx < len(df.columns):
                    try:
                        numeric_data = pd.to_numeric(df.iloc[:, idx], errors='coerce')
                        if numeric_data.notna().sum() / len(numeric_data) > 0.5:
                            target_column = col_name
                            target_column_index = idx
                            break
                    except:
                        pass

        # Detect condition type and value
        condition_type = "NUMBER_GREATER"  # Default - must match sheets-api.js expected types
        condition_value = 0  # Default: highlight values > 0

        # Patterns for conditions
        import re

        # "больше X" / "> X"
        greater_match = re.search(r'(?:больше|>|более)\s*(?:чем\s*)?(\d+(?:[.,]\d+)?)', query_lower)
        if greater_match:
            condition_type = "NUMBER_GREATER"
            condition_value = float(greater_match.group(1).replace(',', '.'))

        # "меньше X" / "< X"
        less_match = re.search(r'(?:меньше|<|менее)\s*(?:чем\s*)?(\d+(?:[.,]\d+)?)', query_lower)
        if less_match:
            condition_type = "NUMBER_LESS"
            condition_value = float(less_match.group(1).replace(',', '.'))

        # "равно X" / "= X"
        equal_match = re.search(r'(?:равно|=|равен)\s*(\d+(?:[.,]\d+)?)', query_lower)
        if equal_match:
            condition_type = "NUMBER_EQ"
            condition_value = float(equal_match.group(1).replace(',', '.'))

        # "пусто" / "пустые"
        if any(w in query_lower for w in ['пуст', 'empty', 'blank', 'нет данных']):
            condition_type = "BLANK"
            condition_value = None

        # "не пусто" / "заполнено"
        if any(w in query_lower for w in ['не пуст', 'not empty', 'заполнен', 'есть данные']):
            condition_type = "NOT_BLANK"
            condition_value = None

        # "отрицательн" / "убыток"
        if any(w in query_lower for w in ['отрицательн', 'убыт', 'negative', 'минус']):
            condition_type = "NUMBER_LESS"
            condition_value = 0

        # "положительн" / "прибыль"
        if any(w in query_lower for w in ['положительн', 'прибыл', 'positive', 'плюс']):
            condition_type = "NUMBER_GREATER"
            condition_value = 0

        # Build the conditional format rule
        rule = {
            "column_index": target_column_index if target_column_index is not None else 0,
            "column_name": target_column or column_names[0] if column_names else "A",
            "condition_type": condition_type,
            "condition_value": condition_value,
            "format_color": format_color
        }

        # Generate message
        condition_text = ""
        if condition_type == "NUMBER_GREATER":
            condition_text = f"> {condition_value}"
        elif condition_type == "NUMBER_LESS":
            condition_text = f"< {condition_value}"
        elif condition_type == "NUMBER_EQ":
            condition_text = f"= {condition_value}"
        elif condition_type == "BLANK":
            condition_text = "пустые"
        elif condition_type == "NOT_BLANK":
            condition_text = "непустые"

        message = f"Условное форматирование: {target_column or 'колонка'} {condition_text} → {color_name}"

        return {
            "action_type": "conditional_format",
            "rule": rule,
            "message": message
        }

    def _detect_pivot_action(self, query: str, column_names: List[str], df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        Определяет, является ли запрос командой создания сводной таблицы.
        Примеры:
        - "сводная по менеджерам"
        - "группировка продаж по регионам"
        - "суммы по категориям"
        """
        query_lower = query.lower()

        # Check for pivot keywords
        is_pivot = any(kw in query_lower for kw in self.PIVOT_KEYWORDS)
        if not is_pivot:
            return None

        logger.info(f"[SimpleGPT] Pivot action detected: {query}")

        # Analyze columns
        numeric_cols = []
        categorical_cols = []

        for idx, col_name in enumerate(column_names):
            if idx >= len(df.columns):
                continue
            col_data = df.iloc[:, idx]

            # Check if numeric
            try:
                numeric_data = pd.to_numeric(col_data, errors='coerce')
                non_null_ratio = numeric_data.notna().sum() / len(numeric_data) if len(numeric_data) > 0 else 0
                if non_null_ratio > 0.5:
                    numeric_cols.append({'name': col_name, 'index': idx})
                    continue
            except:
                pass

            # Otherwise categorical
            unique_count = col_data.nunique()
            if unique_count <= len(col_data) * 0.7:  # Up to 70% unique = categorical
                categorical_cols.append({'name': col_name, 'index': idx})

        logger.info(f"[SimpleGPT] Columns: numeric={[c['name'] for c in numeric_cols]}, categorical={[c['name'] for c in categorical_cols]}")

        # Find grouping column (categorical mentioned in query)
        group_column = None
        for cat in categorical_cols:
            cat_lower = cat['name'].lower()
            if cat_lower in query_lower or cat['name'] in query:
                group_column = cat
                break
            # Partial match - check if column name stem is in query
            for word in cat_lower.split():
                if len(word) > 2 and word in query_lower:
                    group_column = cat
                    break
                # Check if word stem (first 4+ chars) is in query for Russian word forms
                if len(word) >= 4:
                    word_stem = word[:max(4, len(word) - 2)]  # Get stem (at least 4 chars)
                    if word_stem in query_lower:
                        group_column = cat
                        logger.info(f"[SimpleGPT] Found pivot column by stem: '{word_stem}' in '{word}' -> {cat['name']}")
                        break
            if group_column:
                break

        # If not found, use first categorical
        if not group_column and categorical_cols:
            group_column = categorical_cols[0]

        # Find value column (numeric mentioned in query or via synonyms)
        value_column = None

        # First, try direct match
        for num in numeric_cols:
            num_lower = num['name'].lower()
            if num_lower in query_lower or num['name'] in query:
                value_column = num
                logger.info(f"[SimpleGPT] Found value column by direct match: {num['name']}")
                break
            for word in num_lower.split():
                if len(word) > 2 and word in query_lower:
                    value_column = num
                    logger.info(f"[SimpleGPT] Found value column by word match: {num['name']}")
                    break
            if value_column:
                break

        # If not found, try synonyms (e.g., "продажи" -> "Сумма")
        if not value_column:
            for query_term, synonyms in self.VALUE_COLUMN_SYNONYMS.items():
                if query_term in query_lower:
                    # Found a business term in query, look for matching column
                    for num in numeric_cols:
                        num_lower = num['name'].lower()
                        for syn in synonyms:
                            if syn in num_lower or num_lower in syn:
                                value_column = num
                                logger.info(f"[SimpleGPT] Found value column via synonym '{query_term}' -> '{num['name']}'")
                                break
                        if value_column:
                            break
                    if value_column:
                        break

        # Fallback to first numeric column (but skip ID columns)
        if not value_column and numeric_cols:
            for num in numeric_cols:
                # Skip columns that look like IDs
                if num['name'].lower() not in ['id', 'ид', 'номер', 'код', 'index']:
                    value_column = num
                    logger.info(f"[SimpleGPT] Using first non-ID numeric column: {num['name']}")
                    break
            # If all are ID-like, use first one anyway
            if not value_column:
                value_column = numeric_cols[0]

        # Detect aggregation function
        agg_func = 'sum'  # Default
        for kw, func in self.AGG_FUNCTIONS.items():
            if kw in query_lower:
                agg_func = func
                break

        if not group_column or not value_column:
            logger.warning(f"[SimpleGPT] Cannot create pivot: group_column={group_column}, value_column={value_column}")
            return None

        # Create pivot table using pandas
        try:
            pivot_df = df.groupby(df.iloc[:, group_column['index']]).agg({
                df.columns[value_column['index']]: agg_func
            }).reset_index()

            # Rename columns
            pivot_df.columns = [group_column['name'], f"{agg_func.upper()}({value_column['name']})"]

            # Sort by value descending
            pivot_df = pivot_df.sort_values(by=pivot_df.columns[1], ascending=False)

            # Convert to structured data
            pivot_data = {
                "headers": list(pivot_df.columns),
                "rows": format_data_for_sheets(pivot_df.to_dict(orient='records'))
            }

            agg_names = {
                'sum': 'Сумма',
                'mean': 'Среднее',
                'count': 'Количество',
                'max': 'Максимум',
                'min': 'Минимум'
            }

            # Avoid duplication like "Сумма Сумма" when column name matches agg function name
            agg_name = agg_names.get(agg_func, agg_func)
            col_name = value_column['name']
            if agg_name.lower() in col_name.lower() or col_name.lower() in agg_name.lower():
                message = f"Сводная таблица: {col_name} по {group_column['name']}"
            else:
                message = f"Сводная таблица: {agg_name} {col_name} по {group_column['name']}"

            return {
                "action_type": "pivot_table",
                "pivot_data": pivot_data,
                "group_column": group_column['name'],
                "value_column": value_column['name'],
                "agg_func": agg_func,
                "message": message
            }

        except Exception as e:
            logger.error(f"[SimpleGPT] Error creating pivot: {e}")
            return None

    def _detect_csv_split_action(self, query: str, column_names: List[str], df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        Определяет, является ли запрос командой разбиения CSV/текста по ячейкам.
        Примеры:
        - "разбей данные по ячейкам"
        - "раздели csv по столбцам"
        - "text to columns"
        """
        query_lower = query.lower()
        
        # Check for CSV split keywords
        is_csv_split = any(kw in query_lower for kw in self.CSV_SPLIT_KEYWORDS)
        if not is_csv_split:
            return None
        
        logger.info(f"[SimpleGPT] CSV split action detected: {query}")
        logger.info(f"[SimpleGPT] CSV split - df.columns: {df.columns.tolist()}")
        logger.info(f"[SimpleGPT] CSV split - df.shape: {df.shape}")
        logger.info(f"[SimpleGPT] CSV split - df first row: {df.iloc[0].tolist() if len(df) > 0 else 'empty'}")
        
        # Detect delimiter from data
        delimiter = None
        first_row = df.iloc[0, 0] if len(df) > 0 and len(df.columns) > 0 else ''
        first_row_str = str(first_row)
        
        # Check common delimiters
        if ';' in first_row_str:
            delimiter = ';'
        elif ',' in first_row_str:
            delimiter = ','
        elif '	' in first_row_str:
            delimiter = '	'
        elif '|' in first_row_str:
            delimiter = '|'
        
        if not delimiter:
            logger.warning(f"[SimpleGPT] Could not detect delimiter in data")
            return None
        
        logger.info(f"[SimpleGPT] Detected delimiter: '{delimiter}'")
        
        # Split data
        try:
            import io
            # IMPORTANT: column_names contains the FIRST row from Google Sheets
            # which was separated as "headers" by frontend. We need to include it!
            
            # Start with first row (column_names) - it's actually the first data row
            all_data = []
            if column_names and len(column_names) == 1 and delimiter in str(column_names[0]):
                # First row is CSV text in single cell - add it
                all_data.append(str(column_names[0]))
            
            # Add remaining rows from df
            for idx, row in df.iterrows():
                row_str = str(row.iloc[0]) if len(row) > 0 else ''
                all_data.append(row_str)
            
            logger.info(f"[SimpleGPT] CSV split - total rows including header: {len(all_data)}")
            csv_text = chr(10).join(all_data)

            # Parse CSV - first row becomes headers
            split_df = pd.read_csv(io.StringIO(csv_text), sep=delimiter, header=0, dtype=str)

            # Use pandas-extracted headers
            headers = split_df.columns.tolist()
            logger.info(f"[SimpleGPT] CSV split - headers: {headers}")

            # All remaining rows are data
            rows = split_df.fillna('').to_dict('records')
            logger.info(f"[SimpleGPT] CSV split - data rows: {len(rows)}")
            
            structured_data = {
                'headers': headers,
                'rows': rows
            }
            
            message = f"""Данные разбиты по ячейкам

Результат:
• Колонок: {len(headers)}
• Строк данных: {len(rows)}
• Разделитель: '{delimiter}'
• Колонки: {', '.join(headers[:5])}{'...' if len(headers) > 5 else ''}

Нажмите кнопку ниже, чтобы заменить данные в таблице."""
            
            return {
                'structured_data': structured_data,
                'original_rows': len(df),
                'new_rows': len(rows),
                'new_cols': len(headers),
                'delimiter': delimiter,
                'message': message
            }
            
        except Exception as e:
            logger.error(f"[SimpleGPT] CSV split error: {e}")
            return None

    def _detect_clean_action(self, query: str, column_names: List[str], df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        Определяет, является ли запрос командой очистки данных.
        Примеры:
        - "удали дубликаты"
        - "удали пустые строки"
        - "заполни пустые ячейки нулями"
        - "очисти данные"
        """
        query_lower = query.lower()

        # Check for clean keywords
        is_clean = any(kw in query_lower for kw in self.CLEAN_KEYWORDS)
        if not is_clean:
            return None

        logger.info(f"[SimpleGPT] Clean action detected: {query}")

        # Determine operation type
        operations = []

        # Check for duplicate removal
        if any(kw in query_lower for kw in self.CLEAN_OPERATIONS['duplicate']):
            operations.append('remove_duplicates')

        # Check for empty row removal
        if any(kw in query_lower for kw in self.CLEAN_OPERATIONS['empty_rows']):
            # Distinguish between "удали пустые" vs "заполни пустые"
            if any(w in query_lower for w in ['удали', 'убери', 'remove', 'delete']):
                operations.append('remove_empty_rows')
            elif any(w in query_lower for w in ['заполн', 'fill', 'замен']):
                operations.append('fill_empty')

        # Check for trimming whitespace
        if any(kw in query_lower for kw in self.CLEAN_OPERATIONS['trim']):
            operations.append('trim_whitespace')

        # Check for fill operation (if not already detected)
        if 'fill_empty' not in operations and any(kw in query_lower for kw in self.CLEAN_OPERATIONS['fill']):
            operations.append('fill_empty')

        # Default to all common operations if just "очисти данные"
        if not operations and any(w in query_lower for w in ['очисти', 'clean']):
            operations = ['remove_duplicates', 'remove_empty_rows', 'trim_whitespace']

        if not operations:
            return None

        # Detect fill value if applicable
        fill_value = None
        if 'fill_empty' in operations:
            # Check for specific fill values
            import re

            # "нулями" / "0" / "zeros"
            if any(w in query_lower for w in ['нул', 'zero', '0']):
                fill_value = 0
            # "пустой строкой" / ""
            elif any(w in query_lower for w in ['строк', 'string', 'текст']):
                fill_value = ""
            # "средним" / "mean" / "average"
            elif any(w in query_lower for w in ['средн', 'mean', 'average', 'avg']):
                fill_value = "mean"
            # "медианой" / "median"
            elif any(w in query_lower for w in ['медиан', 'median']):
                fill_value = "median"
            # "предыдущим" / "forward fill"
            elif any(w in query_lower for w in ['предыдущ', 'forward', 'ffill', 'последн']):
                fill_value = "ffill"
            # Specific number
            number_match = re.search(r'(\d+(?:[.,]\d+)?)', query_lower)
            if number_match and fill_value is None:
                fill_value = float(number_match.group(1).replace(',', '.'))

            # Default to 0 if not specified
            if fill_value is None:
                fill_value = 0

        # Find target column if specified
        target_column = None
        target_column_index = None

        for idx, col_name in enumerate(column_names):
            col_lower = col_name.lower()
            if col_lower in query_lower or col_name in query:
                target_column = col_name
                target_column_index = idx
                break
            # Partial match
            for word in col_lower.split():
                if len(word) > 2 and word in query_lower:
                    target_column = col_name
                    target_column_index = idx
                    break
            if target_column:
                break

        # Execute cleaning and get preview
        try:
            cleaned_df = df.copy()
            original_rows = len(cleaned_df)
            changes = []

            for op in operations:
                if op == 'remove_duplicates':
                    before = len(cleaned_df)
                    if target_column:
                        cleaned_df = cleaned_df.drop_duplicates(subset=[cleaned_df.columns[target_column_index]])
                    else:
                        cleaned_df = cleaned_df.drop_duplicates()
                    removed = before - len(cleaned_df)
                    if removed > 0:
                        changes.append(f"удалено {removed} дубликатов")

                elif op == 'remove_empty_rows':
                    before = len(cleaned_df)
                    if target_column:
                        cleaned_df = cleaned_df.dropna(subset=[cleaned_df.columns[target_column_index]])
                    else:
                        cleaned_df = cleaned_df.dropna(how='all')
                    removed = before - len(cleaned_df)
                    if removed > 0:
                        changes.append(f"удалено {removed} пустых строк")

                elif op == 'trim_whitespace':
                    # Trim string columns - remove leading/trailing AND multiple internal spaces
                    str_cols = cleaned_df.select_dtypes(include=['object']).columns
                    for col in str_cols:
                        cleaned_df[col] = cleaned_df[col].apply(
                            lambda x: ' '.join(x.split()) if isinstance(x, str) else x
                        )
                    if len(str_cols) > 0:
                        changes.append(f"убраны пробелы в {len(str_cols)} колонках")

                elif op == 'fill_empty':
                    if target_column:
                        col = cleaned_df.columns[target_column_index]
                        empty_count = cleaned_df[col].isna().sum()
                        if fill_value == "mean":
                            cleaned_df[col] = cleaned_df[col].fillna(cleaned_df[col].mean())
                        elif fill_value == "median":
                            cleaned_df[col] = cleaned_df[col].fillna(cleaned_df[col].median())
                        elif fill_value == "ffill":
                            cleaned_df[col] = cleaned_df[col].fillna(method='ffill')
                        else:
                            cleaned_df[col] = cleaned_df[col].fillna(fill_value)
                        if empty_count > 0:
                            changes.append(f"заполнено {empty_count} пустых ячеек в '{target_column}'")
                    else:
                        # Fill all numeric columns
                        num_cols = cleaned_df.select_dtypes(include=[np.number]).columns
                        total_filled = 0
                        for col in num_cols:
                            empty_count = cleaned_df[col].isna().sum()
                            total_filled += empty_count
                            if fill_value == "mean":
                                cleaned_df[col] = cleaned_df[col].fillna(cleaned_df[col].mean())
                            elif fill_value == "median":
                                cleaned_df[col] = cleaned_df[col].fillna(cleaned_df[col].median())
                            elif fill_value == "ffill":
                                cleaned_df[col] = cleaned_df[col].fillna(method='ffill')
                            else:
                                cleaned_df[col] = cleaned_df[col].fillna(fill_value)
                        if total_filled > 0:
                            changes.append(f"заполнено {total_filled} пустых ячеек")

            final_rows = len(cleaned_df)

            # Prepare result data
            cleaned_data = {
                "headers": list(cleaned_df.columns),
                "rows": format_data_for_sheets(cleaned_df.to_dict(orient='records'))
            }

            # Build message
            if changes:
                message = "Очистка данных: " + ", ".join(changes)
            else:
                message = "Данные уже чистые, изменений не требуется"

            return {
                "action_type": "clean_data",
                "operations": operations,
                "fill_value": fill_value,
                "target_column": target_column,
                "original_rows": original_rows,
                "final_rows": final_rows,
                "cleaned_data": cleaned_data,
                "changes": changes,
                "message": message
            }

        except Exception as e:
            logger.error(f"[SimpleGPT] Error cleaning data: {e}")
            return None

    def _detect_validation_action(self, query: str, column_names: List[str], df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        Определяет, является ли запрос командой валидации данных (выпадающий список).
        Примеры:
        - "создай выпадающий список в колонке Статус"
        - "добавь валидацию: только Да/Нет"
        - "ограничь значения в колонке Категория"
        """
        query_lower = query.lower()

        # Check for validation keywords
        is_validation = any(kw in query_lower for kw in self.VALIDATION_KEYWORDS)
        if not is_validation:
            return None

        logger.info(f"[SimpleGPT] Validation action detected: {query}")

        # Find target column
        target_column = None
        target_column_index = None

        for idx, col_name in enumerate(column_names):
            col_lower = col_name.lower()
            if col_lower in query_lower or col_name in query:
                target_column = col_name
                target_column_index = idx
                break
            # Partial match
            for word in col_lower.split():
                if len(word) > 2 and word in query_lower:
                    target_column = col_name
                    target_column_index = idx
                    break
            if target_column:
                break

        # Extract allowed values from query
        allowed_values = []

        # Pattern 1: "только X/Y/Z" or "только X, Y, Z"
        import re
        only_match = re.search(r'только\s+([^.!?]+)', query_lower)
        if only_match:
            values_str = only_match.group(1)
            # Split by / or , or "или"
            values = re.split(r'[/,]|\sили\s|\sor\s', values_str)
            allowed_values = [v.strip() for v in values if v.strip()]

        # Pattern 2: "значения: X, Y, Z" or "варианты: X, Y, Z"
        values_match = re.search(r'(?:значения|варианты|options|values)[:\s]+([^.!?]+)', query_lower)
        if values_match and not allowed_values:
            values_str = values_match.group(1)
            values = re.split(r'[/,]|\sили\s|\sor\s', values_str)
            allowed_values = [v.strip() for v in values if v.strip()]

        # Pattern 3: "Да/Нет" style in query
        if not allowed_values:
            # Look for slash-separated values
            slash_match = re.search(r'([а-яёa-z0-9]+(?:/[а-яёa-z0-9]+)+)', query_lower)
            if slash_match:
                allowed_values = slash_match.group(1).split('/')

        # If still no values and we have a target column, extract unique values from data
        if not allowed_values and target_column and target_column_index is not None:
            try:
                unique_values = df.iloc[:, target_column_index].dropna().unique()
                # Only use if reasonable number of unique values (< 20)
                if len(unique_values) <= 20:
                    allowed_values = [str(v) for v in unique_values]
                    logger.info(f"[SimpleGPT] Auto-extracted {len(allowed_values)} unique values from column")
            except Exception as e:
                logger.warning(f"[SimpleGPT] Could not extract unique values: {e}")

        if not target_column:
            # Try to find first categorical column
            for idx, col_name in enumerate(column_names):
                if idx < len(df.columns):
                    try:
                        unique_count = df.iloc[:, idx].nunique()
                        total_count = len(df)
                        # Categorical if less than 50% unique values and <= 20 unique
                        if unique_count <= 20 and unique_count < total_count * 0.5:
                            target_column = col_name
                            target_column_index = idx
                            if not allowed_values:
                                allowed_values = [str(v) for v in df.iloc[:, idx].dropna().unique()]
                            break
                    except:
                        pass

        if not target_column:
            logger.warning(f"[SimpleGPT] No target column found for validation")
            return None

        if not allowed_values:
            logger.warning(f"[SimpleGPT] No allowed values found for validation")
            return None

        # Capitalize first letter of each value for display
        allowed_values = [v.strip().capitalize() if v.strip() else v for v in allowed_values]

        # Build validation rule
        rule = {
            "column_index": target_column_index,
            "column_name": target_column,
            "validation_type": "ONE_OF_LIST",
            "allowed_values": allowed_values,
            "show_dropdown": True,
            "strict": True  # Reject invalid input
        }

        values_preview = ", ".join(allowed_values[:5])
        if len(allowed_values) > 5:
            values_preview += f" (+{len(allowed_values) - 5})"

        message = f"Валидация для '{target_column}': {values_preview}"

        return {
            "action_type": "data_validation",
            "rule": rule,
            "message": message
        }

    def _detect_highlight_action(self, query: str, column_names: List[str], df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        Определяет, является ли запрос командой выделения строк цветом.
        Примеры:
        - "выдели строки где Сумма > 100000"
        - "подсветь красным отменённые заказы"
        - "отметь зелёным оплаченные"
        """
        query_lower = query.lower()

        # Check for highlight keywords FIRST
        is_highlight = any(kw in query_lower for kw in self.HIGHLIGHT_KEYWORDS)
        if not is_highlight:
            return None

        logger.info(f"[SimpleGPT] Highlight action detected: {query}")

        # Detect color from query - first check explicit colors
        highlight_color = None
        for color_key, color_hex in self.HIGHLIGHT_COLORS.items():
            if color_key in query_lower:
                highlight_color = color_hex
                logger.info(f"[SimpleGPT] Highlight color (explicit): {color_key} -> {color_hex}")
                break

        # If no explicit color, try to detect by context (status words)
        if not highlight_color:
            for context_key, color_hex in self.CONTEXT_COLORS.items():
                if context_key in query_lower:
                    highlight_color = color_hex
                    logger.info(f"[SimpleGPT] Highlight color (context): {context_key} -> {color_hex}")
                    break

        # Default to yellow if nothing matched
        if not highlight_color:
            highlight_color = '#FFFF00'
            logger.info(f"[SimpleGPT] Using default highlight color: yellow")

        # Find target column and condition
        target_column = None
        target_column_index = None
        filter_value = None
        operator = '=='

        # Look for column mentions
        for idx, col_name in enumerate(column_names):
            col_lower = col_name.lower()
            if col_lower in query_lower or col_name in query:
                target_column = col_name
                target_column_index = idx
                break
            # Partial match
            for word in col_lower.split():
                if len(word) > 2 and word in query_lower:
                    target_column = col_name
                    target_column_index = idx
                    break
            if target_column:
                break

        # Detect operator
        for op, patterns in self.FILTER_OPERATORS.items():
            for pattern in patterns:
                if pattern in query_lower:
                    operator = op
                    break
            if operator != '==':
                break

        # Extract value
        import re
        if operator not in ['empty', 'not_empty']:
            # Try to extract numeric value
            number_match = re.search(r'(\d+(?:[.,]\d+)?)', query_lower)
            if number_match:
                filter_value = float(number_match.group(1).replace(',', '.'))
            else:
                # Try to find text value (e.g., status names)
                status_words = ['оплачен', 'отменен', 'отменён', 'доставлен', 'возврат', 'активн',
                                'неактивн', 'завершен', 'завершён', 'выполнен', 'ожидан', 'vip']
                for status in status_words:
                    if status in query_lower:
                        filter_value = status
                        operator = 'contains'
                        break

        # Execute filter to find rows
        try:
            if target_column is None:
                # Try to find by status-like column
                for idx, col in enumerate(column_names):
                    col_lower = col.lower()
                    if any(x in col_lower for x in ['статус', 'status', 'состоян']):
                        target_column = col
                        target_column_index = idx
                        break

            if target_column is None:
                logger.warning(f"[SimpleGPT] No target column found for highlight")
                return None

            filtered_df = df.copy()
            col = filtered_df.columns[target_column_index]

            if operator == 'empty':
                mask = filtered_df[col].isna() | (filtered_df[col] == '')
            elif operator == 'not_empty':
                mask = filtered_df[col].notna() & (filtered_df[col] != '')
            elif operator == 'contains' and filter_value:
                mask = filtered_df[col].astype(str).str.lower().str.contains(str(filter_value).lower(), na=False)
            elif filter_value is not None:
                try:
                    numeric_val = float(filter_value) if isinstance(filter_value, (int, float, str)) and str(filter_value).replace('.', '').replace('-', '').isdigit() else None
                    if numeric_val is not None:
                        col_numeric = pd.to_numeric(filtered_df[col], errors='coerce')
                        if operator == '>':
                            mask = col_numeric > numeric_val
                        elif operator == '<':
                            mask = col_numeric < numeric_val
                        elif operator == '>=':
                            mask = col_numeric >= numeric_val
                        elif operator == '<=':
                            mask = col_numeric <= numeric_val
                        elif operator == '!=':
                            mask = col_numeric != numeric_val
                        else:
                            mask = col_numeric == numeric_val
                    else:
                        str_col = filtered_df[col].astype(str).str.lower()
                        str_val = str(filter_value).lower()
                        if operator == '!=':
                            mask = str_col != str_val
                        else:
                            mask = str_col == str_val
                except:
                    str_col = filtered_df[col].astype(str).str.lower()
                    str_val = str(filter_value).lower()
                    mask = str_col.str.contains(str_val, na=False)
            else:
                logger.warning(f"[SimpleGPT] No filter condition for highlight")
                return None

            # Get row indices (1-indexed for spreadsheet)
            highlight_rows = [i + 2 for i in filtered_df[mask].index.tolist()]  # +2 for header + 1-indexed

            if not highlight_rows:
                logger.warning(f"[SimpleGPT] No rows matched highlight condition")
                return None

            # Build condition string
            op_display = {
                '==': '=', '!=': '≠', '>': '>', '<': '<', '>=': '≥', '<=': '≤',
                'contains': 'содержит', 'empty': 'пусто', 'not_empty': 'не пусто'
            }
            if operator in ['empty', 'not_empty']:
                condition_str = f"{target_column} {op_display.get(operator, operator)}"
            else:
                condition_str = f"{target_column} {op_display.get(operator, operator)} {filter_value}"

            message = f"Выделено {len(highlight_rows)} строк где {condition_str}"

            return {
                "action_type": "highlight",
                "highlight_rows": highlight_rows,
                "highlight_color": highlight_color,
                "highlight_count": len(highlight_rows),
                "condition_str": condition_str,
                "message": message
            }

        except Exception as e:
            logger.error(f"[SimpleGPT] Error detecting highlight rows: {e}")
            return None

    def _detect_filter_action(self, query: str, column_names: List[str], df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        Определяет, является ли запрос командой фильтрации данных.
        Примеры:
        - "покажи только строки где Статус = Активный"
        - "отфильтруй по Цена > 1000"
        - "найди строки где Дата пустая"
        """
        query_lower = query.lower()

        # Check for filter keywords
        is_filter = any(kw in query_lower for kw in self.FILTER_KEYWORDS)
        if not is_filter:
            return None

        logger.info(f"[SimpleGPT] Filter action detected: {query}")

        # Find target column
        target_column = None
        target_column_index = None

        for idx, col_name in enumerate(column_names):
            col_lower = col_name.lower()
            if col_lower in query_lower or col_name in query:
                target_column = col_name
                target_column_index = idx
                break
            # Partial match
            for word in col_lower.split():
                if len(word) > 2 and word in query_lower:
                    target_column = col_name
                    target_column_index = idx
                    break
            if target_column:
                break

        if not target_column:
            logger.warning(f"[SimpleGPT] No target column found for filter")
            return None

        # Detect operator and value
        import re
        operator = '=='
        filter_value = None

        # Check operators in order of specificity (longer patterns first)
        for op, patterns in self.FILTER_OPERATORS.items():
            for pattern in patterns:
                if pattern in query_lower:
                    operator = op
                    break
            if operator != '==':
                break

        # Extract value based on operator
        if operator in ['empty', 'not_empty']:
            filter_value = None
        else:
            # Try to extract numeric value
            number_match = re.search(r'(\d+(?:[.,]\d+)?)', query_lower)
            if number_match:
                filter_value = float(number_match.group(1).replace(',', '.'))
            else:
                # Try to extract text value after operator patterns
                value_patterns = [
                    r'(?:равно|=|равен|is)\s+["\']?([^"\'.,!?]+)["\']?',
                    r'(?:содержит|contains)\s+["\']?([^"\'.,!?]+)["\']?',
                    r'(?:начинается|starts)\s+(?:с|with)?\s*["\']?([^"\'.,!?]+)["\']?',
                ]
                for vp in value_patterns:
                    value_match = re.search(vp, query_lower)
                    if value_match:
                        filter_value = value_match.group(1).strip()
                        break

                # If still no value, try to find value after column name
                if filter_value is None:
                    col_pattern = re.escape(target_column.lower())
                    after_col_match = re.search(
                        rf'{col_pattern}\s*(?:[=<>!]+|равно|больше|меньше|содержит)\s*["\']?([^\s"\'.,!?]+)',
                        query_lower
                    )
                    if after_col_match:
                        filter_value = after_col_match.group(1).strip()

        # Execute filter and get preview
        try:
            filtered_df = df.copy()
            original_rows = len(filtered_df)
            col = filtered_df.columns[target_column_index]

            if operator == 'empty':
                filtered_df = filtered_df[filtered_df[col].isna() | (filtered_df[col] == '')]
            elif operator == 'not_empty':
                filtered_df = filtered_df[filtered_df[col].notna() & (filtered_df[col] != '')]
            elif operator == 'contains' and filter_value:
                filtered_df = filtered_df[
                    filtered_df[col].astype(str).str.lower().str.contains(str(filter_value).lower(), na=False)
                ]
            elif operator == 'startswith' and filter_value:
                filtered_df = filtered_df[
                    filtered_df[col].astype(str).str.lower().str.startswith(str(filter_value).lower())
                ]
            elif operator == 'endswith' and filter_value:
                filtered_df = filtered_df[
                    filtered_df[col].astype(str).str.lower().str.endswith(str(filter_value).lower())
                ]
            elif filter_value is not None:
                # Numeric or exact match
                try:
                    numeric_val = float(filter_value) if isinstance(filter_value, (int, float, str)) and str(filter_value).replace('.', '').replace('-', '').isdigit() else None
                    if numeric_val is not None:
                        col_numeric = pd.to_numeric(filtered_df[col], errors='coerce')
                        if operator == '>':
                            filtered_df = filtered_df[col_numeric > numeric_val]
                        elif operator == '<':
                            filtered_df = filtered_df[col_numeric < numeric_val]
                        elif operator == '>=':
                            filtered_df = filtered_df[col_numeric >= numeric_val]
                        elif operator == '<=':
                            filtered_df = filtered_df[col_numeric <= numeric_val]
                        elif operator == '!=':
                            filtered_df = filtered_df[col_numeric != numeric_val]
                        else:  # ==
                            filtered_df = filtered_df[col_numeric == numeric_val]
                    else:
                        # String comparison
                        str_col = filtered_df[col].astype(str).str.lower()
                        str_val = str(filter_value).lower()
                        if operator == '!=':
                            filtered_df = filtered_df[str_col != str_val]
                        else:
                            filtered_df = filtered_df[str_col == str_val]
                except Exception as e:
                    logger.warning(f"[SimpleGPT] Filter comparison error: {e}")
                    # Fallback to string comparison
                    str_col = filtered_df[col].astype(str).str.lower()
                    str_val = str(filter_value).lower()
                    filtered_df = filtered_df[str_col == str_val]

            filtered_rows = len(filtered_df)

            # Prepare result data
            filtered_data = {
                "headers": list(filtered_df.columns),
                "rows": format_data_for_sheets(filtered_df.to_dict(orient='records'))
            }

            # Build operator display
            op_display = {
                '==': '=', '!=': '≠', '>': '>', '<': '<', '>=': '≥', '<=': '≤',
                'contains': 'содержит', 'startswith': 'начинается с', 'endswith': 'заканчивается на',
                'empty': 'пусто', 'not_empty': 'не пусто'
            }

            if operator in ['empty', 'not_empty']:
                condition_str = f"{target_column} {op_display.get(operator, operator)}"
            else:
                condition_str = f"{target_column} {op_display.get(operator, operator)} {filter_value}"

            message = f"Фильтр: {condition_str} → {filtered_rows} из {original_rows} строк"

            return {
                "action_type": "filter_data",
                "column_name": target_column,
                "column_index": target_column_index,
                "operator": operator,
                "filter_value": filter_value,
                "original_rows": original_rows,
                "filtered_rows": filtered_rows,
                "filtered_data": filtered_data,
                "condition_str": condition_str,
                "message": message
            }

        except Exception as e:
            logger.error(f"[SimpleGPT] Error filtering data: {e}")
            return None

    def _detect_convert_to_numbers_action(self, query: str, column_names: List[str], df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        Определяет, является ли запрос командой конвертации колонки в числа.
        Примеры:
        - "преобразуй колонку Сумма в числа"
        - "конвертируй в числовой формат колонку Цена"
        """
        query_lower = query.lower()

        # Check for convert to numbers keywords
        is_convert = any(kw in query_lower for kw in self.CONVERT_TO_NUMBERS_KEYWORDS)
        if not is_convert:
            return None

        logger.info(f"[SimpleGPT] Convert to numbers action detected: {query}")

        # Find target column
        target_column = None
        target_column_index = None

        query_words = set(query_lower.split())

        # First pass: exact match
        for idx, col_name in enumerate(column_names):
            col_lower = col_name.lower().strip()
            if len(col_lower) < 2:
                continue
            if col_lower in query_words:
                target_column = col_name
                target_column_index = idx
                break

        # Second pass: partial match
        if not target_column:
            for idx, col_name in enumerate(column_names):
                col_lower = col_name.lower().strip()
                if len(col_lower) < 2:
                    continue
                for word in query_words:
                    if len(word) >= len(col_lower) and (word.startswith(col_lower) or col_lower in word):
                        target_column = col_name
                        target_column_index = idx
                        break
                if target_column:
                    break

        if not target_column:
            logger.warning(f"[SimpleGPT] No target column found for convert to numbers")
            return None

        rule = {
            "column_index": target_column_index,
            "column_name": target_column,
            "row_count": len(df)
        }

        message = f"Преобразую колонку '{target_column}' в числа"

        return {
            "action_type": "convert_to_numbers",
            "rule": rule,
            "message": message
        }

    def _detect_color_scale_action(self, query: str, column_names: List[str], df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        Определяет, является ли запрос командой применения цветовой шкалы (градиента).
        Примеры:
        - "цветовая шкала для колонки Сумма"
        - "градиент от красного к зелёному для Цена"
        - "тепловая карта по колонке Продажи"
        """
        query_lower = query.lower()

        # Check for color scale keywords
        is_color_scale = any(kw in query_lower for kw in self.COLOR_SCALE_KEYWORDS)
        if not is_color_scale:
            return None

        logger.info(f"[SimpleGPT] Color scale action detected: {query}")

        # Find target column - look for exact word match first
        target_column = None
        target_column_index = None

        # Split query into words for exact matching
        query_words = set(query_lower.split())

        logger.info(f"[SimpleGPT] Looking for column in query: '{query}', columns: {column_names}")

        # First pass: exact match (column name is a word in query)
        for idx, col_name in enumerate(column_names):
            col_lower = col_name.lower().strip()
            # Skip empty or very short column names
            if len(col_lower) < 2:
                continue
            # Check if column name appears as a word in query
            if col_lower in query_words:
                target_column = col_name
                target_column_index = idx
                logger.info(f"[SimpleGPT] Found exact match: column '{col_name}' at index {idx}")
                break

        # Second pass: column name is a substring of a query word (e.g. "сумма" in "сумму")
        if not target_column:
            for idx, col_name in enumerate(column_names):
                col_lower = col_name.lower().strip()
                if len(col_lower) < 2:
                    continue
                # Check if any query word starts with or contains the column name
                for word in query_words:
                    if len(word) >= len(col_lower) and (word.startswith(col_lower) or col_lower in word):
                        target_column = col_name
                        target_column_index = idx
                        logger.info(f"[SimpleGPT] Found partial match: column '{col_name}' in word '{word}' at index {idx}")
                        break
                if target_column:
                    break

        # Third pass: match by word stems (handle Russian declensions)
        if not target_column:
            stem_mappings = {
                'цен': ['цена', 'price', 'стоимость', 'cost'],
                'сумм': ['сумма', 'sum', 'total', 'итого'],
                'прибыл': ['прибыль', 'profit', 'доход'],
                'количеств': ['количество', 'qty', 'кол-во', 'шт'],
                'остат': ['остаток', 'остатки', 'stock', 'balance'],
                'продаж': ['продажи', 'sales', 'выручка'],
                'расход': ['расходы', 'expenses', 'затраты'],
                'зарплат': ['зарплата', 'salary', 'оклад'],
                'скидк': ['скидка', 'discount'],
                'налог': ['налог', 'tax', 'ндс', 'vat'],
                'марж': ['маржа', 'margin', 'наценка'],
            }
            for query_word in query_words:
                for stem, col_variants in stem_mappings.items():
                    if query_word.startswith(stem):
                        for idx, col_name in enumerate(column_names):
                            col_lower = col_name.lower().strip()
                            if any(variant in col_lower for variant in col_variants) or col_lower.startswith(stem):
                                target_column = col_name
                                target_column_index = idx
                                logger.info(f"[SimpleGPT] Found stem match for color scale: query '{query_word}' → column '{col_name}' at index {idx}")
                                break
                        if target_column:
                            break
                if target_column:
                    break

        # If no column found, try to find first numeric column
        if not target_column:
            for idx, col_name in enumerate(column_names):
                if idx < len(df.columns):
                    try:
                        numeric_data = pd.to_numeric(df.iloc[:, idx], errors='coerce')
                        if numeric_data.notna().sum() / len(numeric_data) > 0.5:
                            target_column = col_name
                            target_column_index = idx
                            logger.info(f"[SimpleGPT] Auto-selected numeric column for color scale: {col_name}")
                            break
                    except:
                        pass

        if not target_column:
            logger.warning(f"[SimpleGPT] No target column found for color scale")
            return None

        # Determine color preset based on query
        preset_name = 'green_yellow_red'  # Default: low=green, high=red (good for costs, expenses)

        # "высокой ценой зеленым" / "наоборот" / "прибыль" = high values should be green
        if any(kw in query_lower for kw in ['к зелёному', 'к зеленому', 'to green', 'прибыл', 'доход',
                                             'высок', 'наоборот', 'инвертир', 'большой зелен', 'больше зелен']):
            preset_name = 'red_yellow_green'  # low=red, high=green (good for profits, revenue)
        elif any(kw in query_lower for kw in ['синий', 'blue', 'голуб']):
            preset_name = 'white_to_blue'
        elif any(kw in query_lower for kw in ['зелён', 'зелен', 'green']) and 'красн' not in query_lower:
            preset_name = 'white_to_green'

        preset = self.COLOR_SCALE_PRESETS[preset_name]

        # Get column stats for the gradient
        try:
            col_data = pd.to_numeric(df.iloc[:, target_column_index], errors='coerce')
            min_val = float(col_data.min())
            max_val = float(col_data.max())
            mid_val = float(col_data.median())
        except:
            min_val = 0
            max_val = 100
            mid_val = 50

        # Build color scale rule
        rule = {
            "column_index": target_column_index,
            "column_name": target_column,
            "min_color": preset['min_color'],
            "mid_color": preset['mid_color'],
            "max_color": preset['max_color'],
            "min_value": min_val,
            "mid_value": mid_val,
            "max_value": max_val,
            "row_count": len(df)
        }

        message = f"Цветовая шкала для колонки '{target_column}' ({min_val:.0f} → {max_val:.0f})"

        return {
            "action_type": "color_scale",
            "rule": rule,
            "message": message
        }



    def _is_analysis_query(self, query: str) -> bool:
        """Detect if query requires deep analysis mode."""
        query_lower = query.lower()
        for keyword in self.DEEP_ANALYSIS_KEYWORDS:
            if keyword in query_lower:
                return True
        return False

    def _is_conversational_query(self, query: str, history: List[Dict[str, Any]] = None) -> bool:
        """Detect if query is conversational (follow-up, why, explain)."""
        query_lower = query.lower().strip()

        # Very short queries with history are likely follow-ups
        if history and len(history) > 0 and len(query_lower.split()) <= 3:
            short_followups = ['почему', 'зачем', 'как', 'что', 'где', 'когда', 'объясни', 'поясни', 'подробнее']
            if any(query_lower.startswith(w) for w in short_followups):
                return True

        # Check conversational keywords
        for keyword in self.CONVERSATIONAL_KEYWORDS:
            if keyword in query_lower:
                return True

        return False

    async def _handle_conversational(
        self,
        query: str,
        df: pd.DataFrame,
        schema_prompt: str,
        history: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle conversational/follow-up queries without code generation."""

        # Build history string
        history_str = ""
        if history:
            for i, item in enumerate(history[-3:], 1):
                prev_q = item.get('query', '')
                prev_r = item.get('response', '')[:500] if item.get('response') else ''
                history_str += f"Q{i}: {prev_q}\nA{i}: {prev_r}\n\n"

        prompt = self.CONVERSATIONAL_PROMPT.format(
            history=history_str if history_str else "Нет предыдущих вопросов",
            query=query
        )

        # Add data context
        prompt += f"\n\nКОНТЕКСТ ДАННЫХ:\n{schema_prompt[:1000]}"

        try:
            response = await self.client.chat.completions.create(
                model=self.MODEL,
                messages=[
                    {"role": "system", "content": "Ты умный аналитик данных. Отвечай развёрнуто и понятно на вопросы пользователя."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=800
            )

            answer = response.choices[0].message.content.strip()

            return {
                "success": True,
                "result": answer,
                "explanation": answer,
                "response_type": "conversational"
            }
        except Exception as e:
            logger.error(f"[SimpleGPT] Conversational error: {e}")
            return {"success": False, "error": str(e)}


    async def process(
        self,
        query: str,
        df: pd.DataFrame,
        column_names: List[str],
        custom_context: Optional[str] = None,
        history: List[Dict[str, Any]] = None,
        reference_df: pd.DataFrame = None,
        reference_sheet_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Главный метод обработки запроса.
        """
        start_time = time.time()

        try:
            # 0. Check for direct actions (sort, format, etc.) - no GPT needed
            sort_action = self._detect_sort_action(query, column_names)
            if sort_action:
                elapsed = time.time() - start_time
                logger.info(f"[SimpleGPT] Returning sort action: {sort_action}")
                return {
                    "success": True,
                    "action_type": "sort",
                    "result_type": "action",
                    "sort_column": sort_action["column_name"],
                    "sort_column_index": sort_action["column_index"],
                    "sort_order": sort_action["sort_order"],
                    "summary": sort_action["message"],
                    "processing_time": f"{elapsed:.2f}s",
                    "processor": "SimpleGPT v1.0 (direct action)"
                }

            # Check for freeze action
            freeze_action = self._detect_freeze_action(query)
            if freeze_action:
                elapsed = time.time() - start_time
                logger.info(f"[SimpleGPT] Returning freeze action: {freeze_action}")
                return {
                    "success": True,
                    "action_type": "freeze",
                    "result_type": "action",
                    "freeze_rows": freeze_action["freeze_rows"],
                    "freeze_columns": freeze_action["freeze_columns"],
                    "summary": freeze_action["message"],
                    "processing_time": f"{elapsed:.2f}s",
                    "processor": "SimpleGPT v1.0 (direct action)"
                }

            # Check for format action
            format_action = self._detect_format_action(query)
            if format_action:
                elapsed = time.time() - start_time
                logger.info(f"[SimpleGPT] Returning format action: {format_action}")
                return {
                    "success": True,
                    "action_type": "format",
                    "result_type": "action",
                    "format_type": format_action["format_type"],
                    "target_row": format_action["target_row"],
                    "bold": format_action["bold"],
                    "background_color": format_action["background_color"],
                    "summary": format_action["message"],
                    "processing_time": f"{elapsed:.2f}s",
                    "processor": "SimpleGPT v1.0 (direct action)"
                }

            # Check for chart action (needs df for column analysis)
            chart_action = self._detect_chart_action(query, column_names, df)
            if chart_action:
                # If pending, finalize with GPT
                if chart_action.get("needs_gpt_selection"):
                    logger.info(f"[SimpleGPT] Chart action needs GPT selection")
                    chart_action = await self._finalize_chart_action(chart_action, column_names, df)

                elapsed = time.time() - start_time
                logger.info(f"[SimpleGPT] Chart action detected: {chart_action}")
                chart_result = {
                    "success": True,
                    "action_type": "chart",
                    "result_type": "action",
                    "chart_spec": chart_action["chart_spec"],
                    "summary": chart_action["message"],
                    "processing_time": f"{elapsed:.2f}s",
                    "processor": "SimpleGPT v1.0 (direct action)"
                }
                logger.info(f"[SimpleGPT] Returning chart result with keys: {list(chart_result.keys())}")
                logger.info(f"[SimpleGPT] chart_result['chart_spec']: {chart_result.get('chart_spec')}")
                return chart_result

            # Check for convert to numbers action
            convert_action = self._detect_convert_to_numbers_action(query, column_names, df)
            if convert_action:
                elapsed = time.time() - start_time
                logger.info(f"[SimpleGPT] Returning convert to numbers action: {convert_action}")
                return {
                    "success": True,
                    "action_type": "convert_to_numbers",
                    "result_type": "action",
                    "rule": convert_action["rule"],
                    "summary": convert_action["message"],
                    "processing_time": f"{elapsed:.2f}s",
                    "processor": "SimpleGPT v1.0 (direct action)"
                }

            # Check for color scale action (BEFORE conditional formatting!)
            color_scale_action = self._detect_color_scale_action(query, column_names, df)
            if color_scale_action:
                elapsed = time.time() - start_time
                logger.info(f"[SimpleGPT] Returning color scale action: {color_scale_action}")
                return {
                    "success": True,
                    "action_type": "color_scale",
                    "result_type": "action",
                    "rule": color_scale_action["rule"],
                    "summary": color_scale_action["message"],
                    "processing_time": f"{elapsed:.2f}s",
                    "processor": "SimpleGPT v1.0 (direct action)"
                }

            # Check for conditional formatting action
            conditional_action = self._detect_conditional_format_action(query, column_names, df)
            if conditional_action:
                elapsed = time.time() - start_time
                logger.info(f"[SimpleGPT] Returning conditional format action: {conditional_action}")
                return {
                    "success": True,
                    "action_type": "conditional_format",
                    "result_type": "action",
                    "rule": conditional_action["rule"],
                    "summary": conditional_action["message"],
                    "processing_time": f"{elapsed:.2f}s",
                    "processor": "SimpleGPT v1.0 (direct action)"
                }

            # Check for pivot table action
            pivot_action = self._detect_pivot_action(query, column_names, df)
            if pivot_action:
                elapsed = time.time() - start_time
                logger.info(f"[SimpleGPT] Returning pivot table action: {pivot_action}")
                return {
                    "success": True,
                    "action_type": "pivot_table",
                    "result_type": "action",
                    "pivot_data": pivot_action["pivot_data"],
                    "group_column": pivot_action["group_column"],
                    "value_column": pivot_action["value_column"],
                    "agg_func": pivot_action["agg_func"],
                    "summary": pivot_action["message"],
                    "processing_time": f"{elapsed:.2f}s",
                    "processor": "SimpleGPT v1.0 (direct action)"
                }

            # Check for CSV split action (text to columns)
            csv_split_action = self._detect_csv_split_action(query, column_names, df)
            if csv_split_action:
                elapsed = time.time() - start_time
                logger.info(f"[SimpleGPT] Returning CSV split action")
                return {
                    "success": True,
                    "action_type": "csv_split",
                    "result_type": "action",
                    "structured_data": csv_split_action["structured_data"],
                    "original_rows": csv_split_action["original_rows"],
                    "new_rows": csv_split_action["new_rows"],
                    "new_cols": csv_split_action["new_cols"],
                    "delimiter": csv_split_action["delimiter"],
                    "summary": csv_split_action["message"],
                    "processing_time": f"{elapsed:.2f}s",
                    "processor": "SimpleGPT v1.0 (direct action)"
                }

            # Check for data cleaning action
            clean_action = self._detect_clean_action(query, column_names, df)
            if clean_action:
                elapsed = time.time() - start_time
                logger.info(f"[SimpleGPT] Returning clean data action: {clean_action}")
                return {
                    "success": True,
                    "action_type": "clean_data",
                    "result_type": "action",
                    "operations": clean_action["operations"],
                    "fill_value": clean_action["fill_value"],
                    "target_column": clean_action["target_column"],
                    "original_rows": clean_action["original_rows"],
                    "final_rows": clean_action["final_rows"],
                    "cleaned_data": clean_action["cleaned_data"],
                    "changes": clean_action["changes"],
                    "summary": clean_action["message"],
                    "processing_time": f"{elapsed:.2f}s",
                    "processor": "SimpleGPT v1.0 (direct action)"
                }

            # Check for data validation action
            validation_action = self._detect_validation_action(query, column_names, df)
            if validation_action:
                elapsed = time.time() - start_time
                logger.info(f"[SimpleGPT] Returning data validation action: {validation_action}")
                return {
                    "success": True,
                    "action_type": "data_validation",
                    "result_type": "action",
                    "rule": validation_action["rule"],
                    "summary": validation_action["message"],
                    "processing_time": f"{elapsed:.2f}s",
                    "processor": "SimpleGPT v1.0 (direct action)"
                }

            # Check for highlight action BEFORE filter (to handle "выдели где..." queries)
            highlight_action = self._detect_highlight_action(query, column_names, df)
            if highlight_action:
                elapsed = time.time() - start_time
                logger.info(f"[SimpleGPT] Returning highlight action: {highlight_action}")
                return {
                    "success": True,
                    "action_type": "highlight",
                    "result_type": "action",
                    "highlight_rows": highlight_action["highlight_rows"],
                    "highlight_color": highlight_action["highlight_color"],
                    "highlight_count": highlight_action["highlight_count"],
                    "highlight_message": highlight_action["message"],
                    "summary": highlight_action["message"],
                    "processing_time": f"{elapsed:.2f}s",
                    "processor": "SimpleGPT v1.0 (direct action)"
                }

            # Check for filter action
            filter_action = self._detect_filter_action(query, column_names, df)
            if filter_action:
                elapsed = time.time() - start_time
                logger.info(f"[SimpleGPT] Returning filter action: {filter_action}")
                return {
                    "success": True,
                    "action_type": "filter_data",
                    "result_type": "action",
                    "column_name": filter_action["column_name"],
                    "column_index": filter_action["column_index"],
                    "operator": filter_action["operator"],
                    "filter_value": filter_action["filter_value"],
                    "original_rows": filter_action["original_rows"],
                    "filtered_rows": filter_action["filtered_rows"],
                    "filtered_data": filter_action["filtered_data"],
                    "condition_str": filter_action["condition_str"],
                    "summary": filter_action["message"],
                    "processing_time": f"{elapsed:.2f}s",
                    "processor": "SimpleGPT v1.0 (direct action)"
                }

            # 0.5. Conversational mode DISABLED - was causing issues with normal queries
            # TODO: Re-enable with stricter detection (only "почему?" single word)
            pass

            # 1. Schema extraction
            logger.info(f"[SimpleGPT] Processing: {query[:50]}...")
            schema = self.schema_extractor.extract_schema(df)
            schema_prompt = self.schema_extractor.schema_to_prompt(schema)
            logger.info(f"[SimpleGPT] Schema: {schema['column_count']} cols, {schema['row_count']} rows")
            
            # v9.2.0: Add reference sheet schema if provided
            if reference_df is not None:
                ref_schema = self.schema_extractor.extract_schema(reference_df)
                ref_prompt = self.schema_extractor.schema_to_prompt(ref_schema)
                ref_name = reference_sheet_name or "reference_df"
                schema_prompt += f"""

ДОПОЛНИТЕЛЬНЫЙ СПРАВОЧНИК (reference_df) - лист "{ref_name}":
{ref_prompt}

ВАЖНО для VLOOKUP (подтягивание данных между листами):

СПОСОБ 1 - merge (рекомендуется для массовых операций):
merged = df.merge(reference_df[['ключ', 'значение']], left_on='колонка_df', right_on='ключ', how='left')

СПОСОБ 2 - map через словарь (быстрее для больших данных):
lookup_dict = reference_df.set_index('ключ')['значение'].to_dict()
df['новая_колонка'] = df['колонка_df'].map(lookup_dict)

СПОСОБ 3 - поиск одного значения:
value = reference_df.loc[reference_df['ключ'] == искомое, 'значение'].values
result = value[0] if len(value) > 0 else 'Не найдено'

ОБРАБОТКА НЕНАЙДЕННЫХ ЗНАЧЕНИЙ:
- После merge проверяй: not_found = merged['результат'].isna().sum()
- Сообщай пользователю сколько значений не найдено
- Показывай примеры ненайденных: df[df['результат'].isna()]['ключ'].head(5).tolist()

ТИПИЧНЫЕ ОШИБКИ (избегай!):
- НЕ используй .values[0] без проверки длины массива
- НЕ забывай how='left' чтобы сохранить все строки df
- ПРОВЕРЯЙ типы данных ключей (str vs int): df['id'].astype(str)
"""
                logger.info(f"[SimpleGPT] Reference sheet added: {ref_name}, {ref_schema['row_count']} rows")

            # 2. Generate and execute code (with retries)
            result = await self._generate_and_execute(
                query=query,
                df=df,
                schema_prompt=schema_prompt,
                custom_context=custom_context,
                history=history,
                reference_df=reference_df
            )

            if not result["success"]:
                return self._create_error_response(result.get("error", "Unknown error"), time.time() - start_time)

            # 3. Post-validation
            validation = await self._validate_result(query, result["result"])

            if validation == "BAD":
                logger.warning(f"[SimpleGPT] Post-validation failed, retrying with clarification...")
                # Retry with explicit clarification
                result = await self._generate_and_execute(
                    query=query,
                    df=df,
                    schema_prompt=schema_prompt,
                    custom_context=custom_context,
                    history=history,
                    clarification="Предыдущий результат не соответствовал запросу. Убедись что возвращаешь правильный тип данных: список для 'какие', число для 'сколько', DataFrame для 'покажи'.",
                    reference_df=reference_df
                )

                # Check retry result
                if not result.get("success"):
                    return self._create_error_response(result.get("error", "Validation failed after retry"), time.time() - start_time)

            # 4. Format response
            elapsed = time.time() - start_time
            formatted_result = self._format_result(result["result"])
            result_type = self._get_result_type(result["result"])

            # Use explanation from code if available, otherwise generate summary
            explanation = result.get("explanation", "")
            if explanation:
                summary = clean_explanation_text(explanation)
                logger.info(f"[SimpleGPT] Using explanation from code: {explanation[:100]}...")
            else:
                summary = self._generate_summary(result["result"], result_type, query)

            response = {
                "success": True,
                "result": formatted_result,
                "result_type": result_type,
                "summary": summary,
                "code": result.get("code"),
                "processing_time": f"{elapsed:.2f}s",
                "processor": "SimpleGPT v1.0",
                "validation": validation
            }

            # Check if this is a highlight query
            query_lower = query.lower()
            is_highlight_query = any(kw in query_lower for kw in ['выдели', 'выделить', 'подсвети', 'подсветить', 'highlight', 'mark'])

            if is_highlight_query:
                logger.info(f"[SimpleGPT] Highlight query detected: {query[:50]}")
                # Extract row indices from the result for highlighting
                highlight_rows = self._extract_highlight_rows(result["result"])
                if highlight_rows:
                    response["highlight_rows"] = highlight_rows
                    response["highlighted_count"] = len(highlight_rows)
                    response["highlight_color"] = "#FFFF00"  # Yellow
                    response["highlight_message"] = f"Выделено {len(highlight_rows)} строк"
                    response["result_type"] = "highlight"
                    logger.info(f"[SimpleGPT] Generated highlight_rows: {highlight_rows[:10]}... (total: {len(highlight_rows)})")

            # Add structured_data for tables/lists (only if NOT highlight query and NOT text-only)
            # Skip if result is a simple string (text-only response)
            is_text_only = isinstance(formatted_result, str)
            if is_text_only:
                logger.info(f"[SimpleGPT] Text-only response detected, no structured_data")

            # Debug logging
            logger.info(f"[SimpleGPT] DEBUG - result type: {type(result['result'])}, formatted_result type: {type(formatted_result)}")
            # Check if result is a table (list of dicts) - skip for text-only
            is_table = not is_text_only and isinstance(formatted_result, list) and len(formatted_result) > 0 and isinstance(formatted_result[0], dict)
            logger.info(f"[SimpleGPT] Checking write_data: is_highlight={is_highlight_query}, result_type={result_type}, is_table={is_table}, has_ref_df={reference_df is not None}")
            if not is_highlight_query and is_table:
                # Extract headers from first row keys (rows are dicts from DataFrame)
                headers = list(formatted_result[0].keys()) if formatted_result else []
                logger.info(f"[SimpleGPT] Table result detected, headers: {headers}")
                
                # v9.3.2: For VLOOKUP (with reference_df), write directly to sheet
                if reference_df is not None:
                    logger.info(f"[SimpleGPT] ✅ VLOOKUP mode - setting write_data")
                    # VLOOKUP result - convert to DataFrame and write to sheet
                    vlookup_df = pd.DataFrame(formatted_result)
                    response["action_type"] = "write_data"
                    response["write_data"] = format_data_for_sheets(vlookup_df.values.tolist())
                    response["write_headers"] = headers
                    response["summary"] = f"✅ Данные из листа \"{reference_sheet_name or 'справочник'}\" подтянуты ({len(formatted_result)} строк)"
                    logger.info(f"[SimpleGPT] VLOOKUP result: {len(formatted_result)} rows, writing to sheet")
                else:
                    # Regular table - show in sidebar or create new sheet
                    response["structured_data"] = {
                        "headers": headers,
                        "rows": format_data_for_sheets(formatted_result),
                        "display_mode": "sidebar_only" if len(formatted_result) <= 20 else "create_sheet"
                    }
            elif result_type == "list" and isinstance(formatted_result, list):
                # Convert all items to strings for schema validation
                response["key_findings"] = [str(item) for item in formatted_result]

            return response

        except Exception as e:
            elapsed = time.time() - start_time
            error_msg = f"{type(e).__name__}: {str(e)}" if str(e) else type(e).__name__
            logger.error(f"[SimpleGPT] Error: {error_msg}", exc_info=True)
            return self._create_error_response(error_msg, elapsed)

    async def _generate_and_execute(
        self,
        query: str,
        df: pd.DataFrame,
        schema_prompt: str,
        custom_context: Optional[str] = None,
        history: List[Dict[str, Any]] = None,
        clarification: Optional[str] = None,
        previous_error: Optional[str] = None,
        reference_df: pd.DataFrame = None
    ) -> Dict[str, Any]:
        """Генерирует и выполняет код с retry."""

        for attempt in range(self.MAX_RETRIES + 1):
            # Generate code
            code = await self._generate_code(
                query=query,
                schema_prompt=schema_prompt,
                custom_context=custom_context,
                history=history,
                clarification=clarification,
                previous_error=previous_error
            )

            if not code:
                return {"success": False, "error": "Не удалось сгенерировать код"}

            # v9.3.3: Fix syntax BEFORE validation
            code = self._fix_code_syntax(code)

            # Validate code safety
            is_safe, safety_error = self._validate_code_safety(code)
            if not is_safe:
                # Give more specific hint for syntax errors
                if "unterminated string" in safety_error.lower() or "string literal" in safety_error.lower():
                    previous_error = f"SYNTAX ERROR: {safety_error}. DO NOT use triple quotes! Use: explanation = 'text' + 'more text'"
                else:
                    previous_error = f"Небезопасный код: {safety_error}"
                continue

            # Execute code
            try:
                exec_result = self._execute_code(code, df, reference_df)
                return {"success": True, "result": exec_result['result'], "explanation": exec_result.get('explanation', ''), "code": code}
            except Exception as e:
                previous_error = f"{type(e).__name__}: {str(e)}"
                logger.warning(f"[SimpleGPT] Attempt {attempt + 1} failed: {previous_error}")
                continue

        return {"success": False, "error": previous_error}

    async def _generate_code(
        self,
        query: str,
        schema_prompt: str,
        custom_context: Optional[str] = None,
        history: List[Dict[str, Any]] = None,
        clarification: Optional[str] = None,
        previous_error: Optional[str] = None
    ) -> Optional[str]:
        """Генерирует Pandas код через GPT-4o."""

        user_prompt = f"""СХЕМА ДАННЫХ:
{schema_prompt}

ЗАПРОС: {query}
"""

        # Build history context if available
        history_context = ""
        if history and len(history) > 0:
            history_context = "\nИСТОРИЯ РАЗГОВОРА (предыдущие вопросы и ответы):\n"
            for i, item in enumerate(history[-5:], 1):
                prev_query = item.get('query', '')
                prev_response = item.get('response', '')
                if prev_query:
                    history_context += f"{i}. Вопрос: {prev_query}\n"
                    if prev_response:
                        resp_str = str(prev_response)
                        history_context += f"   Ответ: {resp_str[:150]}...\n" if len(resp_str) > 150 else f"   Ответ: {resp_str}\n"
            history_context += "ВАЖНО: Используй историю чтобы понять контекст вопросов типа 'почему?' или 'а Петров?'\n"
            logger.info(f"[SimpleGPT] Added conversation history: {len(history)} messages")

        user_prompt = f"""СХЕМА ДАННЫХ:
{schema_prompt}
{history_context}
ЗАПРОС: {query}
"""
        if custom_context:
            user_prompt += f"""
РОЛЬ ПОЛЬЗОВАТЕЛЯ: {custom_context}
ВАЖНО: Учитывай роль в explanation! Фокусируйся на метриках важных для этой роли.
"""

        if clarification:
            user_prompt += f"\nВАЖНО: {clarification}\n"

        if previous_error:
            user_prompt += f"\nПРЕДЫДУЩАЯ ОШИБКА (избегай её): {previous_error}\n"

        try:
            # Select appropriate system prompt
            system_prompt = self.SYSTEM_PROMPT
            if self._is_analysis_query(query):
                system_prompt = self.ANALYSIS_SYSTEM_PROMPT + "\n\n" + self.SYSTEM_PROMPT
                logger.info("[SimpleGPT] Using deep analysis mode")

            response = await self.client.chat.completions.create(
                model=self.MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=1000
            )

            content = response.choices[0].message.content

            # Extract code from markdown
            code_match = re.search(r'```python\s*(.*?)\s*```', content, re.DOTALL)
            if code_match:
                return code_match.group(1).strip()

            # Try without markdown
            if 'result' in content and '=' in content:
                return content.strip()

            return None

        except Exception as e:
            logger.error(f"[SimpleGPT] Code generation error: {e}")
            return None

    async def _validate_result(self, query: str, result: Any) -> str:
        """Post-validation: проверяет релевантность результата."""

        # Format result for validation
        result_str = self._format_for_validation(result)

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",  # Cheaper model for validation
                messages=[
                    {"role": "user", "content": self.VALIDATION_PROMPT.format(
                        query=query,
                        result=result_str
                    )}
                ],
                temperature=0,
                max_tokens=10
            )

            answer = response.choices[0].message.content.strip().upper()
            return "OK" if "OK" in answer else "BAD"

        except Exception as e:
            logger.warning(f"[SimpleGPT] Validation error: {e}")
            return "OK"  # Default to OK if validation fails

    def _fix_code_syntax(self, code: str) -> str:
        """Fix syntax issues: triple quotes and regular strings with embedded newlines."""
        import re

        logger.debug(f"[FIX_SYNTAX] Input code length: {len(code)}")

        # Step 1: Fix closed triple quotes - replace with single quotes + escaped content
        tq_d = chr(34)*3  # triple double quote
        tq_s = chr(39)*3  # triple single quote

        def fix_closed(m):
            s = m.group(1)
            s = s.replace(chr(92), chr(92)+chr(92))  # backslash -> double backslash
            s = s.replace(chr(10), chr(92)+chr(110))  # newline -> backslash-n
            s = s.replace(chr(13), chr(32))  # carriage return -> space
            s = s.replace(chr(34), chr(92)+chr(34))  # double quote -> escaped
            return chr(34) + s + chr(34)

        # Match closed triple quotes and replace
        code = re.sub(tq_d + r'(.*?)' + tq_d, fix_closed, code, flags=re.DOTALL)
        code = re.sub(tq_s + r'(.*?)' + tq_s, fix_closed, code, flags=re.DOTALL)

        # Step 2: Handle unclosed triple quotes - remove to end of line
        while tq_d in code:
            i = code.find(tq_d)
            j = code.find(chr(10), i)
            code = code[:i] + chr(34)+chr(34) + (code[j:] if j > 0 else chr(32))
        while tq_s in code:
            i = code.find(tq_s)
            j = code.find(chr(10), i)
            code = code[:i] + chr(39)+chr(39) + (code[j:] if j > 0 else chr(32))

        # Step 3: Fix regular strings with embedded newlines
        lines = code.split(chr(10))
        fixed_lines = []
        pending_line = None
        pending_quote = None

        for line in lines:
            if pending_line is not None:
                if pending_quote in line:
                    close_idx = line.find(pending_quote)
                    merged = pending_line + chr(92) + chr(110) + line[:close_idx].replace(pending_quote, chr(92)+pending_quote) + pending_quote + line[close_idx+1:]
                    fixed_lines.append(merged)
                    pending_line = None
                    pending_quote = None
                else:
                    pending_line = pending_line + chr(92) + chr(110) + line.replace(chr(92), chr(92)+chr(92))
            else:
                temp = line.replace(chr(92)+chr(34), chr(88)+chr(88)).replace(chr(92)+chr(39), chr(88)+chr(88))
                dq_count = temp.count(chr(34))
                sq_count = temp.count(chr(39))
                eq_f_dq = chr(61)+chr(32)+chr(102)+chr(34)
                eq_dq = chr(61)+chr(32)+chr(34)
                eq_fdq = chr(61)+chr(102)+chr(34)
                eq_f_sq = chr(61)+chr(32)+chr(102)+chr(39)
                eq_sq = chr(61)+chr(32)+chr(39)
                eq_fsq = chr(61)+chr(102)+chr(39)
                if dq_count % 2 == 1 and (eq_f_dq in line or eq_dq in line or eq_fdq in line):
                    pending_line = line
                    pending_quote = chr(34)
                elif sq_count % 2 == 1 and (eq_f_sq in line or eq_sq in line or eq_fsq in line):
                    pending_line = line
                    pending_quote = chr(39)
                else:
                    fixed_lines.append(line)

        if pending_line is not None:
            fixed_lines.append(pending_line + pending_quote)

        result = chr(10).join(fixed_lines)
        logger.debug(f"[FIX_SYNTAX] Output code length: {len(result)}")
        return result

    def _validate_code_safety(self, code: str) -> tuple:
        """Проверяет безопасность кода."""
        # First try to fix common syntax errors
        code = self._fix_code_syntax(code)

        for pattern in self.FORBIDDEN_PATTERNS:
            if re.search(pattern, code, re.IGNORECASE):
                return False, f"Forbidden pattern: {pattern}"

        # Check AST
        try:
            ast.parse(code)
        except SyntaxError as e:
            return False, f"Syntax error: {e}"

        return True, None

    def _execute_code(self, code: str, df: pd.DataFrame, reference_df: pd.DataFrame = None) -> dict:
        """Выполняет код в sandbox. Возвращает dict с result и explanation."""

        # Create safe namespace
        namespace = {
            'df': df.copy(),
            'pd': pd,
            'np': np,
            'result': None,
            'explanation': None,
            'datetime': __import__('datetime'),
            'timedelta': __import__('datetime').timedelta,
            're': __import__('re'),
            'math': __import__('math'),
        }
        
        # v9.2.0: Add reference_df for cross-sheet VLOOKUP
        if reference_df is not None:
            namespace['reference_df'] = reference_df.copy()

        exec(code, namespace)

        result = namespace.get('result')
        explanation = namespace.get('explanation', '')

        # Allow result = None for text-only responses
        if result is None and not explanation:
            raise ValueError("Код не вернул результат (result = None)")

        # For text-only responses, use explanation as result
        if result is None and explanation:
            result = explanation

        return {'result': result, 'explanation': explanation}

    def _format_result(self, result: Any) -> Any:
        """Форматирует результат для JSON."""

        if isinstance(result, pd.DataFrame):
            # Convert to list of dicts
            return result.to_dict(orient='records')
        elif isinstance(result, pd.Series):
            return result.tolist()
        elif isinstance(result, np.ndarray):
            return result.tolist()
        elif isinstance(result, (np.integer, np.floating)):
            return float(result)
        elif isinstance(result, list):
            return result
        else:
            return result

    def _format_for_validation(self, result: Any) -> str:
        """Форматирует результат для валидации."""

        if isinstance(result, pd.DataFrame):
            if len(result) > 5:
                return f"DataFrame с {len(result)} строками. Первые 3: {result.head(3).to_dict(orient='records')}"
            return str(result.to_dict(orient='records'))
        elif isinstance(result, (list, pd.Series)):
            items = list(result)[:10]
            return f"Список: {items}" + (f" (всего {len(result)})" if len(result) > 10 else "")
        elif isinstance(result, (int, float, np.integer, np.floating)):
            return f"Число: {result}"
        else:
            return str(result)[:500]

    def _get_result_type(self, result: Any) -> str:
        """Определяет тип результата."""

        if isinstance(result, pd.DataFrame):
            return "table"
        elif isinstance(result, (list, pd.Series)):
            return "list"
        elif isinstance(result, (int, float, np.integer, np.floating)):
            return "number"
        else:
            return "text"

    def _generate_summary(self, result: Any, result_type: str, query: str) -> str:
        """Генерирует человеко-читаемое описание результата."""

        if result_type == "number":
            # Для чисел - просто значение
            if isinstance(result, float):
                return f"{result:,.2f}".replace(",", " ")
            return str(result)

        elif result_type == "list":
            # Для списков - перечисление элементов
            items = list(result) if isinstance(result, pd.Series) else result
            if len(items) == 0:
                return "Ничего не найдено"
            elif len(items) <= 5:
                return ", ".join(str(item) for item in items)
            else:
                first_items = ", ".join(str(item) for item in items[:5])
                return f"{first_items} (и ещё {len(items) - 5})"

        elif result_type == "table":
            # Для таблиц - количество строк
            if isinstance(result, pd.DataFrame):
                return f"Найдено {len(result)} записей"
            elif isinstance(result, list):
                return f"Найдено {len(result)} записей"
            return "Таблица данных"

        else:
            # Текст
            return str(result)[:200] if result else "Результат обработан"

    def _extract_highlight_rows(self, result: Any) -> List[int]:
        """
        Извлекает номера строк для выделения из результата.
        Возвращает list[int] с номерами строк (1-based для Google Sheets, +1 для header).
        """
        try:
            if isinstance(result, pd.DataFrame):
                # Get original DataFrame indices and convert to Google Sheets row numbers
                # +2 because: +1 for 1-based indexing, +1 for header row
                indices = result.index.tolist()
                row_numbers = [int(idx) + 2 for idx in indices]
                logger.info(f"[SimpleGPT] Extracted {len(row_numbers)} row indices from DataFrame")
                return row_numbers
            elif isinstance(result, pd.Series):
                # Series with row indices
                indices = result.index.tolist()
                row_numbers = [int(idx) + 2 for idx in indices]
                return row_numbers
            elif isinstance(result, list):
                # If result is a list of row numbers
                if all(isinstance(x, (int, np.integer)) for x in result):
                    return [int(x) + 2 for x in result]
                # If result is list of dicts (from DataFrame.to_dict), can't extract indices
                return []
            else:
                return []
        except Exception as e:
            logger.error(f"[SimpleGPT] Error extracting highlight rows: {e}")
            return []

    def _create_error_response(self, error: str, elapsed: float) -> Dict[str, Any]:
        """Создаёт ответ об ошибке."""
        return {
            "success": False,
            "error": error,
            "processing_time": f"{elapsed:.2f}s",
            "processor": "SimpleGPT v1.0"
        }


# Singleton
_processor = None

def get_simple_gpt_processor() -> SimpleGPTProcessor:
    global _processor
    if _processor is None:
        _processor = SimpleGPTProcessor()
    return _processor
