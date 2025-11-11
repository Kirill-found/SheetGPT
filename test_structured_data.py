"""Test structured_data in HARDCODED response"""

import sys
sys.path.insert(0, r'C:\SheetGPT\backend')

from app.services.ai_service import get_ai_service

# Test data
column_names = ["Kolonna A", "Kolonna B", "Kolonna C", "Kolonna D", "Kolonna E"]

sheet_data = [
    ["Tovar 1", "OOO Vremya", 5000, 2, 10000],
    ["Tovar 2", "OOO Radost", 3500, 3, 10500],
    ["Tovar 3", "OOO Kosmos", 4500, 1, 4500],
    ["Tovar 4", "OOO Kosmos", 5000, 2, 10000],
    ["Tovar 5", "OOO Kosmos", 4200, 1, 4200],
    ["Tovar 6", "OOO Kosmos", 3800, 2, 7600],
    ["Tovar 7", "OOO Kosmos", 4100, 1, 4100],
    ["Tovar 8", "OOO Kosmos", 4335, 2, 8670],  # FIXED: 4335
    ["Tovar 9", "OOO Vremya", 6000, 1, 6000],
    ["Tovar 10", "OOO Radost", 4000, 2, 8000],
]

query = "kakaya srednyaya tsena tovarov u kazhdogo postavshchika"

print("="*80)
print("TEST: structured_data in HARDCODED response")
print("="*80)
print()

try:
    ai_service = get_ai_service()
    result = ai_service.process_formula_request(
        query=query,
        column_names=column_names,
        sheet_data=sheet_data,
        history=[]
    )

    print("RESULT KEYS:", list(result.keys()))
    print()

    # Check Kosmos calculation
    if "key_findings" in result:
        kosmos = [k for k in result["key_findings"] if "Kosmos" in k]
        if kosmos:
            print("KOSMOS RESULT:", kosmos[0])
            print("EXPECTED: OOO Kosmos: 4,322.50")
            print()

    # Check structured_data
    if "structured_data" in result:
        print("SUCCESS: structured_data FOUND!")
        print()
        sd = result["structured_data"]
        print("Headers:", sd.get("headers"))
        print("Rows count:", len(sd.get("rows", [])))
        print("Table title:", sd.get("table_title"))
        print("Chart type:", sd.get("chart_recommended"))
        print()
        print("First 3 rows:")
        for row in sd.get("rows", [])[:3]:
            print("  ", row)
    else:
        print("FAILED: structured_data NOT FOUND!")
        print("Available keys:", list(result.keys()))

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
