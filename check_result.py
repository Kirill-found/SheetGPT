import json

with open('C:/SheetGPT/railway_final_test.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print("="*80)
print("ФИНАЛЬНЫЙ РЕЗУЛЬТАТ RAILWAY")
print("="*80)
print()

# Check structured_data
has_sd = 'structured_data' in data
print(f"Has structured_data: {has_sd}")
print()

# Check calculation
kosmos_finding = [k for k in data.get('key_findings', []) if 'Kosmos' in k]
if kosmos_finding:
    print(f"OOO Kosmos result: {kosmos_finding[0]}")
    print("Expected: OOO Kosmos: 4,322.50")
    is_correct = '4,322.50' in kosmos_finding[0] or '4322.5' in kosmos_finding[0]
    print(f"Calculation correct: {is_correct}")
print()

# Check methodology
methodology = data.get('methodology', '')
print(f"Methodology type: {'FAILSAFE' if 'FAILSAFE' in methodology else 'HARDCODED' if 'HARDCODED' in methodology else 'OTHER'}")
print(f"Methodology preview: {methodology[:100]}...")
print()

# Show structured_data if exists
if has_sd:
    sd = data['structured_data']
    print("SUCCESS! structured_data found:")
    print(f"  Headers: {sd.get('headers')}")
    print(f"  Rows count: {len(sd.get('rows', []))}")
    print(f"  Chart type: {sd.get('chart_recommended')}")
    print(f"  Table title: {sd.get('table_title')}")
    print(f"  First 2 rows: {sd.get('rows', [])[:2]}")
else:
    print("FAIL: structured_data NOT FOUND")
    print(f"Available keys: {list(data.keys())}")
