"""
Debug encoding error
"""

import sys
import os

# Set console encoding to UTF-8
if sys.platform == 'win32':
    os.system('chcp 65001 >nul')
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, '.')

from app.services.ai_code_executor import get_ai_executor

# Test data
test_data = [
    ["Moscow", "1500"],
    ["Saint Petersburg", "540"],
    ["Novosibirsk", "158"]
]

column_names = ["City", "Population (thousands)"]

# Query in English to avoid console encoding issues
query = "highlight cities with population more than 1.7 million"

print(f"\n{'='*80}")
print(f"TEST: {query}")
print(f"{'='*80}\n")

try:
    executor = get_ai_executor()
    result = executor.process_with_code(
        query=query,
        column_names=column_names,
        sheet_data=test_data,
        history=[]
    )

    print(f"\n{'='*80}")
    print(f"[RESULT]:")
    print(f"{'='*80}\n")

    print(f"Response Type: {result.get('response_type')}")
    print(f"Confidence: {result.get('confidence')}")

    if 'error' in result:
        print(f"\n[ERROR IN RESULT]: {result['error']}")

    if 'answer' in result:
        print(f"\nAnswer: {result['answer']}")

    print(f"\n[SUCCESS]")

except Exception as e:
    print(f"\n[EXCEPTION]: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
