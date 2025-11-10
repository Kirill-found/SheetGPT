# -*- coding: utf-8 -*-
"""Проверка что API возвращает в insights"""
import json

# Читаем ответ API
with open('C:/SheetGPT/api_response.json', 'r', encoding='utf-8') as f:
    response = json.load(f)

print("=" * 80)
print("АНАЛИЗ ОТВЕТА API")
print("=" * 80)
print()

print("Структура ответа:")
print(f"  response_type: {response.get('response_type')}")
print(f"  formula field: {response.get('formula')}")
print(f"  target_cell: {response.get('target_cell')}")
print()

insights = response.get('insights', [])
print(f"insights array: {len(insights)} элементов")
print()

if insights:
    for i, insight in enumerate(insights):
        print(f"insights[{i}]:")
        print(f"  type: {insight.get('type')}")
        if insight.get('type') == 'insert_formula':
            config = insight.get('config', {})
            print(f"  config.cell: {config.get('cell')}")
            formula = config.get('formula', '')
            print(f"  config.formula:")
            print(f"    {formula}")
            print()

            # Проверяем формулу
            print("ПРОВЕРКА ФОРМУЛЫ:")
            has_g = '$G:' in formula or 'G:G' in formula
            has_h = '$H:' in formula or 'H:H' in formula
            has_i = '$I:' in formula or 'I:I' in formula

            print(f"  ✓ Ищет в $G:$G (текст - Отделы): {has_g}")
            print(f"  ✓ Возвращает из $H:$H (числа - Оклад): {has_h}")
            print(f"  ✓ НЕ использует $I:$I: {not has_i}")
            print()

            if has_g and has_h and not has_i:
                print("🎉 ФОРМУЛА ПРАВИЛЬНАЯ!")
                print()
                print("ВЫВОД:")
                print("  API возвращает корректную формулу в insights[0].config.formula")
                print("  Бэкенд работает ПРАВИЛЬНО!")
                print()
                print("  Проблема скорее всего в одном из:")
                print("  1. Кэш расширения Google Apps Script")
                print("  2. Расширение использует старую версию кода")
                print("  3. Нужно обновить расширение в Google Sheets")
            else:
                print("❌ ФОРМУЛА НЕПРАВИЛЬНАЯ")
                print("  Нужна дополнительная отладка бэкенда")
        print()
