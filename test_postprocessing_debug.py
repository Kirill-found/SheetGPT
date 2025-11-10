# -*- coding: utf-8 -*-
"""Тест постпроцессинга INDEX/MATCH на ТОЧНОЙ формуле пользователя"""
import re

# ТОЧНАЯ формула которую видит пользователь из скриншота
user_formula = "=ARRAYFORMULA(IF(C2:C<5;INDEX($I:$I;MATCH(B2:B;$H:$H;0));INDEX($I:$I;MATCH(B2:B;$H:$H;0))*1.05))"

# Regex паттерн из ai_service.py строка 238
index_match_pattern = r'INDEX\(([^;]+);\s*MATCH\(([^;]+);\s*([^;]+);\s*0\)\)'

print("=" * 80)
print("ПРОВЕРКА REGEX НА ФОРМУЛЕ ПОЛЬЗОВАТЕЛЯ")
print("=" * 80)
print()
print("Формула:")
print(user_formula)
print()

# Ищем все совпадения
matches = list(re.finditer(index_match_pattern, user_formula, flags=re.IGNORECASE))
print(f"Найдено совпадений: {len(matches)}")
print()

if matches:
    for i, match in enumerate(matches):
        print(f"Совпадение {i+1}:")
        print(f"  Полная строка: {match.group(0)}")
        print(f"  result_col: {match.group(1)}")
        print(f"  lookup_value: {match.group(2)}")
        print(f"  search_col: {match.group(3)}")
        print()

        # Разбираем result_col
        result_col = match.group(1).strip()
        result_match = re.search(r'\$?([A-Z]+):\$?\1', result_col)
        if result_match:
            result_letter = result_match.group(1)
            print(f"  result_col letter: {result_letter}")

        # Разбираем search_col
        search_col = match.group(3).strip()
        search_match = re.search(r'\$?([A-Z]+):\$?\1', search_col)
        if search_match:
            search_letter = search_match.group(1)
            print(f"  search_col letter: {search_letter}")

        # Разбираем lookup_value
        lookup_value = match.group(2).strip()
        lookup_match = re.search(r'\$?([A-Z]+)\d*:\$?[A-Z]+', lookup_value)
        if lookup_match:
            lookup_letter = lookup_match.group(1)
            print(f"  lookup_value letter: {lookup_letter}")

        print()

    print("✅ REGEX СРАБАТЫВАЕТ!")
    print()
    print("ВЫВОД:")
    print("  Постпроцессинг ДОЛЖЕН перехватывать эту формулу")
    print("  Проблема скорее всего НЕ в regex паттерне")
else:
    print("❌ REGEX НЕ СРАБАТЫВАЕТ!")
    print()
    print("ВЫВОД:")
    print("  Нужно исправить regex паттерн")
    print("  Возможно проблема в пробелах или других символах")

print()
print("=" * 80)
print("СЛЕДУЮЩИЙ ШАГ: Проверить почему постпроцессинг не исправляет формулу")
print("=" * 80)
