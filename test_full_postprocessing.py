# -*- coding: utf-8 -*-
"""Полная симуляция постпроцессинга INDEX/MATCH"""
import re
from typing import List, Dict, Any

# Данные из скриншота пользователя
column_names = ["Ф.И.О.", "Отдел", "Стаж работы", "Оклад, руб.", "", "", "Отделы", "Оклад"]
sample_data = [
    ["Баканов", "Аналитика", 11, "", "", "", "Бухгалтерия", 55000],
    ["Белокоса", "АСУ", 3, "", "", "", "АСУ", 70000],
    ["Иваненко", "Бухгалтерия", 8, "", "", "", "Статистика", 60000]
]

# ТОЧНАЯ формула которую видит пользователь
user_formula = "=ARRAYFORMULA(IF(C2:C<5;INDEX($I:$I;MATCH(B2:B;$H:$H;0));INDEX($I:$I;MATCH(B2:B;$H:$H;0))*1.05))"

def analyze_column_types(column_names: List[str], sample_data: List[List[Any]]) -> Dict[str, str]:
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
            # Все числа - это числовой столбец
            column_types[col_name] = "number"
        elif all(isinstance(v, str) for v in values):
            # Все строки - это текстовый столбец
            column_types[col_name] = "text"
        else:
            column_types[col_name] = "mixed"

    return column_types

def fix_index_match_formula(formula: str, column_names: List[str], sample_data: List[List[Any]]) -> str:
    """Исправляет INDEX/MATCH формулы с неправильными ссылками"""

    if 'INDEX' not in formula.upper() or 'MATCH' not in formula.upper():
        return formula

    if not column_names or not sample_data:
        return formula

    # Анализируем типы данных
    column_types = analyze_column_types(column_names, sample_data)

    print("Типы столбцов:")
    for name, type_ in column_types.items():
        print(f"  {name}: {type_}")
    print()

    # Паттерн для INDEX(result_col; MATCH(lookup_value; search_col; 0))
    index_match_pattern = r'INDEX\(([^;]+);\s*MATCH\(([^;]+);\s*([^;]+);\s*0\)\)'

    def fix_index_match_columns(match):
        result_col = match.group(1).strip()
        lookup_value = match.group(2).strip()
        search_col = match.group(3).strip()

        print(f"Обрабатываю: {match.group(0)}")
        print(f"  result_col: {result_col}")
        print(f"  lookup_value: {lookup_value}")
        print(f"  search_col: {search_col}")

        # Извлекаем буквы столбцов
        lookup_col_letter = None
        lookup_match = re.search(r'\$?([A-Z]+)\d*:\$?[A-Z]+', lookup_value)
        if lookup_match:
            lookup_col_letter = lookup_match.group(1)

        search_col_letter = None
        search_match = re.search(r'\$?([A-Z]+):\$?\1', search_col)
        if search_match:
            search_col_letter = search_match.group(1)

        result_col_letter = None
        result_match = re.search(r'\$?([A-Z]+):\$?\1', result_col)
        if result_match:
            result_col_letter = result_match.group(1)

        if not lookup_col_letter or not search_col_letter or not result_col_letter:
            print("  -> Не могу разобрать, оставляю как есть")
            return match.group(0)

        print(f"  lookup_col_letter: {lookup_col_letter}")
        print(f"  search_col_letter: {search_col_letter}")
        print(f"  result_col_letter: {result_col_letter}")

        # Определяем индексы
        lookup_col_idx = sum((ord(c) - ord('A') + 1) * (26 ** i) for i, c in enumerate(reversed(lookup_col_letter))) - 1
        search_col_idx = sum((ord(c) - ord('A') + 1) * (26 ** i) for i, c in enumerate(reversed(search_col_letter))) - 1
        result_col_idx = sum((ord(c) - ord('A') + 1) * (26 ** i) for i, c in enumerate(reversed(result_col_letter))) - 1

        print(f"  lookup_col_idx: {lookup_col_idx}")
        print(f"  search_col_idx: {search_col_idx}")
        print(f"  result_col_idx: {result_col_idx}")

        # Проверяем валидность
        if lookup_col_idx >= len(column_names) or search_col_idx >= len(column_names):
            print("  -> lookup или search выходит за пределы, оставляю как есть")
            return match.group(0)

        # Получаем типы данных
        lookup_col_name = column_names[lookup_col_idx]
        search_col_name = column_names[search_col_idx]
        result_col_name = column_names[result_col_idx] if result_col_idx < len(column_names) else None

        print(f"  lookup_col_name: {lookup_col_name}")
        print(f"  search_col_name: {search_col_name}")
        print(f"  result_col_name: {result_col_name}")

        lookup_type = column_types.get(lookup_col_name, "unknown")
        search_type = column_types.get(search_col_name, "unknown")
        result_type = column_types.get(result_col_name, "unknown") if result_col_name else "unknown"

        print(f"  lookup_type: {lookup_type}")
        print(f"  search_type: {search_type}")
        print(f"  result_type: {result_type}")

        # ПРОВЕРКА ОШИБКИ: Если ищем текст в числовом столбце
        if lookup_type == "text" and search_type in ["number", "number_formatted"]:
            print("  -> ОШИБКА ОБНАРУЖЕНА: ищем текст в числовом столбце!")

            # Ищем правильный текстовый столбец
            correct_search_idx = None

            # Проверяем слева
            if search_col_idx > 0:
                neighbor_col_name = column_names[search_col_idx - 1]
                neighbor_type = column_types.get(neighbor_col_name, "unknown")
                print(f"  -> Проверяю слева: {neighbor_col_name} ({neighbor_type})")
                if neighbor_type == "text" and neighbor_col_name:
                    correct_search_idx = search_col_idx - 1
                    print(f"  -> НАШЕЛ правильный столбец слева: {neighbor_col_name}")

            # Если не нашли слева, ищем справа
            if correct_search_idx is None and search_col_idx + 1 < len(column_names):
                neighbor_col_name = column_names[search_col_idx + 1]
                neighbor_type = column_types.get(neighbor_col_name, "unknown")
                print(f"  -> Проверяю справа: {neighbor_col_name} ({neighbor_type})")
                if neighbor_type == "text" and neighbor_col_name:
                    correct_search_idx = search_col_idx + 1
                    print(f"  -> НАШЕЛ правильный столбец справа: {neighbor_col_name}")

            # Если нашли правильный столбец, заменяем ссылки
            if correct_search_idx is not None:
                correct_search_letter = chr(ord('A') + correct_search_idx)
                correct_result_letter = search_col_letter

                has_dollar = '$' in search_col
                dollar_prefix = '$' if has_dollar else ''

                new_search_col = f"{dollar_prefix}{correct_search_letter}:{dollar_prefix}{correct_search_letter}"
                new_result_col = f"{dollar_prefix}{correct_result_letter}:{dollar_prefix}{correct_result_letter}"

                fixed = f'INDEX({new_result_col}; MATCH({lookup_value}; {new_search_col}; 0))'
                print(f"  -> ИСПРАВЛЕНО: {fixed}")
                return fixed
            else:
                print("  -> НЕ НАШЕЛ подходящий текстовый столбец")
        else:
            print("  -> Ошибки не обнаружено")

        return match.group(0)

    fixed_formula = re.sub(index_match_pattern, fix_index_match_columns, formula, flags=re.IGNORECASE)
    return fixed_formula

print("=" * 80)
print("ПОЛНАЯ СИМУЛЯЦИЯ ПОСТПРОЦЕССИНГА INDEX/MATCH")
print("=" * 80)
print()
print("Формула ДО:")
print(user_formula)
print()

fixed = fix_index_match_formula(user_formula, column_names, sample_data)

print()
print("=" * 80)
print("Формула ПОСЛЕ:")
print(fixed)
print()

if fixed != user_formula:
    print("РЕЗУЛЬТАТ: Формула была исправлена!")
    print()
    print("Проверка исправлений:")
    has_g = 'G:G' in fixed or '$G:' in fixed
    has_h = 'H:H' in fixed or '$H:' in fixed
    no_i = 'I:I' not in fixed and '$I:' not in fixed
    print(f"  Ищет в G:G (текст): {has_g}")
    print(f"  Возвращает из H:H (числа): {has_h}")
    print(f"  НЕ использует I:I: {no_i}")

    if has_g and has_h and no_i:
        print()
        print("ВЫВОД: Постпроцессинг работает ИДЕАЛЬНО!")
    else:
        print()
        print("ВЫВОД: Постпроцессинг работает, но что-то не так...")
else:
    print("РЕЗУЛЬТАТ: Формула НЕ была исправлена!")
    print()
    print("ВЫВОД: Нужна дополнительная отладка")
