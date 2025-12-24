# -*- coding: utf-8 -*-
"""Fix aggregation detection patterns"""

file_path = "app/services/clean_analyst.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Old patterns (too restrictive)
old_patterns = r'''        # Паттерны запросов на сумму по группам
        sum_patterns = [
            r'(?:сумм[ау]|итог[и]?)\s+(?:по|для)\s+',
            r'сколько\s+(?:продал[иа]?|заработал[иа]?|сделал[иа]?)',
            r'(?:продажи|выручка|сумма)\s+(?:по|для|каждого)',
            r'(?:сводк[ау]|итоги?|агрегац)',
            r'на\s+какую\s+сумму',
        ]'''

# New patterns (more comprehensive)
new_patterns = r'''        # Паттерны запросов на сумму по группам
        sum_patterns = [
            r'(?:сумм[ау]|итог[и]?)\s+(?:по|для)\s+',
            r'сколько\s+(?:продал[иа]?|заработал[иа]?|сделал[иа]?)',
            r'(?:продажи|выручка|сумма)\s+(?:по|для|каждого)',
            r'(?:сводк[ау]|итоги?|агрегац)',
            r'на\s+какую\s+сумму',
            r'посчитай',  # "посчитай все заказы", "посчитай оплаченные"
            r'подсчитай',
            r'рассчитай',
            r'(?:все|только)\s+заказ',  # "все заказы", "только оплаченные заказы"
            r'по\s+(?:город|менеджер|статус|категори)',  # "по городам", "по менеджерам"
        ]'''

if old_patterns in content:
    content = content.replace(old_patterns, new_patterns)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS: Fixed aggregation patterns")
else:
    print("ERROR: Pattern not found")
    # Debug
    if "sum_patterns = [" in content:
        print("Found sum_patterns")
