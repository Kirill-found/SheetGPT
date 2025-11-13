"""
Тест sanitization для строки из production теста
"""
import re

def _sanitize_custom_context(custom_context: str):
    """Копия функции из ai_code_executor.py"""
    if not custom_context or not custom_context.strip():
        return None

    sanitized = custom_context.strip()

    if len(sanitized) > 2000:
        sanitized = sanitized[:2000] + "..."

    dangerous_patterns = [
        r"ignore\s+(previous|above|all)\s+instructions",
        r"forget\s+(everything|all|previous)",
        r"disregard\s+(previous|above)",
        r"new\s+instructions:",
        r"system\s*:\s*",
        r"assistant\s*:\s*",
        r"<\|im_start\|>",
        r"<\|im_end\|>",
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, sanitized, re.IGNORECASE):
            print(f"REJECTED by pattern: {pattern}")
            return None

    print(f"PASSED sanitization")
    return sanitized

# Тест
test_strings = [
    "You are a financial analyst. Provide brief recommendations.",
    "Ты финансовый директор. Давай краткие рекомендации.",
    "You are a CFO with 10 years of experience. Analyze data from profitability perspective."
]

for s in test_strings:
    print(f"\n--- Testing: '{s[:50]}...'")
    result = _sanitize_custom_context(s)
    print(f"Result: {result}")
