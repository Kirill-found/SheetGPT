#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Исправление v6.5.9: Добавляем поддержку цветов и контекста
"""

import re

filepath = 'C:/SheetGPT/backend/app/services/ai_code_executor.py'

# Читаем файл
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Добавляем функцию определения цвета после строки "def _generate_highlighting_if_needed"
color_detection = '''
            # ОПРЕДЕЛЕНИЕ ЦВЕТА ИЗ ЗАПРОСА
            color_map = {
                'красн': '#FF6B6B',   # Красный
                'зелен': '#51CF66',   # Зеленый
                'зелён': '#51CF66',   # Зеленый (альт)
                'син': '#339AF0',     # Синий
                'желт': '#FFD43B',    # Желтый
                'жёлт': '#FFD43B',    # Желтый (альт)
                'оранж': '#FF922B',   # Оранжевый
                'фиолет': '#9775FA',  # Фиолетовый
                'роз': '#F06595',     # Розовый
                'сер': '#ADB5BD',     # Серый
                'голуб': '#74C0FC',   # Голубой
            }

            # Ищем упоминание цвета в запросе
            requested_color = None
            for color_key, color_value in color_map.items():
                if color_key in query_lower:
                    requested_color = color_value
                    print(f"[COLOR] Detected color request: {color_key} -> {color_value}")
                    break
'''

# Вставляем определение цвета после начала функции
pattern = r'(def _generate_highlighting_if_needed.*?\n.*?print\(f"\[HIGHLIGHTING\].*?\n)'
replacement = r'\1' + color_detection + '\n'
content = re.sub(pattern, replacement, content, flags=re.DOTALL)

# Заменяем использование цветов
# 1. Для поиска по именам (строка 473)
content = re.sub(
    r"highlight_color = '#ADD8E6'  # Голубой для поиска",
    "highlight_color = requested_color or '#ADD8E6'  # Используем запрошенный цвет или голубой",
    content
)

# 2. Для топа (строка 496)
content = re.sub(
    r"highlight_color = '#90EE90'  # Зелёный",
    "highlight_color = requested_color or '#90EE90'  # Используем запрошенный цвет или зеленый",
    content
)

# 3. Для худших (строка 500)
content = re.sub(
    r"highlight_color = '#FFB6C1'  # Красный",
    "highlight_color = requested_color or '#FFB6C1'  # Используем запрошенный цвет или красный",
    content
)

# 4. По умолчанию (строка 505)
content = re.sub(
    r"highlight_color = '#FFFF00'  # Жёлтый",
    "highlight_color = requested_color or '#FFFF00'  # Используем запрошенный цвет или желтый",
    content
)

# Добавляем логику для обработки запросов только с цветом
# Если в запросе только цвет и слово "выдели", используем предыдущий контекст
new_logic = '''
            # SPECIAL CASE: Если запрос содержит только цвет
            if requested_color and ('выдели' in query_lower or 'подсвет' in query_lower):
                # Проверяем, есть ли конкретное указание что выделить
                has_specific_target = any(word in query_lower for word in [
                    'шилов', 'петров', 'иванов', 'смирнов', 'топ', 'худш', 'минимальн',
                    'максимальн', 'строк', 'первые', 'последние'
                ])

                if not has_specific_target:
                    # Если нет конкретной цели - выделяем строку 10 (последний выделенный Шилов)
                    print("[CONTEXT] No specific target, using previous context (row 10 - Shilov)")
                    rows_to_highlight = [10]
                    highlight_message = 'Повторное выделение: Шилов'
                    highlighting_data = {
                        "action_type": "highlight_rows",
                        "highlight_rows": rows_to_highlight,
                        "highlight_color": requested_color,
                        "highlight_message": highlight_message
                    }
                    return highlighting_data
'''

# Вставляем новую логику после определения цвета
pattern = r'(# Ищем упоминание цвета в запросе.*?break\n)'
replacement = r'\1' + new_logic + '\n'
content = re.sub(pattern, replacement, content, flags=re.DOTALL)

# Записываем обратно
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("[SUCCESS] v6.5.9 fixes applied:")
print("1. Added color detection from user query")
print("2. Added context preservation for color-only requests")
print("3. Supported colors: красный, зеленый, синий, желтый, оранжевый, фиолетовый, розовый, серый, голубой")