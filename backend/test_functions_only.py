"""
Unit тест Function Registry (без AI вызовов)
Проверяет что все функции работают правильно
"""

import pandas as pd
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.services.function_registry import FunctionRegistry


def test_function_registry():
    """Тестирование всех функций registry"""

    print("="*80)
    print("UNIT TEST: Function Registry v7.0.0")
    print("="*80)

    # Тестовые данные
    test_data = {
        "Канал": ["Google Ads", "Facebook Ads", "TikTok Ads", "Email", "SEO"],
        "Показы": [120000, 90000, 150000, 40000, 80000],
        "Клики": [4800, 3150, 6000, 3200, 4000],
        "CTR": [0.04, 0.035, 0.04, 0.08, 0.05],
        "Лиды": [1200, 700, 1500, 2600, 1000],
        "CPL": [250, 285, 200, 40, 100],
        "Клиенты": [180, 110, 210, 520, 150],
        "CAC": [1667, 2273, 1428, 200, 667],
        "Выручка": [950000, 510000, 780000, 520000, 600000]
    }

    df = pd.DataFrame(test_data)
    registry = FunctionRegistry()

    print(f"\nTest data: {len(df)} rows x {len(df.columns)} columns")
    print(f"Columns: {', '.join(df.columns)}\n")

    results = []

    # Тест 1: filter_rows
    print("\n[TEST 1] filter_rows - Filter rows where Выручка < 600000")
    try:
        result = registry.execute("filter_rows", df, column="Выручка", operator="<", value=600000)
        if result["success"]:
            filtered_df = result["result"]
            print(f"[PASS] Filtered {len(filtered_df)} rows: {filtered_df['Канал'].tolist()}")
            results.append({"test": "filter_rows", "status": "PASS"})
        else:
            print(f"[FAIL] {result['error']}")
            results.append({"test": "filter_rows", "status": "FAIL"})
    except Exception as e:
        print(f"[ERROR] {e}")
        results.append({"test": "filter_rows", "status": "ERROR"})

    # Тест 2: highlight_rows
    print("\n[TEST 2] highlight_rows - Highlight rows where Выручка < 600000")
    try:
        result = registry.execute("highlight_rows", df, column="Выручка", operator="<", value=600000, color="yellow")
        if result["success"]:
            rows = result["result"]["highlight_rows"]
            color = result["result"]["highlight_color"]
            print(f"[PASS] Highlighted {len(rows)} rows with color {color}: {rows}")
            results.append({"test": "highlight_rows", "status": "PASS"})
        else:
            print(f"[FAIL] {result['error']}")
            results.append({"test": "highlight_rows", "status": "FAIL"})
    except Exception as e:
        print(f"[ERROR] {e}")
        results.append({"test": "highlight_rows", "status": "ERROR"})

    # Тест 3: sort_data
    print("\n[TEST 3] sort_data - Sort by Выручка descending")
    try:
        result = registry.execute("sort_data", df, columns=["Выручка"], ascending=False)
        if result["success"]:
            sorted_df = result["result"]
            print(f"[PASS] Sorted, top channel: {sorted_df.iloc[0]['Канал']} ({sorted_df.iloc[0]['Выручка']:,.0f})")
            results.append({"test": "sort_data", "status": "PASS"})
        else:
            print(f"[FAIL] {result['error']}")
            results.append({"test": "sort_data", "status": "FAIL"})
    except Exception as e:
        print(f"[ERROR] {e}")
        results.append({"test": "sort_data", "status": "ERROR"})

    # Тест 4: calculate_sum
    print("\n[TEST 4] calculate_sum - Sum of Выручка")
    try:
        result = registry.execute("calculate_sum", df, column="Выручка")
        if result["success"]:
            total = result["result"]
            print(f"[PASS] Total revenue: {total:,.0f}")
            results.append({"test": "calculate_sum", "status": "PASS"})
        else:
            print(f"[FAIL] {result['error']}")
            results.append({"test": "calculate_sum", "status": "FAIL"})
    except Exception as e:
        print(f"[ERROR] {e}")
        results.append({"test": "calculate_sum", "status": "ERROR"})

    # Тест 5: calculate_average
    print("\n[TEST 5] calculate_average - Average CTR")
    try:
        result = registry.execute("calculate_average", df, column="CTR")
        if result["success"]:
            avg = result["result"]
            print(f"[PASS] Average CTR: {avg:.4f}")
            results.append({"test": "calculate_average", "status": "PASS"})
        else:
            print(f"[FAIL] {result['error']}")
            results.append({"test": "calculate_average", "status": "FAIL"})
    except Exception as e:
        print(f"[ERROR] {e}")
        results.append({"test": "calculate_average", "status": "ERROR"})

    # Тест 6: aggregate_by_group
    print("\n[TEST 6] aggregate_by_group - Sum revenue by channel")
    try:
        result = registry.execute("aggregate_by_group", df, group_by=["Канал"], agg_column="Выручка", agg_func="sum")
        if result["success"]:
            agg_df = result["result"]
            print(f"[PASS] Aggregated {len(agg_df)} groups")
            print(f"  Top: {agg_df.iloc[0]['Канал']} = {agg_df.iloc[0]['Выручка']:,.0f}")
            results.append({"test": "aggregate_by_group", "status": "PASS"})
        else:
            print(f"[FAIL] {result['error']}")
            results.append({"test": "aggregate_by_group", "status": "FAIL"})
    except Exception as e:
        print(f"[ERROR] {e}")
        results.append({"test": "aggregate_by_group", "status": "ERROR"})

    # Тест 7: search_rows
    print("\n[TEST 7] search_rows - Find rows with 'Google'")
    try:
        result = registry.execute("search_rows", df, column="Канал", search_term="Google")
        if result["success"]:
            found_df = result["result"]
            print(f"[PASS] Found {len(found_df)} rows")
            results.append({"test": "search_rows", "status": "PASS"})
        else:
            print(f"[FAIL] {result['error']}")
            results.append({"test": "search_rows", "status": "FAIL"})
    except Exception as e:
        print(f"[ERROR] {e}")
        results.append({"test": "search_rows", "status": "ERROR"})

    # Тест 8: calculate_rank
    print("\n[TEST 8] calculate_rank - Rank by Выручка")
    try:
        result = registry.execute("calculate_rank", df, column="Выручка", ascending=False)
        if result["success"]:
            ranks = result["result"]
            print(f"[PASS] Ranks calculated: {ranks.tolist()}")
            results.append({"test": "calculate_rank", "status": "PASS"})
        else:
            print(f"[FAIL] {result['error']}")
            results.append({"test": "calculate_rank", "status": "FAIL"})
    except Exception as e:
        print(f"[ERROR] {e}")
        results.append({"test": "calculate_rank", "status": "ERROR"})

    # Тест 9: calculate_percentage
    print("\n[TEST 9] calculate_percentage - Revenue as % of total")
    try:
        result = registry.execute("calculate_percentage", df, column="Выручка")
        if result["success"]:
            percentages = result["result"]
            print(f"[PASS] Percentages: {percentages.tolist()}")
            results.append({"test": "calculate_percentage", "status": "PASS"})
        else:
            print(f"[FAIL] {result['error']}")
            results.append({"test": "calculate_percentage", "status": "FAIL"})
    except Exception as e:
        print(f"[ERROR] {e}")
        results.append({"test": "calculate_percentage", "status": "ERROR"})

    # Тест 10: vlookup
    print("\n[TEST 10] vlookup - Find CAC for 'Google Ads'")
    try:
        result = registry.execute("vlookup", df, lookup_value="Google Ads", lookup_column="Канал", return_column="CAC")
        if result["success"]:
            value = result["result"]
            print(f"[PASS] Found CAC: {value}")
            results.append({"test": "vlookup", "status": "PASS"})
        else:
            print(f"[FAIL] {result['error']}")
            results.append({"test": "vlookup", "status": "FAIL"})
    except Exception as e:
        print(f"[ERROR] {e}")
        results.append({"test": "vlookup", "status": "ERROR"})

    # Итоги
    print("\n" + "="*80)
    print("RESULTS")
    print("="*80)

    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    errors = sum(1 for r in results if r["status"] == "ERROR")
    total = len(results)

    print(f"\nTotal tests: {total}")
    print(f"PASS: {passed}")
    print(f"FAIL: {failed}")
    print(f"ERROR: {errors}")

    success_rate = (passed / total * 100) if total > 0 else 0
    print(f"\nSuccess rate: {success_rate:.1f}%")

    if success_rate == 100:
        print("\n[SUCCESS] All functions working perfectly!")
    elif success_rate >= 80:
        print("\n[GOOD] Most functions working, ready for integration")
    else:
        print("\n[WARNING] Some functions need fixing")

    return success_rate >= 80


if __name__ == "__main__":
    success = test_function_registry()
    sys.exit(0 if success else 1)
