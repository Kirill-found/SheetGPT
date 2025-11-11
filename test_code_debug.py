"""
Test to see GENERATED PYTHON CODE from AI Code Executor
"""

import requests
import json

column_names = ["Kolonna A", "Kolonna B", "Kolonna C", "Kolonna D", "Kolonna E"]

# Test data: 6 products for OOO Kosmos
sheet_data = [
    ["Tovar 1", "OOO Vremya", 5000, 2, 10000],
    ["Tovar 2", "OOO Radost", 3500, 3, 10500],
    ["Tovar 3", "OOO Kosmos", 4500, 1, 4500],  # Price 4500
    ["Tovar 4", "OOO Kosmos", 5000, 2, 10000],  # Price 5000
    ["Tovar 5", "OOO Kosmos", 4200, 1, 4200],   # Price 4200
    ["Tovar 6", "OOO Kosmos", 3800, 2, 7600],   # Price 3800
    ["Tovar 7", "OOO Kosmos", 4100, 1, 4100],   # Price 4100
    ["Tovar 8", "OOO Kosmos", 4335, 2, 8670],   # Price 4335 (FIXED: was 3335)
    # Kosmos total: 6 items, sum prices = 25935, average = 4322.50
    ["Tovar 9", "OOO Vremya", 6000, 1, 6000],
    ["Tovar 10", "OOO Radost", 4000, 2, 8000],
]

payload = {
    "query": "kakaya srednyaya tsena tovarov u kazhdogo postavshchika",
    "column_names": column_names,
    "sheet_data": sheet_data,
    "history": []
}

print("=" * 80)
print("TEST: Average price per supplier")
print("=" * 80)
print(f"\nExpected for OOO Kosmos: 4322.50 (25935 / 6)")
print("Sending request to API...\n")

try:
    response = requests.post(
        "https://sheetgpt-production.up.railway.app/api/v1/formula",
        json=payload,
        timeout=30
    )

    result = response.json()

    # Check if code_generated is in response
    if "code_generated" in result:
        print("=" * 80)
        print("GENERATED PYTHON CODE:")
        print("=" * 80)
        print(result["code_generated"])
        print("\n")
    else:
        print("WARNING: No 'code_generated' field in response!")
        print("Response keys:", list(result.keys()))

    # Show summary
    if "summary" in result:
        print("=" * 80)
        print("RESULT (summary):")
        print("=" * 80)
        print(result["summary"])
        print("\n")

    # Show methodology
    if "methodology" in result:
        print("=" * 80)
        print("METHODOLOGY:")
        print("=" * 80)
        print(result["methodology"])
        print("\n")

    # Full response
    print("=" * 80)
    print("FULL API RESPONSE:")
    print("=" * 80)
    print(json.dumps(result, indent=2, ensure_ascii=False))

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
