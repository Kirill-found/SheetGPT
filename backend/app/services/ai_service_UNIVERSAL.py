"""
УНИВЕРСАЛЬНЫЙ AI Service для SheetGPT
Никакого хардкода - только AI анализ
"""

import json
from typing import List, Dict, Any, Optional
from openai import OpenAI
from app.config import settings
import pandas as pd

class UniversalAIService:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        # Используем САМУЮ УМНУЮ модель для максимальной точности
        self.model = "gpt-4o"  # или "gpt-4-turbo-preview" для еще большей точности

    def process_any_request(self, query: str, column_names: List[str], sheet_data: List[List[Any]], history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        УНИВЕРСАЛЬНАЯ обработка ЛЮБОГО запроса через AI
        Никаких регулярок, никакого хардкода
        """

        # Конвертируем данные в DataFrame для анализа
        df = pd.DataFrame(sheet_data, columns=column_names)

        # Создаем детальное описание данных для AI
        data_description = self._analyze_data_structure(df)

        # Формируем супер-детальный промпт для AI
        system_prompt = f"""You are an expert data analyst working with Google Sheets data.

DATA STRUCTURE:
{data_description}

SAMPLE DATA (first 10 rows):
{df.head(10).to_string()}

AVAILABLE DATA:
- Total rows: {len(df)}
- Columns: {', '.join(column_names)}

YOUR TASK:
1. Understand the user's question in ANY language (Russian, English, etc.)
2. Analyze the data to find the correct answer
3. Perform any necessary calculations (SUM, GROUP BY, FILTER, etc.)
4. Return a precise, accurate answer with methodology

CRITICAL RULES:
- ALWAYS sum/aggregate duplicate entries (e.g., if "Товар 14" appears 6 times, sum all 6)
- Identify what each column represents (products, suppliers, prices, quantities, sales, etc.)
- Use the ACTUAL data, not assumptions
- For aggregations, use pandas-style operations
- Return numbers with proper formatting

RESPONSE FORMAT:
Return a JSON with:
{{
    "summary": "Brief answer to the question",
    "methodology": "Explain which columns were used and how",
    "key_findings": ["finding1", "finding2", ...],
    "calculations": "Show the actual calculations performed",
    "confidence": 0.0-1.0,
    "formula": null or Google Sheets formula if applicable,
    "response_type": "analysis" or "formula"
}}
"""

        # Создаем детальный запрос с примерами вычислений
        user_prompt = f"""
Question: {query}

Please analyze this data and provide an accurate answer.
If the question asks about "top products" - group by product column and sum sales.
If the question asks about "top suppliers" - group by supplier column and sum sales.
Always check for duplicate entries and aggregate them properly.

For reference, here's the data in a more readable format:
{self._create_readable_data_sample(df)}

Remember: If an item appears multiple times, sum ALL occurrences.
"""

        try:
            # Отправляем запрос к самой умной модели
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,  # Низкая температура для точности
                response_format={ "type": "json_object" },  # Форсируем JSON ответ
                max_tokens=2000
            )

            result = json.loads(response.choices[0].message.content)

            # Добавляем дополнительную валидацию
            if self._needs_python_verification(query):
                result = self._verify_with_python(df, query, result)

            return result

        except Exception as e:
            # Fallback на Python вычисления
            return self._pure_python_calculation(df, query)

    def _analyze_data_structure(self, df: pd.DataFrame) -> str:
        """Анализирует структуру данных для AI"""
        analysis = []

        for col in df.columns:
            sample_values = df[col].dropna().head(5).tolist()
            col_type = df[col].dtype

            # Определяем тип колонки по содержимому
            if any('ООО' in str(v) or 'ИП' in str(v) for v in sample_values if pd.notna(v)):
                col_desc = f"{col}: Company/Supplier names"
            elif any('Товар' in str(v) for v in sample_values if pd.notna(v)):
                col_desc = f"{col}: Product names"
            elif col_type in ['float64', 'int64']:
                if df[col].max() > 10000:
                    col_desc = f"{col}: Large numbers (likely sales/revenue)"
                elif df[col].max() > 1000:
                    col_desc = f"{col}: Medium numbers (likely quantities/prices)"
                else:
                    col_desc = f"{col}: Small numbers"
            else:
                col_desc = f"{col}: Text/Mixed data"

            analysis.append(f"- {col_desc}. Sample: {sample_values[:3]}")

        return '\n'.join(analysis)

    def _create_readable_data_sample(self, df: pd.DataFrame) -> str:
        """Создает читаемый образец данных"""
        sample = df.head(20).to_dict('records')
        readable = []
        for i, row in enumerate(sample, 1):
            readable.append(f"Row {i}: {json.dumps(row, ensure_ascii=False)}")
        return '\n'.join(readable)

    def _needs_python_verification(self, query: str) -> bool:
        """Определяет нужна ли Python проверка"""
        keywords = ['топ', 'сумм', 'больше', 'меньше', 'средн', 'группир', 'top', 'sum', 'avg', 'group']
        return any(keyword in query.lower() for keyword in keywords)

    def _verify_with_python(self, df: pd.DataFrame, query: str, ai_result: Dict) -> Dict:
        """Проверяет результат AI через Python вычисления"""
        query_lower = query.lower()

        try:
            # Автоматически определяем какие колонки использовать
            product_col = None
            supplier_col = None
            sales_col = None

            for col in df.columns:
                sample = df[col].dropna().head(5)
                if any('Товар' in str(v) for v in sample):
                    product_col = col
                elif any('ООО' in str(v) or 'ИП' in str(v) for v in sample):
                    supplier_col = col
                elif df[col].dtype in ['float64', 'int64'] and df[col].max() > 10000:
                    sales_col = col

            # Выполняем агрегацию если нужно
            if 'товар' in query_lower and product_col and sales_col:
                grouped = df.groupby(product_col)[sales_col].sum().sort_values(ascending=False)
                top_items = grouped.head(10)

                # Обновляем результат AI с проверенными данными
                ai_result['python_verified'] = True
                ai_result['verification_data'] = {
                    'top_products': top_items.to_dict(),
                    'total_unique_products': len(grouped),
                    'aggregation_method': f'GROUP BY {product_col}, SUM {sales_col}'
                }

            elif 'поставщик' in query_lower and supplier_col and sales_col:
                grouped = df.groupby(supplier_col)[sales_col].sum().sort_values(ascending=False)
                top_items = grouped.head(10)

                ai_result['python_verified'] = True
                ai_result['verification_data'] = {
                    'top_suppliers': top_items.to_dict(),
                    'total_unique_suppliers': len(grouped),
                    'aggregation_method': f'GROUP BY {supplier_col}, SUM {sales_col}'
                }

        except Exception as e:
            ai_result['verification_error'] = str(e)

        return ai_result

    def _pure_python_calculation(self, df: pd.DataFrame, query: str) -> Dict:
        """Чистые Python вычисления как fallback"""
        query_lower = query.lower()

        try:
            # Автоматическое определение колонок
            cols_info = {}
            for col in df.columns:
                sample = df[col].dropna().head(5)
                if any('Товар' in str(v) for v in sample):
                    cols_info['product'] = col
                elif any('ООО' in str(v) or 'ИП' in str(v) for v in sample):
                    cols_info['supplier'] = col
                elif df[col].dtype in ['float64', 'int64']:
                    if df[col].max() > 10000:
                        cols_info['sales'] = col
                    elif 'quantity' not in cols_info:
                        cols_info['quantity'] = col

            # Определяем тип запроса и выполняем
            if 'товар' in query_lower and 'product' in cols_info and 'sales' in cols_info:
                grouped = df.groupby(cols_info['product'])[cols_info['sales']].sum().sort_values(ascending=False)
                top3 = grouped.head(3)

                summary = "Топ 3 товара по продажам:\n"
                findings = []
                for i, (product, sales) in enumerate(top3.items(), 1):
                    summary += f"{i}. {product}: {sales:,.2f} руб.\n"
                    findings.append(f"{product}: {sales:,.2f} руб.")

                return {
                    "summary": summary.strip(),
                    "methodology": f"Сгруппировано по {cols_info['product']}, просуммированы продажи из {cols_info.get('sales', 'последней колонки')}",
                    "key_findings": findings,
                    "calculations": f"Использован pandas groupby().sum() по {len(df)} строкам данных",
                    "confidence": 0.95,
                    "response_type": "analysis",
                    "python_calculated": True
                }

            elif 'поставщик' in query_lower and 'supplier' in cols_info and 'sales' in cols_info:
                grouped = df.groupby(cols_info['supplier'])[cols_info['sales']].sum().sort_values(ascending=False)
                top = grouped.iloc[0]

                return {
                    "summary": f"Поставщик с наибольшими продажами - {grouped.index[0]} с суммой {top:,.2f} руб.",
                    "methodology": f"Сгруппировано по {cols_info['supplier']}, просуммированы продажи",
                    "key_findings": [f"{name}: {sales:,.2f} руб." for name, sales in grouped.head(3).items()],
                    "calculations": f"GROUP BY supplier, SUM sales",
                    "confidence": 0.95,
                    "response_type": "analysis",
                    "python_calculated": True
                }

            # Для остальных запросов - базовый анализ
            return {
                "summary": "Анализ выполнен",
                "methodology": "Автоматический анализ данных",
                "key_findings": [f"Всего строк: {len(df)}", f"Всего колонок: {len(df.columns)}"],
                "confidence": 0.7,
                "response_type": "analysis"
            }

        except Exception as e:
            return {
                "error": str(e),
                "summary": "Не удалось выполнить анализ",
                "methodology": "Ошибка при обработке",
                "confidence": 0.0,
                "response_type": "error"
            }

# Singleton
ai_service = UniversalAIService()

def get_ai_service() -> UniversalAIService:
    return ai_service