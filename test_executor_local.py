"""
Test AI Code Executor LOCALLY to see generated Python code
"""

import sys
sys.path.insert(0, r'C:\SheetGPT\backend')

from app.services.ai_code_executor import get_ai_executor

# Test data
column_names = ["Kolonna A", "Kolonna B", "Kolonna C", "Kolonna D", "Kolonna E"]

sheet_data = [
    ["Tovar 1", "OOO Vremya", 5000, 2, 10000],
    ["Tovar 2", "OOO Radost", 3500, 3, 10500],
    ["Tovar 3", "OOO Kosmos", 4500, 1, 4500],  # Price 4500
    ["Tovar 4", "OOO Kosmos", 5000, 2, 10000],  # Price 5000
    ["Tovar 5", "OOO Kosmos", 4200, 1, 4200],   # Price 4200
    ["Tovar 6", "OOO Kosmos", 3800, 2, 7600],   # Price 3800
    ["Tovar 7", "OOO Kosmos", 4100, 1, 4100],   # Price 4100
    ["Tovar 8", "OOO Kosmos", 4335, 2, 8670],   # Price 4335 (FIXED: was 3335)
    # Kosmos: 6 items, sum=25935, avg=4322.50
    ["Tovar 9", "OOO Vremya", 6000, 1, 6000],
    ["Tovar 10", "OOO Radost", 4000, 2, 8000],
]

query = "kakaya srednyaya tsena tovarov u kazhdogo postavshchika"

print("="*80)
print("LOCAL TEST: AI Code Executor")
print("="*80)
print(f"\nExpected for OOO Kosmos: 4322.50 (25935 / 6)\n")

try:
    executor = get_ai_executor()
    result = executor.process_with_code(
        query=query,
        column_names=column_names,
        sheet_data=sheet_data,
        history=[]
    )

    print("="*80)
    print("RESULT KEYS:")
    print("="*80)
    print(list(result.keys()))
    print()

    if "code_generated" in result:
        print("="*80)
        print("GENERATED PYTHON CODE:")
        print("="*80)
        print(result["code_generated"])
        print()
    else:
        print("WARNING: No code_generated in result!")

    if "summary" in result:
        print("="*80)
        print("SUMMARY:")
        print("="*80)
        print(result["summary"])
        print()

    if "methodology" in result:
        print("="*80)
        print("METHODOLOGY:")
        print("="*80)
        print(result["methodology"])
        print()

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
