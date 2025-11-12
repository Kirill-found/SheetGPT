"""
AI + Python Executor Service
Работает как Formula Bot:
1. AI понимает запрос и генерирует Python код
2. Python выполняет код на реальных данных
3. Возвращает 100% точный результат
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from openai import OpenAI
from app.config import settings
import json
import traceback
from io import StringIO
import sys
import re

class AICodeExecutor:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4o"  # Лучшая модель для генерации кода

    def process_with_code(self, query: str, column_names: List[str], sheet_data: List[List[Any]], history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Основная функция - генерирует и выполняет Python код для точных расчетов
        """
        generated_code = None  # Инициализируем перед try для доступа в except
        try:
            # Шаг 1: Создаем DataFrame
            df = pd.DataFrame(sheet_data, columns=column_names)

            # FAILSAFE: For average price queries, use simple direct calculation
            query_lower = query.lower()
            if any(word in query_lower for word in ['средн', 'average', 'mean', 'sredn', 'tsena', 'price']):
                if any(word in query_lower for word in ['постав', 'supplier', 'postavsh', 'компан', 'kazhdogo']):
                    # This is "average price per supplier" query - use failsafe
                    return self._calculate_avg_price_failsafe(df, column_names)

            # FAILSAFE 2: For chart/table creation queries, use direct pandas calculation
            if any(word in query_lower for word in ['создай график', 'построй график', 'сделай график', 'график по', 'диаграмм']):
                if any(word in query_lower for word in ['топ', 'top']):
                    # "создай график по топ X товарам" - use failsafe
                    return self._calculate_top_items_failsafe(df, column_names, query)

            # Шаг 2: AI генерирует Python код
            try:
                generated_code = self._generate_python_code(query, df)
                # DEBUG: Логируем сгенерированный код
                print(f"\n{'='*60}\nGENERATED CODE:\n{'='*60}\n{generated_code}\n{'='*60}\n")
            except Exception as gen_error:
                generated_code = f"ERROR DURING GENERATION: {gen_error}"
                raise

            # Шаг 3: Выполняем код безопасно
            try:
                result = self._execute_python_code(generated_code, df)
            except Exception as exec_error:
                # Сохраняем код даже если выполнение упало
                print(f"\n⛔ EXECUTION ERROR with code:\n{generated_code}\n")
                raise

            # Шаг 4: Форматируем ответ
            return self._format_response(result, generated_code, query)

        except Exception as e:
            # Добавляем сгенерированный код в ошибку для отладки
            error_summary = f"Ошибка: {str(e)}"
            if generated_code:
                error_summary += f"\n\n🔍 DEBUG - Generated code:\n{generated_code[:800]}"

            return {
                "error": str(e),
                "summary": error_summary,
                "methodology": "Ошибка при обработке",
                "confidence": 0.0,
                "response_type": "error"
            }

    def _calculate_top_items_failsafe(self, df: pd.DataFrame, column_names: List[str], query: str) -> Dict[str, Any]:
        """
        FAILSAFE: Прямой расчет топ товаров без AI генерации кода
        Гарантированно правильный результат с РЕАЛЬНЫМИ данными
        """
        try:
            # Extract number from query (топ 5, топ 3, и т.д.)
            import re
            match = re.search(r'топ\s+(\d+)', query.lower())
            top_n = int(match.group(1)) if match else 5

            # Get product column (usually first column)
            product_col = df.columns[0]

            # Get numeric columns (sales/values)
            numeric_cols = [col for col in df.columns if df[col].dtype in ['int64', 'float64']]
            if not numeric_cols:
                raise Exception("Не найдено числовых колонок для расчета")

            # Use last numeric column as sales
            sales_col = numeric_cols[-1]

            # Group by product and sum sales
            product_sales = df.groupby(product_col)[sales_col].sum().sort_values(ascending=False)
            top_items = product_sales.head(top_n)

            # Format summary
            summary = f"Топ {top_n} товаров по продажам:\n\n"
            for i, (product, sales) in enumerate(top_items.items(), 1):
                summary += f"{i}. {product}: {sales:,.2f} руб.\n"
            summary = summary.strip()

            # Format key_findings
            key_findings = [f"{product}: {sales:,.2f}" for product, sales in top_items.items()]

            return {
                "summary": summary,
                "methodology": f"FAILSAFE MODE: Проанализированы РЕАЛЬНЫЕ данные из таблицы. Сгруппировано по '{product_col}', просуммированы '{sales_col}'. Найдено {len(product_sales)} уникальных товаров.",
                "key_findings": key_findings,
                "confidence": 0.99,
                "response_type": "analysis",
                "data": top_items.to_dict(),
                "structured_data": None,  # Упрощено - только расчеты!
                "code_generated": "# FAILSAFE MODE: Direct pandas calculation",
                "python_executed": True
            }
        except Exception as e:
            raise Exception(f"Failsafe top items calculation failed: {str(e)}")

    def _calculate_avg_price_failsafe(self, df: pd.DataFrame, column_names: List[str]) -> Dict[str, Any]:
        """
        FAILSAFE: Прямой расчет средней цены по поставщикам без AI генерации кода
        Гарантированно правильный результат
        """
        try:
            # Find columns
            supplier_col = column_names[1] if len(column_names) > 1 else df.columns[1]  # Usually column B

            # DEBUG: Log all numeric columns
            numeric_debug = []
            for col in df.columns:
                if df[col].dtype in ['int64', 'float64']:
                    col_idx = list(df.columns).index(col)
                    col_max = df[col].max()
                    col_samples = df[col].dropna().head(3).tolist()
                    numeric_debug.append(f"{col}(idx={col_idx}, max={col_max}, samples={col_samples})")

            # Find price column (numeric column with values < 100000)
            price_col = None
            for col in df.columns:
                if df[col].dtype in ['int64', 'float64']:
                    max_val = df[col].max()
                    if max_val < 100000 and max_val > 0:
                        price_col = col
                        break

            if not price_col:
                raise Exception("Не найдена колонка с ценами")

            # DEBUG: Get selected column info
            selected_idx = list(df.columns).index(price_col)
            selected_samples = df[price_col].dropna().head(5).tolist()

            # Remove duplicates before calculating average
            df_before = len(df)
            df_unique = df[[supplier_col, price_col]].drop_duplicates()
            df_after = len(df_unique)

            # Group by supplier and calculate mean
            avg_prices = df_unique.groupby(supplier_col)[price_col].mean().sort_values(ascending=False)

            # Format summary
            summary = "Средняя цена товаров у каждого поставщика:\n\n"
            for i, (supplier, avg_price) in enumerate(avg_prices.items(), 1):
                summary += f"{i}. {supplier}: {avg_price:,.2f} руб.\n"
            summary = summary.strip()

            # Format key_findings
            key_findings = [f"{supplier}: {avg_price:,.2f}" for supplier, avg_price in avg_prices.items()]

            return {
                "summary": summary,
                "methodology": f"FAILSAFE: Удалены дубликаты ({df_before}->{df_after} rows), сгруппировано по поставщикам ({supplier_col}), вычислена средняя цена для колонки '{price_col}' (idx={selected_idx}, samples={selected_samples}).",
                "key_findings": key_findings,
                "confidence": 0.99,
                "response_type": "analysis",
                "data": avg_prices.to_dict(),
                "structured_data": None,  # Упрощено - только расчеты!
                "code_generated": "# FAILSAFE MODE: Direct calculation",
                "python_executed": True
            }
        except Exception as e:
            raise Exception(f"Failsafe calculation failed: {str(e)}")

    def _generate_python_code(self, query: str, df: pd.DataFrame) -> str:
        """
        AI генерирует Python код для решения задачи
        """

        # Анализируем структуру данных
        data_info = self._analyze_dataframe(df)

        prompt = f"""You are a Python data analyst expert. Generate Python code to answer this question.

QUESTION: {query}

AVAILABLE DATA:
DataFrame 'df' with {len(df)} rows and columns:
{data_info}

SAMPLE DATA (first 5 rows):
{df.head().to_string()}

RULES FOR CODE GENERATION:
1. Use pandas for all data operations
2. Variable 'df' contains the data
3. Create a variable 'result' with the final answer
4. Create a variable 'summary' with human-readable explanation in Russian
5. Create a variable 'methodology' explaining what was calculated in Russian
6. Handle duplicates properly (GROUP BY when needed)
7. For "топ товаров" - group by product column and sum sales
8. For "топ поставщиков" - group by supplier column and sum sales
9. For "средняя цена" - use .mean() on PRICE column (NOT SUM!)
10. CRITICAL: When asked for AVERAGE PRICE - REMOVE DUPLICATES FIRST!
11. CRITICAL: For "средняя цена товаров у поставщика" - drop_duplicates by (Supplier, Product, Price) BEFORE calculating mean
12. CRITICAL: Data may contain duplicate rows for same product - deduplicate before averaging!
13. CRITICAL: NEVER calculate average as sum/count - use .mean() function directly!
14. Always aggregate duplicate entries for TOP/SUM queries
15. LIMIT TOP LISTS to maximum 5 items for readability
16. Use DOUBLE line break (\\n\\n) after title for better spacing
17. ⛔ CRITICAL: NEVER CREATE NEW DATAFRAMES OR DICTIONARIES WITH FAKE DATA!
18. ⛔ CRITICAL: ONLY USE EXISTING 'df' VARIABLE - DO NOT WRITE df = pd.DataFrame(...)!
19. ⛔ CRITICAL: Use df.columns[0], df.columns[1] to get REAL column names from existing df
20. ⛔ CRITICAL: ALL product names, suppliers, values MUST come from df - NO HARDCODED "Product A/B/C/D/E"!
21. CRITICAL: For "создай график/таблицу" - analyze df.groupby() FIRST, then format results
22. CRITICAL: NEVER write example data like {'Product E': 3000, 'Product F': 2500} - use df data!

REQUIRED OUTPUT VARIABLES:
- result: the computed answer (number, dataframe, or list)
- summary: string with the answer in Russian
- methodology: string explaining the calculation in Russian
- highlight_rows: (ONLY for "выдели" queries) list of row numbers to highlight (1-indexed, starting from 2 for data rows)

SPECIAL: HIGHLIGHT ROW QUERIES ("выдели строки где...")
If query asks to HIGHLIGHT rows ("выдели", "подсвети", "покрась"), you MUST:
1. Find matching rows based on condition
2. Create variable 'highlight_rows' with list of row numbers (1-indexed, data starts at row 2)
3. Set 'result' to number of matching rows
4. Set 'summary' to "Найдено X строк для выделения: [description]"

EXAMPLE CODE FOR "выдели строки где товар 2":
```python
# Find matching rows
matching_mask = df['Колонка A'] == 'Товар 2'
matching_indices = df[matching_mask].index.tolist()

# Convert to 1-indexed row numbers (data starts at row 2 in Google Sheets)
highlight_rows = [idx + 2 for idx in matching_indices]

result = len(highlight_rows)
summary = f"Найдено {{len(highlight_rows)}} строк с товаром 'Товар 2'"
methodology = "Выбраны все строки где колонка A (товар) = 'Товар 2'"
```

FORMATTING RULES FOR SUMMARY:
- Always use \\n for line breaks
- Format numbers with thousand separators: {{value:,.2f}}
- For TOP lists: put each item on NEW LINE
- Use clear structure: Title, then numbered list
- Keep it readable and well-spaced

EXAMPLE CODE FOR "средняя цена товаров у каждого поставщика":
```python
# IMPORTANT: Use .mean() for averages, NOT sum/count!
# Find columns
product_col = df.columns[0]  # Usually column A
supplier_col = df.columns[1]  # Usually column B
price_col = None
for col in df.columns:
    if df[col].dtype in ['int64', 'float64'] and df[col].max() < 100000:
        price_col = col
        break

# CRITICAL: Remove duplicates BEFORE calculating average!
# Data may have duplicate rows for same product
df_unique = df.drop_duplicates(subset=[supplier_col, product_col, price_col])

# Now group by supplier and calculate MEAN of prices
supplier_avg_price = df_unique.groupby(supplier_col)[price_col].mean().sort_values(ascending=False)

# Format result
result = supplier_avg_price.to_dict()
summary = "Средняя цена товаров у каждого поставщика:\\n\\n"
for i, (supplier, avg_price) in enumerate(supplier_avg_price.items(), 1):
    summary += f"{{i}}. {{supplier}}: {{avg_price:,.2f}} руб.\\n"
summary = summary.strip()
methodology = f"Удалены дубликаты, сгруппировано по поставщикам ({{supplier_col}}), вычислена средняя цена методом .mean() для колонки '{{price_col}}'"
```

EXAMPLE CODE FOR "топ 3 товара по продажам":
```python
# Group by product and sum sales
product_sales = df.groupby('Колонка A')['Колонка E'].sum().sort_values(ascending=False)
top3 = product_sales.head(3)

# Format result with CLEAR LINE BREAKS
result = top3.to_dict()
summary = "Топ 3 товара по продажам:\\n\\n"
for i, (product, sales) in enumerate(top3.items(), 1):
    summary += f"{{i}}. {{product}}: {{sales:,.2f}} руб.\\n"
summary = summary.strip()
methodology = f"Сгруппировано по товарам (Колонка A), просуммированы продажи (Колонка E). Всего уникальных товаров: {{len(product_sales)}}"
```

EXAMPLE CODE FOR "у какого поставщика больше всего продаж":
```python
# Group by supplier and sum sales
supplier_sales = df.groupby('Колонка B')['Колонка E'].sum().sort_values(ascending=False)
top_supplier = supplier_sales.index[0]
top_sales = supplier_sales.iloc[0]

# Format with TOP 5 for context
result = supplier_sales.head(5).to_dict()
summary = f"Топ поставщик: {{top_supplier}}\\n"
summary += f"Продажи: {{top_sales:,.2f}} руб.\\n\\n"
summary += "Топ 5 поставщиков:\\n\\n"
for i, (supplier, sales) in enumerate(supplier_sales.head(5).items(), 1):
    summary += f"{{i}}. {{supplier}}: {{sales:,.2f}} руб.\\n"
summary = summary.strip()
methodology = f"Сгруппировано по поставщикам (Колонка B), просуммированы продажи (Колонка E)"
```

EXAMPLE CODE FOR "создай график/диаграмму по топ 5 товарам":
```python
# ⛔ IMPORTANT: NEVER create new DataFrame or dict with fake data!
# ✅ ONLY use existing 'df' variable provided to you!

# Step 1: Get REAL column names from existing df
product_col = df.columns[0]  # This gets ACTUAL column name like "Товар", NOT "Колонка A"!
numeric_cols = [col for col in df.columns if df[col].dtype in ['int64', 'float64']]
sales_col = numeric_cols[-1] if numeric_cols else df.columns[-1]

print(f"DEBUG: Using columns: product={{product_col}}, sales={{sales_col}}")
print(f"DEBUG: Sample products from df: {{df[product_col].head(3).tolist()}}")  # ← This shows REAL products!

# Step 2: Analyze REAL data from df (DO NOT CREATE NEW DATA!)
product_sales = df.groupby(product_col)[sales_col].sum().sort_values(ascending=False)
top5 = product_sales.head(5)

print(f"DEBUG: Top 5 from df: {{top5.to_dict()}}")  # ← Must show REAL product names!

# Step 3: Format result - product names come FROM DF, not hardcoded!
result = top5.to_dict()  # ← This will have REAL names like {{'Товар 4': 3000, 'Товар 5': 2500}}
summary = "Топ 5 товаров по продажам:\\n\\n"
for i, (product, sales) in enumerate(top5.items(), 1):  # ← 'product' comes from df!
    summary += f"{{i}}. {{product}}: {{sales:,.2f}} руб.\\n"  # ← Shows REAL product name
summary = summary.strip()
methodology = f"Проанализированы РЕАЛЬНЫЕ данные из df. Сгруппировано по '{{product_col}}', просуммированы '{{sales_col}}'. Найдено {{len(product_sales)}} уникальных товаров."
```

⛔ WRONG CODE EXAMPLE (DO NOT DO THIS!):
```python
# ❌ NEVER write code like this:
result = {{'Product E': 3000, 'Product F': 2500}}  # ← WRONG! Fake data!
summary = "1. Product E: 3,000..."  # ← WRONG! Not from df!
```

NOW GENERATE CODE FOR THIS QUESTION:
{query}

Return ONLY the Python code, no explanations."""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a Python data analysis expert. Generate clean, working code.\n"
                        "⛔ CRITICAL: You MUST use ONLY the 'df' variable provided to you.\n"
                        "⛔ NEVER create new DataFrames with pd.DataFrame()\n"
                        "⛔ NEVER create dictionaries with hardcoded data like {'Product E': 3000}\n"
                        "⛔ ALL data MUST come from analyzing the existing 'df' variable using pandas operations\n"
                        "✅ CORRECT: df.groupby(df.columns[0])[df.columns[1]].sum()\n"
                        "❌ WRONG: result = {'Product E': 3000, 'Product F': 2500}"
                    )
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=1500
        )

        code = response.choices[0].message.content

        # Очищаем код от markdown если есть
        code = re.sub(r'^```python\n', '', code)
        code = re.sub(r'\n```$', '', code)
        code = re.sub(r'^```\n', '', code)

        return code

    def _validate_generated_code(self, code: str) -> None:
        """
        Валидирует сгенерированный код перед выполнением
        Выбрасывает исключение если находит запрещенные паттерны
        """
        # Запрещенные паттерны - признаки fake data
        forbidden_patterns = [
            r"pd\.DataFrame\s*\(",  # Создание нового DataFrame
            r"['\"]Product\s+[A-Z]['\"]\s*:",  # {'Product E': ..., 'Product F': ...}
            r"['\"]Item\s+\d+['\"]\s*:",  # {'Item 1': ..., 'Item 2': ...}
            r"result\s*=\s*\{[^}]*['\"]Product",  # result = {'Product A': 100}
            r"result\s*=\s*\{[^}]*['\"]Item",  # result = {'Item 1': 100}
        ]

        for pattern in forbidden_patterns:
            if re.search(pattern, code):
                raise ValueError(
                    f"⛔ CRITICAL ERROR: Generated code contains FAKE DATA pattern: {pattern}\n"
                    f"AI must use REAL data from 'df' variable, NOT create new dictionaries or DataFrames!\n"
                    f"Found in code:\n{code[:500]}"
                )

    def _execute_python_code(self, code: str, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Безопасно выполняет Python код и возвращает результат
        """
        # КРИТИЧЕСКАЯ ВАЛИДАЦИЯ: проверяем что код не создает fake data
        self._validate_generated_code(code)

        # Создаем безопасное окружение для выполнения
        safe_globals = {
            'df': df,
            'pd': pd,
            'np': np,
            'len': len,
            'sum': sum,
            'min': min,
            'max': max,
            'abs': abs,
            'round': round,
            'str': str,
            'int': int,
            'float': float,
            'list': list,
            'dict': dict,
            'enumerate': enumerate,
            'zip': zip,
            'sorted': sorted,
            'print': print  # Для отладки
        }

        safe_locals = {}

        # Перехватываем stdout для отладки
        old_stdout = sys.stdout
        sys.stdout = mystdout = StringIO()

        try:
            # Выполняем код
            exec(code, safe_globals, safe_locals)

            # Восстанавливаем stdout
            sys.stdout = old_stdout
            output = mystdout.getvalue()

            # Извлекаем результаты
            result = safe_locals.get('result', None)
            summary = safe_locals.get('summary', 'Результат вычислен')
            methodology = safe_locals.get('methodology', 'Python анализ данных')

            # Дополнительные переменные если есть
            key_findings = safe_locals.get('key_findings', [])
            confidence = safe_locals.get('confidence', 0.95)
            highlight_rows = safe_locals.get('highlight_rows', None)  # Для выделения строк

            return {
                'result': result,
                'summary': summary,
                'methodology': methodology,
                'key_findings': key_findings,
                'confidence': confidence,
                'highlight_rows': highlight_rows,  # Добавлено для выделения строк
                'code': code,
                'output': output
            }

        except Exception as e:
            sys.stdout = old_stdout
            error_msg = f"Ошибка выполнения кода: {str(e)}\n{traceback.format_exc()}"

            # Пытаемся выполнить fallback код
            fallback_code = self._generate_fallback_code(df, code, error_msg)
            if fallback_code:
                return self._execute_python_code(fallback_code, df)

            raise Exception(error_msg)

    def _generate_fallback_code(self, df: pd.DataFrame, failed_code: str, error: str) -> Optional[str]:
        """
        Генерирует исправленный код если первая попытка не удалась
        """
        prompt = f"""The following Python code failed with an error. Fix it.

FAILED CODE:
{failed_code}

ERROR:
{error}

DataFrame structure:
{df.dtypes}

Generate CORRECTED code that will work. Return ONLY the Python code."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=1500
            )

            fixed_code = response.choices[0].message.content
            fixed_code = re.sub(r'^```python\n', '', fixed_code)
            fixed_code = re.sub(r'\n```$', '', fixed_code)

            return fixed_code
        except:
            return None

    def _should_highlight_rows(self, query: str) -> bool:
        """
        Определяет, является ли запрос на РЕАЛЬНОЕ выделение строк цветом
        НЕ путать с "выдели топ 5" (покажи) и "выдели строки где..." (highlight)
        """
        query_lower = query.lower()

        # Если есть запрос на график/таблицу - это НЕ highlight
        if any(word in query_lower for word in ['график', 'диаграмм', 'таблиц', 'chart']):
            return False

        # "выдели топ" = покажи топ, НЕ highlight
        if 'выдели' in query_lower and 'топ' in query_lower:
            return False

        # Реальный highlight - с указанием условия "где"
        highlight_keywords = [
            'подсвети', 'покрась', 'highlight', 'mark', 'цвет',
            'закрась', 'раскрась', 'отметь'
        ]

        # "выдели" только если есть "где" или "с" (условие)
        if 'выдели' in query_lower:
            return 'где' in query_lower or 'с ' in query_lower or 'строк' in query_lower

        return any(word in query_lower for word in highlight_keywords)

    def _should_auto_execute_table(self, query: str) -> bool:
        """
        Определяет, нужно ли АВТОМАТИЧЕСКИ создать таблицу/график (без кнопки)
        Возвращает True только если пользователь ЯВНО просит: "построй график", "создай таблицу"
        """
        query_lower = query.lower()

        # Явные команды на создание таблицы/графика
        auto_execute_keywords = [
            'построй график', 'создай график', 'сделай график', 'нарисуй график',
            'построй диаграмм', 'создай диаграмм', 'сделай диаграмм',
            'построй таблиц', 'создай таблиц',
            'визуализируй', 'визуализ',
            'покажи в виде', 'отобрази',
            'build chart', 'create chart', 'make chart'
        ]

        return any(keyword in query_lower for keyword in auto_execute_keywords)

    def _should_create_table(self, query: str) -> bool:
        """
        Определяет, нужно ли создавать structured_data для таблицы/графика
        ВАЖНО: Таблицы создаются ТОЛЬКО если:
        1. Пользователь явно просит (построй таблицу, создай график, визуализируй)
        2. ИЛИ запрос подразумевает сравнение/рейтинг (топ-N, сравнение, средние по группам)
        НО НЕ если это запрос на выделение строк!
        """
        query_lower = query.lower()

        # Если запрос на выделение - НЕ создаем таблицу
        if self._should_highlight_rows(query):
            return False

        # Явный запрос на таблицу/график
        explicit_keywords = [
            'таблиц', 'график', 'диаграмм', 'визуализ', 'chart', 'table', 'plot',
            'построй', 'создай', 'покажи в виде', 'отобрази', 'нарисуй', 'сделай'
        ]
        if any(word in query_lower for word in explicit_keywords):
            return True

        # Запросы, которые логично визуализировать (топ-N, сравнение, средние по группам)
        # НО только предложить (показать кнопку), не автовыполнять
        implicit_keywords = [
            'топ', 'top', 'рейтинг', 'ranking', 'лучш', 'худш',
            'сравн', 'compare', 'comparison',
            'средн', 'average', 'mean',  # средние по группам
            'у каждого', 'по каждому', 'для каждого',  # группировка
            'больше всего', 'меньше всего',
            'лидер', 'аутсайдер'
        ]
        if any(word in query_lower for word in implicit_keywords):
            return True

        # По умолчанию - НЕ создаем таблицу (просто текстовый ответ)
        return False

    def _detect_chart_type(self, query: str) -> str:
        """
        Определяет рекомендуемый тип графика на основе запроса
        """
        query_lower = query.lower()

        # Гистограмма/столбчатая для сравнения
        if any(word in query_lower for word in ['топ', 'top', 'сравн', 'compare', 'больше', 'меньше']):
            return "column"

        # Линейный график для трендов
        if any(word in query_lower for word in ['тренд', 'trend', 'динамик', 'изменен', 'рост', 'падение']):
            return "line"

        # Круговая диаграмма для долей
        if any(word in query_lower for word in ['дол', 'процент', 'share', 'percent', 'распределение']):
            return "pie"

        # По умолчанию - столбчатая
        return "column"

    def _analyze_dataframe(self, df: pd.DataFrame) -> str:
        """
        Анализирует структуру DataFrame для AI
        """
        analysis = []

        for col in df.columns:
            dtype = df[col].dtype
            sample_values = df[col].dropna().head(3).tolist()

            # Определяем семантический тип колонки
            semantic_type = "unknown"
            if df[col].dtype == 'object':
                if any('Товар' in str(v) for v in sample_values):
                    semantic_type = "products"
                elif any('ООО' in str(v) or 'ИП' in str(v) for v in sample_values):
                    semantic_type = "suppliers/companies"
                else:
                    semantic_type = "text"
            elif df[col].dtype in ['int64', 'float64']:
                max_val = df[col].max()
                if max_val > 100000:
                    semantic_type = "sales/revenue (large numbers)"
                elif max_val > 1000:
                    semantic_type = "quantity/price (medium numbers)"
                else:
                    semantic_type = "small numbers/ids"

            analysis.append(f"- {col}: {dtype} ({semantic_type}), sample: {sample_values}")

        return '\n'.join(analysis)

    def _format_response(self, exec_result: Dict[str, Any], code: str, query: str) -> Dict[str, Any]:
        """
        Форматирует финальный ответ - УПРОЩЕННАЯ ВЕРСИЯ
        Фокус на точных расчетах, без создания таблиц/графиков
        """
        result = exec_result.get('result')

        # Конвертируем pandas объекты в сериализуемые
        if isinstance(result, pd.DataFrame):
            result_dict = result.to_dict('records')
        elif isinstance(result, pd.Series):
            result_dict = result.to_dict()
        else:
            result_dict = result

        # Форматируем key_findings для красивого отображения
        key_findings = exec_result.get('key_findings', [])
        if not key_findings and isinstance(result_dict, dict):
            key_findings = [f"{k}: {v:,.2f}" if isinstance(v, (int, float)) else f"{k}: {v}"
                          for k, v in list(result_dict.items())[:10]]  # Показываем до 10 элементов

        # DEBUG: Print generated code to console for debugging
        print("=" * 80)
        print("🐍 AI GENERATED PYTHON CODE:")
        print("=" * 80)
        print(code)
        print("=" * 80)
        print("📊 EXECUTION RESULT:")
        print(f"Summary: {exec_result.get('summary')}")
        print(f"Methodology: {exec_result.get('methodology')}")
        print("=" * 80)

        # УПРОЩЕННЫЙ ОТВЕТ - только расчеты!
        response_data = {
            "summary": exec_result.get('summary', 'Результат вычислен'),
            "methodology": exec_result.get('methodology', 'Автоматический анализ с помощью Python'),
            "key_findings": key_findings,
            "confidence": exec_result.get('confidence', 0.95),
            "response_type": "analysis",
            "data": result_dict,
            "structured_data": None,  # Больше не создаем таблицы!
            "code_generated": code[:500],  # Первые 500 символов кода для отладки
            "python_executed": True
        }

        return response_data

# Singleton
ai_executor = AICodeExecutor()

def get_ai_executor() -> AICodeExecutor:
    return ai_executor