# Add query rewriting for short follow-up questions
file_path = 'C:/Projects/SheetGPT/backend/app/services/simple_gpt_processor.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

old = '''        # Prepare history context
        history_text = ""
        if history and len(history) > 0:
            history_text = "\\n=== ИСТОРИЯ ДИАЛОГА ===\\n"'''

new = '''        # v11.1.3: Rewrite short follow-up queries to be explicit
        # "а на Ozon?" with history "Сколько товаров на WB?" → "Сколько товаров на Ozon?"
        query = self._rewrite_followup_query(query, history)

        # Prepare history context
        history_text = ""
        if history and len(history) > 0:
            history_text = "\\n=== ИСТОРИЯ ДИАЛОГА ===\\n"'''

if old in content:
    content = content.replace(old, new)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS: Added query rewrite call')
else:
    print('ERROR: Pattern not found')
