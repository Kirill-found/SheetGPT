"""
Test Russian query with encoding fix
"""

import sys
import os

# Set console encoding to UTF-8
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, errors='replace')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, errors='replace')

sys.path.insert(0, '.')

from app.services.ai_code_executor import get_ai_executor

# Test data - in English to avoid input encoding issues
test_data = [
    ["Moscow", "1500"],
    ["Saint Petersburg", "540"],
    ["Novosibirsk", "158"],
    ["Yekaterinburg", "147"]
]

column_names = ["City", "Population (thousands)"]

# Russian query
query = "выдели города с населением больше 1,7 млн"

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
