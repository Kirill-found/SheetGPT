# Add _rewrite_followup_query method
file_path = 'C:/Projects/SheetGPT/backend/app/services/simple_gpt_processor.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

old = '''        return False

    def _is_conversational_query(self, query: str, history: List[Dict[str, Any]] = None) -> bool:
        """Detect if query is conversational (follow-up, why, explain)."""
        query_lower = query.lower().strip()

        # Very short queries with history are likely follow-ups
        if history and len(history) > 0 and len(query_lower.split()) <= 3:'''

new = '''        return False

    def _rewrite_followup_query(self, query: str, history: List[Dict[str, Any]] = None) -> str:
        """
        v11.1.3: Rewrite short follow-up queries to be explicit.

        Example:
        - History: "Сколько товаров на WB?" → "31912 шт"
        - Query: "а на Ozon?"
        - Rewritten: "Сколько товаров на Ozon?"
        """
        if not history or len(history) == 0:
            return query

        query_lower = query.lower().strip()
        words = query_lower.split()

        # Only rewrite short queries (1-4 words) starting with "а" or "и"
        if len(words) > 4:
            return query

        if not (query_lower.startswith('а ') or query_lower.startswith('и ') or
                query_lower.startswith('а?') or query_lower.startswith('и?')):
            return query

        # Get the most recent query from history
        prev_query = history[-1].get('query', '')
        if not prev_query:
            return query

        # Extract the new subject from current query
        # "а на Ozon?" → "Ozon", "а Петров?" → "Петров", "а за июль?" → "июль"
        import re

        # Remove leading "а " or "и " and trailing "?"
        subject_part = re.sub(r'^[аи]\\s*', '', query, flags=re.IGNORECASE)
        subject_part = subject_part.rstrip('?').strip()

        # Extract preposition and subject: "на Ozon" → ("на", "Ozon"), "Петров" → ("", "Петров")
        prep_match = re.match(r'^(на|по|за|в|от|до|с|у|к|из)?\\s*(.+)$', subject_part, re.IGNORECASE)
        if prep_match:
            prep = prep_match.group(1) or ''
            new_subject = prep_match.group(2).strip()
        else:
            prep = ''
            new_subject = subject_part

        # Find what to replace in previous query
        # Look for patterns like "на WB", "по Москве", "за январь", or standalone subjects
        prev_lower = prev_query.lower()

        # Try to find preposition + subject pattern in previous query
        replacements = [
            (r'на\\s+\\w+', f'на {new_subject}'),
            (r'по\\s+\\w+', f'по {new_subject}'),
            (r'за\\s+\\w+', f'за {new_subject}'),
            (r'в\\s+\\w+', f'в {new_subject}'),
            (r'от\\s+\\w+', f'от {new_subject}'),
            (r'у\\s+\\w+', f'у {new_subject}'),
        ]

        rewritten = prev_query
        replaced = False

        for pattern, replacement in replacements:
            if re.search(pattern, prev_lower, re.IGNORECASE):
                rewritten = re.sub(pattern, replacement, prev_query, count=1, flags=re.IGNORECASE)
                replaced = True
                break

        if replaced and rewritten != prev_query:
            logger.info(f"[SmartGPT] 🔄 Query rewritten: '{query}' → '{rewritten}'")
            return rewritten

        return query

    def _is_conversational_query(self, query: str, history: List[Dict[str, Any]] = None) -> bool:
        """Detect if query is conversational (follow-up, why, explain)."""
        query_lower = query.lower().strip()

        # Very short queries with history are likely follow-ups
        if history and len(history) > 0 and len(query_lower.split()) <= 3:'''

if old in content:
    content = content.replace(old, new)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS: Added _rewrite_followup_query method')
else:
    print('ERROR: Pattern not found')
    # Debug
    if 'def _is_conversational_query' in content:
        print('Found _is_conversational_query')
    if 'return False' in content:
        print('Found return False')
