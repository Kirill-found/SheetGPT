#!/usr/bin/env python3
"""
Локальное воспроизведение ошибки .dtype
Тестируем с точными данными пользователя
"""

import sys
import os
import asyncio
import pandas as pd

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'app'))

from services.ai_function_caller import AIFunctionCaller

# Данные из скриншота пользователя
query = "выдели строки где ОП меньше 20 тысяч"
column_names = ["Щетки", "Заказали на сумму", "ОП", "ОП в %", "Товар", "Сумма продаж", "ABC по прибыли"]
sheet_data = [
    ["Щетка 1", "р.100 000", 15000, "15%", "Товар A", "р.120 000", "A"],
    ["Щетка 2", "р.200 000", 35000, "17.5%", "Товар B", "р.220 000", "A"],
    ["Щетка 3", "р.50 000", 8000, "16%", "Товар C", "р.55 000", "B"],
    ["Щетка 4", "р.150 000", 25000, "16.7%", "Товар D", "р.160 000", "A"],
    ["Щетка 5", "р.80 000", 12000, "15%", "Товар E", "р.90 000", "B"]
]

async def test():
    print("="*80)
    print("LOCAL DEBUG TEST - Reproducing user's .dtype error")
    print("="*80)
    print(f"\nQuery: {query}")
    print(f"Columns: {column_names}")
    print(f"\nData sample:")
    for i, row in enumerate(sheet_data[:2]):
        print(f"  Row {i}: {row}")

    # Create DataFrame
    df = pd.DataFrame(sheet_data, columns=column_names)
    print(f"\nDataFrame shape: {df.shape}")
    print(f"OP column dtype: {df['ОП'].dtype}")
    print(f"OP values: {df['ОП'].tolist()}")

    # Test with AIFunctionCaller
    print("\n" + "="*80)
    print("Testing with AIFunctionCaller (v7.2.1 with auto-fix)")
    print("="*80)

    try:
        caller = AIFunctionCaller()
        result = await caller.process_query(
            query=query,
            df=df,
            column_names=column_names,
            sheet_data=sheet_data
        )

        print("\n[SUCCESS] No error!")
        print(f"\nResult keys: {result.keys()}")

        if "highlight_rows" in result:
            print(f"\nHighlight rows: {result['highlight_rows']}")
            print(f"Color: {result.get('highlight_color')}")
            print(f"Message: {result.get('highlight_message')}")

        if "error" in str(result) or "dtype" in str(result).lower():
            print("\n[FAIL] Result contains error or dtype!")
            print(f"Result: {result}")
        else:
            print("\n[TEST PASSED]")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
