# -*- coding: utf-8 -*-
"""Add debug logging for aggregation detection"""

file_path = "app/services/clean_analyst.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Check if already has logging
if "Checking aggregation patterns" in content:
    print("Logging already added!")
    exit(0)

# Add logging before pattern check
old_code = '''        aggregation_type = self._detect_aggregation_query(query)
        if aggregation_type:'''

new_code = '''        logger.info(f"[CleanAnalyst] Checking aggregation patterns for: {query}")
        aggregation_type = self._detect_aggregation_query(query)
        logger.info(f"[CleanAnalyst] Aggregation detected: {aggregation_type}")
        if aggregation_type:'''

if old_code in content:
    content = content.replace(old_code, new_code)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS: Added debug logging")
else:
    print("ERROR: Pattern not found")
