"""
Улучшенная логика для определения строк выделения
"""

def generate_smart_highlighting(query, key_findings, df, result_dict):
    """
    Умная генерация данных для выделения строк
    Анализирует реальные данные вместо простой последовательности
    """
    import re

    highlight_keywords = ['выдели', 'подсвет', 'отметь', 'покаж', 'highlight', 'mark', 'топ', 'лучш', 'худш']
    query_lower = query.lower()

    if not any(kw in query_lower for kw in highlight_keywords):
        return None

    # Извлекаем число из запроса
    numbers = re.findall(r'\d+', query)
    count = 5  # По умолчанию 5
    if numbers:
        count = min(int(numbers[0]), 20)

    rows_to_highlight = []

    # УМНЫЙ АНАЛИЗ: Парсим key_findings и находим реальные позиции
    if key_findings and len(key_findings) > 0:
        product_positions = {}

        # Парсим key_findings чтобы понять какие товары выделять
        for finding in key_findings[:count]:
            if ':' in finding:
                product_name = finding.split(':')[0].strip()

                # Ищем позицию этого товара в DataFrame
                if df is not None:
                    # Поиск в DataFrame
                    for idx in range(len(df)):
                        row_name = str(df.iloc[idx, 0])  # Первая колонка - названия
                        if product_name in row_name or row_name in product_name:
                            # +2 потому что в Google Sheets строка 1 - заголовки
                            actual_row = idx + 2
                            if actual_row not in rows_to_highlight:
                                rows_to_highlight.append(actual_row)
                            break

        # Если DataFrame анализ не дал результатов, анализируем result_dict
        if not rows_to_highlight and result_dict:
            if isinstance(result_dict, dict):
                # Ищем в словаре результатов
                for finding in key_findings[:count]:
                    if ':' in finding:
                        product_name = finding.split(':')[0].strip()

                        # Проверяем разные форматы данных
                        if 'rows' in result_dict:
                            # Формат с rows
                            for idx, row in enumerate(result_dict['rows']):
                                if isinstance(row, list) and len(row) > 0:
                                    if product_name in str(row[0]) or str(row[0]) in product_name:
                                        rows_to_highlight.append(idx + 2)
                                        break
                        elif 'data' in result_dict:
                            # Формат с data
                            data = result_dict['data']
                            if isinstance(data, dict):
                                # Простой словарь товар: значение
                                items = list(data.keys())
                                for idx, item in enumerate(items):
                                    if product_name in item or item in product_name:
                                        rows_to_highlight.append(idx + 2)
                                        break

    # Если умный анализ не помог - используем простую последовательность
    # но ПРАВИЛЬНУЮ - основанную на сортировке данных
    if not rows_to_highlight:
        if df is not None and len(df) > 0:
            # Находим колонку с числами
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                # Сортируем по первой числовой колонке
                sorted_df = df.sort_values(by=numeric_cols[0], ascending=False)
                # Берем топ N строк
                for i in range(min(count, len(sorted_df))):
                    original_idx = sorted_df.index[i]
                    rows_to_highlight.append(original_idx + 2)
        else:
            # Крайний случай - простая последовательность
            rows_to_highlight = list(range(2, 2 + count))

    # Определяем цвет и сообщение
    if 'топ' in query_lower or 'лучш' in query_lower:
        highlight_color = '#90EE90'  # Зелёный
        highlight_message = f'Выделены топ {len(rows_to_highlight)} товаров'
    elif 'худш' in query_lower or 'минимальн' in query_lower:
        highlight_color = '#FFB6C1'  # Красный
        highlight_message = f'Выделены {len(rows_to_highlight)} минимальных значений'
    else:
        highlight_color = '#FFFF00'  # Жёлтый
        highlight_message = f'Выделены {len(rows_to_highlight)} строк'

    return {
        "action_type": "highlight_rows",
        "highlight_rows": sorted(rows_to_highlight),  # Сортируем для удобства
        "highlight_color": highlight_color,
        "highlight_message": highlight_message
    }

# Пример интеграции в основной код:
#
# В методе process_with_code после генерации key_findings:
#
# # Умная генерация выделения
# highlighting_data = generate_smart_highlighting(query, key_findings, df, result_dict)
# if highlighting_data:
#     print(f"✅ Smart highlighting generated: {highlighting_data}")
# else:
#     print(f"❌ No highlighting needed")