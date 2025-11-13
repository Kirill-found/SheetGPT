"""
Local test for custom_context feature
Bypasses Railway deployment issues
"""
import sys
sys.path.insert(0, 'C:/SheetGPT/backend')

import json
from app.services.ai_code_executor import get_ai_executor

# Load test data
with open('C:/SheetGPT/test_custom_context.json', 'r', encoding='utf-8') as f:
    test_data = json.load(f)

print("=== LOCAL CUSTOM_CONTEXT TEST ===\n")
print(f"Query: {test_data['query']}")
print(f"Custom context: {test_data['custom_context'][:100]}...\n")

# Call executor directly
executor = get_ai_executor()
result = executor.process_with_code(
    query=test_data['query'],
    column_names=test_data['column_names'],
    sheet_data=test_data['sheet_data'],
    history=[],
    custom_context=test_data['custom_context']
)

print("\n=== RESULT ===")
print(f"Summary: {result.get('summary')}")
print(f"\nProfessional insights: {result.get('professional_insights')}")
print(f"Recommendations: {result.get('recommendations')}")
print(f"Warnings: {result.get('warnings')}")
print(f"\nMethodology: {result.get('methodology')}")
print(f"Confidence: {result.get('confidence')}")
