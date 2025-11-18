"""
Test comma separator fix
"""

import sys
sys.path.insert(0, '.')

import pandas as pd
from app.services.function_registry import FunctionRegistry

# Test data with comma decimals
data = {
    "Город": ["Москва", "Санкт-Петербург", "Новосибирск", "Екатеринбург"],
    "Население (млн)": ["12,6", "5,4", "1,6", "1,5"]
}

df = pd.DataFrame(data)

print(f"\n{'='*80}")
print(f"TEST: Comma decimal separator fix")
print(f"{'='*80}\n")

print(f"Original data:")
print(df)
print()

# Create function registry
registry = FunctionRegistry()

# Test highlight_rows with comma decimals
print(f"Testing: highlight_rows with value > 1.7")
result = registry.highlight_rows(df, "Население", ">", 1.7, "yellow")

print(f"\nResult:")
print(f"  Highlight rows: {result['highlight_rows']}")
print(f"  Expected: [2, 3] (Москва:12,6 и СПб:5,4)")
print()

if result['highlight_rows'] == [2, 3]:
    print(f"✅ SUCCESS - Correct rows highlighted!")
else:
    print(f"❌ FAILED - Wrong rows: {result['highlight_rows']}")
