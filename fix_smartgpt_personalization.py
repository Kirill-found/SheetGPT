# Add custom_context support to SmartGPT
file_path = 'C:/Projects/SheetGPT/backend/app/services/simple_gpt_processor.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update function signature
old_sig = 'async def _gpt_smart_action(self, query: str, column_names: List[str], df: pd.DataFrame, history: List[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:'
new_sig = 'async def _gpt_smart_action(self, query: str, column_names: List[str], df: pd.DataFrame, history: List[Dict[str, Any]] = None, custom_context: Optional[str] = None) -> Optional[Dict[str, Any]]:'

if old_sig in content:
    content = content.replace(old_sig, new_sig)
    print('SUCCESS: Updated _gpt_smart_action signature')
else:
    print('ERROR: Signature not found')

# 2. Update call to _gpt_smart_action
old_call = 'smart_result = await self._gpt_smart_action(query, column_names, df, history=history)'
new_call = 'smart_result = await self._gpt_smart_action(query, column_names, df, history=history, custom_context=custom_context)'

if old_call in content:
    content = content.replace(old_call, new_call)
    print('SUCCESS: Updated _gpt_smart_action call')
else:
    print('ERROR: Call not found')

# 3. Add custom_context to SmartGPT prompt - find where the prompt is built
# Look for the history_text addition and add custom_context after it
old_prompt_section = '''        history_text = ""
        if history and len(history) > 0:
            history_text = "\\n=== ИСТОРИЯ ДИАЛОГА ===\\n"
            for i, item in enumerate(history[-5:], 1):
                q = item.get('query', '')
                r = item.get('response', item.get('summary', item.get('answer', '')))
                if isinstance(r, dict):
                    r = r.get('summary', r.get('explanation', str(r)[:1500]))
                # Longer limit for history to capture full analysis results (tables, lists)
                history_text += f"{i}. Вопрос: {q}\\n   Ответ: {str(r)[:1500]}\\n"
            history_text += "=== КОНЕЦ ИСТОРИИ ===\\n\\n"'''

new_prompt_section = '''        history_text = ""
        if history and len(history) > 0:
            history_text = "\\n=== ИСТОРИЯ ДИАЛОГА ===\\n"
            for i, item in enumerate(history[-5:], 1):
                q = item.get('query', '')
                r = item.get('response', item.get('summary', item.get('answer', '')))
                if isinstance(r, dict):
                    r = r.get('summary', r.get('explanation', str(r)[:1500]))
                # Longer limit for history to capture full analysis results (tables, lists)
                history_text += f"{i}. Вопрос: {q}\\n   Ответ: {str(r)[:1500]}\\n"
            history_text += "=== КОНЕЦ ИСТОРИИ ===\\n\\n"

        # Add personalization context
        context_text = ""
        if custom_context:
            context_text = f"""
=== РОЛЬ ПОЛЬЗОВАТЕЛЯ ===
{custom_context}
ВАЖНО: Учитывай роль пользователя при формулировании ответов и выборе действий!
=== КОНЕЦ РОЛИ ===

"'''

if old_prompt_section in content:
    content = content.replace(old_prompt_section, new_prompt_section)
    print('SUCCESS: Added custom_context to prompt building')
else:
    print('ERROR: Prompt section not found')

# 4. Include context_text in the actual prompt - find where prompt is assembled
# The prompt variable is built later, we need to add context_text there
# Search for where history_text is used in the prompt and add context_text
old_prompt_usage = 'ЗАПРОС: {query}\\n{history_text}'
new_prompt_usage = 'ЗАПРОС: {query}\\n{context_text}{history_text}'

if old_prompt_usage in content:
    content = content.replace(old_prompt_usage, new_prompt_usage)
    print('SUCCESS: Added context_text to prompt')
else:
    # Try alternative pattern
    old_alt = '{history_text}ЗАПРОС:'
    new_alt = '{context_text}{history_text}ЗАПРОС:'
    if old_alt in content:
        content = content.replace(old_alt, new_alt)
        print('SUCCESS: Added context_text to prompt (alt pattern)')
    else:
        print('WARNING: Could not find prompt usage pattern - may need manual fix')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
