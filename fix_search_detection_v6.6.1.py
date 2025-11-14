#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v6.6.1: Исправление определения поискового запроса
1. Убрать дубликат else
2. Улучшить is_search_query: если есть "выдели" + слово начинающееся с заглавной (имя), то это поиск
3. Добавить в промпт AI инструкцию про частичный поиск и морфологию
"""

import re

filepath = 'C:/SheetGPT/backend/app/services/ai_code_executor.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Исправляем дубликат else (строки 511-512)
content = re.sub(
    r'(\s+else:\s*\n\s+else:\s*\n)',
    '\n            else:\n',
    content
)

# 2. Заменяем is_search_query логику на более умную
old_search_logic = r'''is_search_query = any\(word in query_lower for word in \['фамили', 'имен', 'строк', 'найди', 'где'\]\)'''

new_search_logic = '''# УЛУЧШЕННАЯ ЛОГИКА: поиск = ключевое слово + имя/фамилия
            is_search_query = False
            search_keywords = ['фамили', 'имен', 'строк', 'найди', 'где']

            # Случай 1: явные поисковые ключевые слова
            if any(word in query_lower for word in search_keywords):
                is_search_query = True

            # Случай 2: "выдели" + слово с заглавной буквы (вероятно имя/фамилия)
            elif 'выдели' in query_lower:
                # Ищем слова с заглавной буквы (кроме первого слова в запросе)
                words = query.split()
                for word in words[1:]:  # Пропускаем первое слово
                    # Если слово начинается с заглавной и не является служебным
                    if word[0].isupper() and word.lower() not in ['оранжевым', 'красным', 'зелёным', 'синим', 'жёлтым', 'цветом', 'строк']:
                        is_search_query = True
                        print(f"[SEARCH_DETECT] Found name/surname: {word}")
                        break'''

content = re.sub(old_search_logic, new_search_logic, content, flags=re.MULTILINE)

# 3. Улучшаем промпт AI для поиска с морфологией
# Находим секцию с промптом
prompt_section = r'''(QUESTION: \{query\}

AVAILABLE DATA:
DataFrame 'df' with \{len\(df\)\} rows and columns:
\{data_info\}

SAMPLE DATA \(first 5 rows\):
\{df\.head\(\)\.to_string\(\)\}

RULES FOR CODE GENERATION:)'''

improved_prompt = r'''\1
10. For Russian names/surnames: use partial matching with .str.contains() to handle different word forms
11. Example: "Капустина" should match "Капустин", "Шилова" matches "Шилов"

'''

content = re.sub(prompt_section, improved_prompt, content)

# Записываем обратно
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("[OK] v6.6.1 фикс применён!")
print("Изменения:")
print("1. ✓ Исправлен дубликат else")
print("2. ✓ Улучшена логика is_search_query")
print("3. ✓ Добавлена инструкция AI про частичный поиск имён")
