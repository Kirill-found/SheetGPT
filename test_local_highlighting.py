#!/usr/bin/env python3
"""
Локальный тест функции выделения
"""

import json
import re
from typing import Any, Dict, Optional

def _generate_highlighting_if_needed(query: str, result_data: Any) -> Optional[Dict[str, Any]]:
    """
    Определяет нужно ли выделение строк и генерирует данные для него
    """
    # Ключевые слова для выделения
    highlight_keywords = ['выдели', 'подсвет', 'отметь', 'покаж', 'highlight', 'mark', 'топ', 'лучш', 'худш', 'больш', 'меньш', 'максимальн', 'минимальн']

    query_lower = query.lower()
    needs_highlighting = any(kw in query_lower for kw in highlight_keywords)

    if not needs_highlighting:
        print(f"[X] No highlight keywords found in: {query}")
        return None

    print(f"[OK] Highlight keywords detected in query: {query}")

    try:
        # Пытаемся определить что выделять
        rows_to_highlight = []
        highlight_color = '#FFFF00'  # Жёлтый по умолчанию
        highlight_message = 'Выделены строки по запросу'

        print(f"📊 Result data type: {type(result_data)}")

        # Извлекаем число из запроса
        numbers = re.findall(r'\d+', query)
        count = 5  # По умолчанию 5
        if numbers:
            count = min(int(numbers[0]), 20)  # Максимум 20

        print(f"📊 Count to highlight: {count}")

        # Обрабатываем словарь с данными
        if isinstance(result_data, dict):
            print(f"📊 Dict keys: {list(result_data.keys())}")

            # Проверяем разные варианты ключей
            rows_data = None
            if 'rows' in result_data:
                rows_data = result_data['rows']
                print(f"✅ Found 'rows' key with {len(rows_data) if rows_data else 0} items")
            else:
                # Если данные прямо в словаре (key: value пары)
                print(f"⚠️ No 'rows' key, extracting from dict items")
                items = list(result_data.items())
                print(f"⚠️ Dict items: {items}")
                rows_data = [[k, v] for k, v in items if isinstance(v, (int, float))]
                if rows_data:
                    print(f"✅ Extracted {len(rows_data)} numeric items: {rows_data}")

            # Если есть данные и они являются списком
            if rows_data and isinstance(rows_data, list) and len(rows_data) > 0:
                print(f"📊 Processing {len(rows_data)} rows of data")

                # Пытаемся найти числовую колонку
                numeric_values = []
                for i, row in enumerate(rows_data):
                    if isinstance(row, (list, tuple)) and len(row) > 1:
                        try:
                            # Пытаемся взять второй элемент как число
                            val = float(row[1])
                            numeric_values.append((i + 2, val))  # +2 для строки в Sheets
                            print(f"  Row {i}: {row[0]} = {val}")
                        except (ValueError, TypeError) as e:
                            print(f"  Row {i}: Cannot convert to number: {row}")
                    elif isinstance(row, list) and len(row) == 2:
                        # Специальный случай для ['key', value]
                        try:
                            val = float(row[1])
                            numeric_values.append((i + 2, val))
                            print(f"  Row {i}: {row[0]} = {val}")
                        except:
                            pass

                if numeric_values:
                    # Сортируем по значению
                    numeric_values.sort(key=lambda x: x[1], reverse=True)
                    print(f"📊 Sorted numeric values: {numeric_values[:5]}")

                    if 'топ' in query_lower or 'лучш' in query_lower:
                        # Берём топ N
                        rows_to_highlight = [row[0] for row in numeric_values[:count]]
                        highlight_color = '#90EE90'  # Зелёный для топ значений
                        highlight_message = f'Выделены топ {count} товаров'
                        print(f"✅ Generated highlight rows: {rows_to_highlight}")

        # Если нашли строки для выделения
        if rows_to_highlight:
            result = {
                "action_type": "highlight_rows",
                "highlight_rows": rows_to_highlight,
                "highlight_color": highlight_color,
                "highlight_message": highlight_message
            }
            print(f"✅ Returning highlighting data: {result}")
            return result

        print(f"❌ No rows to highlight found")
        return None

    except Exception as e:
        print(f"❌ Error generating highlighting data: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_with_key_findings():
    """Тест с данными из key_findings"""
    query = "выдели топ 5 товаров по продажам"

    # Симулируем данные из key_findings
    key_findings = [
        "Товар G: 4,000.00",
        "Товар D: 3,000.00",
        "Товар B: 2,500.00",
        "Товар I: 2,200.00",
        "Товар J: 1,800.00"
    ]

    # Парсим key_findings в словарь
    result_dict = {}
    for finding in key_findings:
        if ':' in finding:
            parts = finding.split(':', 1)
            key = parts[0].strip()
            value_str = parts[1].strip().replace(',', '')
            try:
                value = float(value_str)
                result_dict[key] = value
            except ValueError:
                result_dict[key] = value_str

    print(f"\n=== TEST 1: Key findings dict ===")
    print(f"Query: {query}")
    print(f"Result dict: {result_dict}")

    result = _generate_highlighting_if_needed(query, result_dict)
    print(f"Result: {json.dumps(result, ensure_ascii=False, indent=2) if result else 'None'}")

    return result

def test_with_rows_data():
    """Тест с данными в формате rows"""
    query = "выдели топ 5 товаров"

    result_dict = {
        "rows": [
            ["Товар A", 1500],
            ["Товар B", 2500],
            ["Товар C", 500],
            ["Товар D", 3000],
            ["Товар E", 1200],
            ["Товар F", 800],
            ["Товар G", 4000],
            ["Товар H", 600],
            ["Товар I", 2200],
            ["Товар J", 1800]
        ]
    }

    print(f"\n=== TEST 2: Rows format ===")
    print(f"Query: {query}")
    print(f"Result dict keys: {list(result_dict.keys())}")

    result = _generate_highlighting_if_needed(query, result_dict)
    print(f"Result: {json.dumps(result, ensure_ascii=False, indent=2) if result else 'None'}")

    return result

if __name__ == "__main__":
    print("=" * 60)
    print("TESTING HIGHLIGHTING FUNCTION LOCALLY")
    print("=" * 60)

    # Тест 1: С данными из key_findings
    result1 = test_with_key_findings()

    # Тест 2: С данными в формате rows
    result2 = test_with_rows_data()

    print("\n" + "=" * 60)
    print("SUMMARY:")
    print(f"Test 1 (key_findings): {'✅ PASSED' if result1 else '❌ FAILED'}")
    print(f"Test 2 (rows format): {'✅ PASSED' if result2 else '❌ FAILED'}")
    print("=" * 60)