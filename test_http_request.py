"""Test HTTP request with custom_context"""
import requests
import json

# Load test data
with open('C:/SheetGPT/test_english_context.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print("Sending request with custom_context:")
print(f"  custom_context: {data.get('custom_context')}")
print()

# Send request
response = requests.post(
    'https://sheetgpt-production.up.railway.app/api/v1/formula',
    json=data,
    headers={'Content-Type': 'application/json'}
)

print(f"Status: {response.status_code}")
result = response.json()

print(f"\nProfessional insights: {result.get('professional_insights')}")
print(f"Recommendations: {result.get('recommendations')}")
print(f"Warnings: {result.get('warnings')}")
print(f"\nSummary: {result.get('summary')}")
