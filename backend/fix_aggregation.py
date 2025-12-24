# -*- coding: utf-8 -*-
"""Fix aggregation to work without explicit group column in query"""

file_path = "app/services/clean_analyst.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# The problem: we only find group_col if the query mentions it
# But "посчитай все заказы" doesn't mention "город"

# Find and replace the group column detection logic
old_code = '''        # Сначала ищем по ключевым словам в запросе
        for key, synonyms in group_keywords.items():
            if any(s in query_lower for s in synonyms):
                # Нашли ключевое слово в запросе - ищем соответствующую колонку
                for col in column_names:
                    col_lower = col.lower()
                    if any(s in col_lower for s in synonyms):
                        if col in df.columns:
                            group_col = col
                            break
            if group_col:
                break

        if not group_col:
            logger.info("[CleanAnalyst] No group column found for aggregation")
            return None'''

new_code = '''        # Сначала ищем по ключевым словам в запросе
        for key, synonyms in group_keywords.items():
            if any(s in query_lower for s in synonyms):
                # Нашли ключевое слово в запросе - ищем соответствующую колонку
                for col in column_names:
                    col_lower = col.lower()
                    if any(s in col_lower for s in synonyms):
                        if col in df.columns:
                            group_col = col
                            break
            if group_col:
                break

        # v12.1: Если не нашли по запросу - ищем подходящую колонку в данных
        if not group_col:
            logger.info("[CleanAnalyst] No group column in query, searching in columns...")
            for col in column_names:
                col_lower = col.lower()
                # Ищем типичные колонки для группировки
                for key, synonyms in group_keywords.items():
                    if any(s in col_lower for s in synonyms):
                        if col in df.columns:
                            group_col = col
                            logger.info(f"[CleanAnalyst] Auto-detected group column: {col}")
                            break
                if group_col:
                    break

        if not group_col:
            logger.info("[CleanAnalyst] No group column found for aggregation")
            return None'''

if old_code in content:
    content = content.replace(old_code, new_code)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS: Fixed group column detection")
else:
    print("ERROR: Pattern not found")
