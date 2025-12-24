# -*- coding: utf-8 -*-
"""Add pandas aggregation methods to CleanAnalyst"""

file_path = "app/services/clean_analyst.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Check if already exists
if "_detect_aggregation_query" in content:
    print("Methods already exist!")
    exit(0)

# The code to insert after __init__
new_methods = r'''
    def _detect_aggregation_query(self, query: str) -> Optional[Dict]:
        """
        Определяет запросы на агрегацию и извлекает параметры.
        GPT плохо считает - лучше считать в pandas!
        """
        query_lower = query.lower()

        # Паттерны запросов на сумму по группам
        sum_patterns = [
            r'(?:сумм[ау]|итог[и]?)\s+(?:по|для)\s+',
            r'сколько\s+(?:продал[иа]?|заработал[иа]?|сделал[иа]?)',
            r'(?:продажи|выручка|сумма)\s+(?:по|для|каждого)',
            r'(?:сводк[ау]|итоги?|агрегац)',
            r'на\s+какую\s+сумму',
        ]

        for pattern in sum_patterns:
            if re.search(pattern, query_lower):
                return {"type": "aggregation", "operation": "sum"}

        return None

    def _calculate_aggregation(
        self,
        df: pd.DataFrame,
        column_names: List[str],
        query: str
    ) -> Optional[Dict]:
        """
        Выполняет агрегацию в pandas - точные расчёты!
        Возвращает результаты для GPT чтобы он их отформатировал.
        """
        query_lower = query.lower()

        # Определяем колонку для группировки
        group_col = None
        group_keywords = {
            'менеджер': ['менеджер', 'продавец', 'сотрудник', 'manager'],
            'город': ['город', 'регион', 'филиал', 'city'],
            'статус': ['статус', 'состояние', 'status'],
            'категория': ['категория', 'тип', 'группа', 'category'],
            'клиент': ['клиент', 'покупатель', 'заказчик', 'customer'],
        }

        # Сначала ищем по ключевым словам в запросе
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
            return None

        # Определяем колонку для суммирования (числовая)
        sum_col = None
        sum_keywords = ['сумма', 'выручка', 'продажи', 'итого', 'стоимость', 'цена', 'amount', 'total', 'price', 'sum']

        for col in column_names:
            col_lower = col.lower()
            if any(s in col_lower for s in sum_keywords):
                if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
                    sum_col = col
                    break

        # Если не нашли по названию, берём первую числовую с большими значениями
        if not sum_col:
            for col in column_names:
                if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
                    # Пропускаем ID-шные колонки (обычно маленькие целые числа подряд)
                    if df[col].max() > 100:  # Сумма обычно > 100
                        sum_col = col
                        break

        if not sum_col:
            logger.info("[CleanAnalyst] No numeric column found for aggregation")
            return None

        logger.info(f"[CleanAnalyst] Aggregation: group by '{group_col}', sum '{sum_col}'")

        # Проверяем фильтр по статусу
        status_filter = None
        if 'оплачен' in query_lower or 'paid' in query_lower:
            status_col = None
            for col in column_names:
                if 'статус' in col.lower() or 'status' in col.lower():
                    status_col = col
                    break
            if status_col and status_col in df.columns:
                # Ищем значения со словом "оплачен"
                unique_statuses = df[status_col].dropna().unique()
                for status in unique_statuses:
                    if 'оплачен' in str(status).lower():
                        status_filter = (status_col, status)
                        break

        # Фильтруем если нужно
        work_df = df.copy()
        filter_desc = ""
        if status_filter:
            col, val = status_filter
            work_df = work_df[work_df[col] == val]
            filter_desc = f" (filter: {col} = '{val}')"
            logger.info(f"[CleanAnalyst] Applied filter: {col} = '{val}', rows: {len(work_df)}")

        # Выполняем агрегацию
        try:
            result = work_df.groupby(group_col)[sum_col].sum().sort_values(ascending=False)

            # Форматируем результат
            aggregation_result = {
                "group_column": group_col,
                "sum_column": sum_col,
                "filter": filter_desc,
                "total_rows": len(work_df),
                "groups": []
            }

            for group_name, value in result.items():
                aggregation_result["groups"].append({
                    "name": str(group_name),
                    "value": float(value),
                    "formatted": f"{value:,.0f}".replace(",", " ")
                })

            aggregation_result["grand_total"] = float(result.sum())
            aggregation_result["grand_total_formatted"] = f"{result.sum():,.0f}".replace(",", " ")

            logger.info(f"[CleanAnalyst] Aggregation complete: {len(result)} groups, total: {result.sum()}")
            return aggregation_result

        except Exception as e:
            logger.error(f"[CleanAnalyst] Aggregation error: {e}")
            return None

'''

# Find the insertion point - after __init__ method
old_text = "    def __init__(self, api_key: str):\n        self.client = AsyncOpenAI(api_key=api_key)\n\n    def format_data_as_table"
new_text = "    def __init__(self, api_key: str):\n        self.client = AsyncOpenAI(api_key=api_key)\n" + new_methods + "\n    def format_data_as_table"

if old_text in content:
    content = content.replace(old_text, new_text)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS: Added aggregation methods")
else:
    print("ERROR: Pattern not found")
    # Debug
    if "def __init__(self, api_key: str):" in content:
        print("Found __init__")
    if "def format_data_as_table" in content:
        print("Found format_data_as_table")
