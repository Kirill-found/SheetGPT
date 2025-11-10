# -*- coding: utf-8 -*-
"""Простой тест INDEX/MATCH постпроцессинга без зависимостей"""
import re
from typing import List, Dict, Any

def _analyze_column_types(column_names: List[str], sample_data: List[List[Any]]) -> Dict[str, str]:
    """Определяет типы данных в колонках"""
    column_types = {}

    if not sample_data or len(sample_data) == 0:
        return column_types

    for i, col_name in enumerate(column_names):
        # Смотрим на первые несколько значений
        values = [row[i] if i < len(row) else None for row in sample_data[:5]]
        values = [v for v in values if v is not None and v != ""]

        if not values:
            column_types[col_name] = "unknown"
            continue

        # Определяем тип
        if all(isinstance(v, (int, float)) for v in values):
            column_types[col_name] = "number"
        elif all(str(v).replace('.', '').replace(',', '').replace('%', '').replace('р', '').replace('p', '').strip().replace('-', '').isdigit() for v in values):
            column_types[col_name] = "number_formatted"
        else:
            column_types[col_name] = "text"

    return column_types

def fix_index_match(formula: str, column_names: List[str], sample_data: List[List[Any]]) -> str:
    """Исправляет INDEX/MATCH поиск текста в числовых столбцах"""

    if 'INDEX' not in formula.upper() or 'MATCH' not in formula.upper():
        return formula

    if not column_names or not sample_data:
        return formula

    # Анализируем типы данных в столбцах
    column_types = _analyze_column_types(column_names, sample_data)

    # Паттерн для INDEX(result_col; MATCH(lookup_value; search_col; 0))
    index_match_pattern = r'INDEX\(([^;]+);\s*MATCH\(([^;]+);\s*([^;]+);\s*0\)\)'

    def fix_index_match_columns(match):
        result_col = match.group(1).strip()
        lookup_value = match.group(2).strip()
        search_col = match.group(3).strip()

        # Извлекаем букву столбца для lookup_value (например, B2:B → B)
        lookup_col_letter = None
        lookup_match = re.search(r'\$?([A-Z]+)\d*:\$?[A-Z]+', lookup_value)
        if lookup_match:
            lookup_col_letter = lookup_match.group(1)

        # Извлекаем букву столбца для search_col (например, $H:$H → H)
        search_col_letter = None
        search_match = re.search(r'\$?([A-Z]+):\$?\1', search_col)
        if search_match:
            search_col_letter = search_match.group(1)

        # Извлекаем букву столбца для result_col (например, $I:$I → I)
        result_col_letter = None
        result_match = re.search(r'\$?([A-Z]+):\$?\1', result_col)
        if result_match:
            result_col_letter = result_match.group(1)

        if not lookup_col_letter or not search_col_letter or not result_col_letter:
            return match.group(0)  # Не можем разобрать, оставляем как есть

        # Определяем индексы столбцов (A=0, B=1, C=2, ...)
        lookup_col_idx = sum((ord(c) - ord('A') + 1) * (26 ** i) for i, c in enumerate(reversed(lookup_col_letter))) - 1
        search_col_idx = sum((ord(c) - ord('A') + 1) * (26 ** i) for i, c in enumerate(reversed(search_col_letter))) - 1
        result_col_idx = sum((ord(c) - ord('A') + 1) * (26 ** i) for i, c in enumerate(reversed(result_col_letter))) - 1

        # Проверяем валидность индексов
        if lookup_col_idx >= len(column_names) or search_col_idx >= len(column_names) or result_col_idx >= len(column_names):
            return match.group(0)

        # Получаем типы данных
        lookup_col_name = column_names[lookup_col_idx]
        search_col_name = column_names[search_col_idx]
        result_col_name = column_names[result_col_idx]

        lookup_type = column_types.get(lookup_col_name, "unknown")
        search_type = column_types.get(search_col_name, "unknown")
        result_type = column_types.get(result_col_name, "unknown")

        # ПРОВЕРКА ОШИБКИ: Если ищем текст в числовом столбце
        if lookup_type == "text" and search_type in ["number", "number_formatted"]:
            # Ищем правильный текстовый столбец рядом с search_col
            # Обычно это предыдущий столбец (например, H числа → G текст)
            correct_search_idx = None

            # Сначала проверяем столбец слева от search_col
            if search_col_idx > 0:
                neighbor_col_name = column_names[search_col_idx - 1]
                neighbor_type = column_types.get(neighbor_col_name, "unknown")
                if neighbor_type == "text" and neighbor_col_name:  # не пустой столбец
                    correct_search_idx = search_col_idx - 1

            # Если не нашли слева, ищем справа
            if correct_search_idx is None and search_col_idx + 1 < len(column_names):
                neighbor_col_name = column_names[search_col_idx + 1]
                neighbor_type = column_types.get(neighbor_col_name, "unknown")
                if neighbor_type == "text" and neighbor_col_name:
                    correct_search_idx = search_col_idx + 1

            # Если нашли правильный столбец, заменяем ссылки
            if correct_search_idx is not None:
                # Определяем букву для нового search_col
                correct_search_letter = chr(ord('A') + correct_search_idx)

                # Определяем букву для нового result_col (должен быть числовой столбец)
                # Обычно это исходный search_col (который был числовым)
                correct_result_letter = search_col_letter

                # Сохраняем $ если они были
                has_dollar = '$' in search_col
                dollar_prefix = '$' if has_dollar else ''

                # Формируем новые ссылки
                new_search_col = f"{dollar_prefix}{correct_search_letter}:{dollar_prefix}{correct_search_letter}"
                new_result_col = f"{dollar_prefix}{correct_result_letter}:{dollar_prefix}{correct_result_letter}"

                return f'INDEX({new_result_col}; MATCH({lookup_value}; {new_search_col}; 0))'

        # Если ошибки не обнаружено, возвращаем как есть
        return match.group(0)

    formula = re.sub(index_match_pattern, fix_index_match_columns, formula, flags=re.IGNORECASE)
    return formula


# Тестовые данные - точно как у пользователя
column_names = ["ФИО", "Отдел", "Стаж работы (лет)", "Оклад", "", "", "Отделы", "Базовый оклад"]
sample_data = [
    ["Иванов И.И.", "Аналитика", 3, "", "", "", "Аналитика", 55000],
    ["Петров П.П.", "HR", 7, "", "", "", "HR", 45000],
    ["Сидоров С.С.", "IT", 2, "", "", "", "IT", 70000]
]

print("=" * 80)
print("ТЕСТ INDEX/MATCH ПОСТПРОЦЕССИНГА")
print("=" * 80)
print()

# Анализ типов данных
print("Анализ типов данных:")
print("-" * 80)
column_types = _analyze_column_types(column_names, sample_data)
for i, (col_name, col_type) in enumerate(column_types.items()):
    col_letter = chr(ord('A') + i)
    sample_val = sample_data[0][i] if i < len(sample_data[0]) else ""
    print(f"  {col_letter}: {col_name:30} → {col_type:15} (пример: {sample_val})")
print()

print("ФОРМУЛА ПОЛЬЗОВАТЕЛЯ:")
print("-" * 80)
wrong = "=ARRAYFORMULA(IF(C2:C<5;INDEX($I:$I;MATCH(B2:B;$H:$H;0));INDEX($I:$I;MATCH(B2:B;$H:$H;0))*1.05))"
print(f"До:  {wrong}")
print()

print("ПРОБЛЕМА:")
print(f"  • B2:B (столбец B = 'Отдел') содержит: ['Аналитика', 'HR', 'IT'] — ТЕКСТ")
print(f"  • $H:$H (столбец H = 'Базовый оклад') содержит: [55000, 45000, 70000] — ЧИСЛА")
print(f"  • MATCH ищет 'Аналитика' в [55000, 45000, 70000] → #ERROR!")
print()

correct = fix_index_match(wrong, column_names, sample_data)

print(f"После: {correct}")
print()

print("РЕШЕНИЕ:")
print(f"  • $G:$G (столбец G = 'Отделы') содержит: ['Аналитика', 'HR', 'IT'] — ТЕКСТ")
print(f"  • MATCH теперь ищет 'Аналитика' в ['Аналитика', 'HR', 'IT'] → находит!")
print(f"  • INDEX возвращает значение из $H:$H по найденной позиции → 55000")
print()

# Проверка
has_correct_search = "$G:$G" in correct
has_correct_result = "$H:$H" in correct
no_wrong_col = "$I:$I" not in correct

print("ПРОВЕРКА:")
print(f"  {'✓' if has_correct_search else '✗'} Ищет в $G:$G (текст): {has_correct_search}")
print(f"  {'✓' if has_correct_result else '✗'} Возвращает из $H:$H (числа): {has_correct_result}")
print(f"  {'✓' if no_wrong_col else '✗'} Не использует $I:$I: {no_wrong_col}")
print()

if has_correct_search and has_correct_result and no_wrong_col:
    print("🎉 УСПЕХ! Постпроцессинг работает правильно!")
    exit(0)
else:
    print("❌ ОШИБКА! Постпроцессинг не исправил формулу!")
    exit(1)
