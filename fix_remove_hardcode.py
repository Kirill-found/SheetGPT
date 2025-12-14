# -*- coding: utf-8 -*-
# Remove the hardcoded profitability check and improve prompt instead

with open('C:/Projects/SheetGPT/backend/app/services/simple_gpt_processor.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove the hardcoded check
old_hardcode = """        # v11.5: ANTI-HALLUCINATION - check for profitability queries WITHOUT cost data
        query_lower = query.lower()
        profitability_keywords = ['прибыл', 'прибыльн', 'выгодн', 'маржа', 'марж', 'рентабельн', 'наценк', 'себестоим']
        is_profitability_query = any(kw in query_lower for kw in profitability_keywords)

        if is_profitability_query:
            # Check if there's a cost/purchase price column
            cost_keywords = ['себестоим', 'закуп', 'cost', 'purchase', 'входн', 'оптов']
            has_cost_column = any(
                any(kw in col.lower() for kw in cost_keywords)
                for col in column_names
            )

            if not has_cost_column:
                logger.warning(f"[SmartGPT] Profitability query detected but NO COST COLUMN found!")
                return {
                    'action_type': 'chat',
                    'message': 'Для расчёта прибыльности/маржи нужны данные о себестоимости (закупочной цене). В таблице такой колонки нет. Могу показать товар с максимальной выручкой или средним чеком - это вам подойдёт?',
                    'success': True,
                    'result_type': 'chat'
                }
            else:
                logger.info(f"[SmartGPT] Profitability query - cost column found: {[c for c in column_names if any(kw in c.lower() for kw in cost_keywords)]}")

        # v11.1.3: Rewrite short follow-up queries to be explicit"""

new_hardcode = """        # v11.1.3: Rewrite short follow-up queries to be explicit"""

if old_hardcode in content:
    content = content.replace(old_hardcode, new_hardcode)
    print('OK: Removed hardcoded profitability check')
else:
    print('Hardcode not found, maybe already removed')

# Now improve the prompt - add smart data interpretation rules
old_prompt_section = """[!!!] ЗАПРЕТ НА ВЫДУМЫВАНИЕ ДАННЫХ [!!!]
==============================================================

КРИТИЧНО: НЕ ВЫДУМЫВАЙ данные, которых НЕТ в таблице!

Если пользователь просит "прибыльность", "маржу", "рентабельность":
1. ПРОВЕРЬ: есть ли колонка с себестоимостью/закупочной ценой?
2. Если НЕТ -> СРАЗУ СКАЖИ: "Для расчёта прибыльности нужна себестоимость. В таблице её нет. Добавьте колонку с себестоимостью."
3. НЕ ВЫДУМЫВАЙ цифры типа "прибыльность 60,000 руб."!

Плохо: "Самый выгодный товар: Ноутбук, прибыльность 60,171 руб."
(если нет данных о себестоимости - это ЛОЖЬ!)

Хорошо: "Для расчёта прибыльности нужны данные о себестоимости.
В таблице есть только цена продажи. Могу показать товар с максимальной
выручкой или средним чеком - это вам подойдёт?"

ПРАВИЛО: Лучше честно сказать "не могу" чем выдумать ответ!"""

new_prompt_section = """[!!!] ИНТЕРПРЕТАЦИЯ ЗАПРОСОВ ПО ИМЕЮЩИМСЯ ДАННЫМ [!!!]
==============================================================

КРИТИЧНО: Отвечай ТОЛЬКО на основе данных, которые ЕСТЬ в таблице!

АЛГОРИТМ ДЛЯ ЛЮБОГО ЗАПРОСА:
1. Посмотри какие КОЛОНКИ есть в таблице
2. Определи что можно посчитать с этими данными
3. Интерпретируй запрос через ДОСТУПНЫЕ метрики
4. Дай ответ на основе РЕАЛЬНЫХ данных

ПРИМЕР - "какой товар самый выгодный":
1. Смотрю колонки: Товар, Цена, Количество, Сумма, Город, Дата
2. Нет колонки "Себестоимость" → прибыльность посчитать НЕВОЗМОЖНО
3. Есть "Сумма" → могу определить выгодность по ВЫРУЧКЕ
4. Ответ: "По выручке лидирует Ноутбук: 1,835,901 руб."

НЕ ДЕЛАЙ ТАК:
❌ "Прибыльность: 60,171 руб." (откуда цифра если нет себестоимости?!)
❌ Выдумывать данные которых нет в таблице
❌ Использовать термин "прибыльность" без колонки себестоимости

ДЕЛАЙ ТАК:
✅ Интерпретируй "выгодный" как "с наибольшей выручкой" если нет себестоимости
✅ Чётко указывай по какой метрике даёшь ответ: "По выручке...", "По количеству продаж..."
✅ Если запрос невозможен с имеющимися данными - скажи какие данные нужны

ПРАВИЛО: Работай с тем что ЕСТЬ, не выдумывай то чего НЕТ!"""

if old_prompt_section in content:
    content = content.replace(old_prompt_section, new_prompt_section)
    print('OK: Updated prompt with smart data interpretation')
else:
    print('Old prompt section not found')

with open('C:/Projects/SheetGPT/backend/app/services/simple_gpt_processor.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done!')
