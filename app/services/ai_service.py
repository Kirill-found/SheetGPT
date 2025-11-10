from openai import AsyncOpenAI
import json
import time
from typing import List, Any, Dict
from app.core.config import settings


class AIService:
    """Профессиональный AI помощник для Google Sheets"""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4o-mini"

    async def process_query(
        self, query: str, column_names: List[str], sample_data: List[List[Any]] = None
    ) -> dict:
        """
        Главная функция - определяет тип запроса и обрабатывает соответственно

        Returns:
            dict с типом ответа и данными
        """
        # Классифицируем запрос
        query_type = await self._classify_query(query)

        # Убираем заголовки из sample_data (первая строка)
        data_without_headers = sample_data[1:] if sample_data and len(sample_data) > 1 else []

        if query_type == "formula":
            return await self.generate_formula(query, column_names, data_without_headers)
        elif query_type == "analysis":
            return await self.analyze_data(query, data_without_headers, column_names)
        elif query_type == "question":
            return await self.answer_question(query, data_without_headers, column_names)
        else:
            # Дефолт - пробуем формулу
            return await self.generate_formula(query, column_names, data_without_headers)

    async def _classify_query(self, query: str) -> str:
        """
        Определяет тип запроса пользователя

        Returns:
            "formula" | "analysis" | "visualization" | "question"
        """
        query_lower = query.lower()

        # Ключевые слова для анализа
        analysis_keywords = [
            "исходя", "отбери", "найди", "покажи", "выведи", "топ", "лучш",
            "худш", "самы", "расчет", "рассчит", "вывод", "почему", "как",
            "анализ", "статистик", "тренд"
        ]

        # Ключевые слова для формул
        formula_keywords = [
            "формул", "сумм", "средн", "количеств", "count", "sum", "average",
            "если", "if", "vlookup", "filter"
        ]

        # Ключевые слова для вопросов
        question_keywords = ["почему", "как", "что такое", "объясни", "расскажи"]

        # Проверяем вопросы
        if any(kw in query_lower for kw in question_keywords):
            return "question"

        # Проверяем анализ (приоритет выше формул!)
        if any(kw in query_lower for kw in analysis_keywords):
            return "analysis"

        # Проверяем формулы
        if any(kw in query_lower for kw in formula_keywords):
            return "formula"

        # По умолчанию - анализ (более гибко)
        return "analysis"

    async def generate_formula(
        self, query: str, column_names: List[str], sample_data: List[List[Any]] = None
    ) -> dict:
        """Генерирует Google Sheets формулу"""
        start_time = time.time()

        # Анализируем типы данных в колонках
        column_types = self._analyze_column_types(column_names, sample_data)

        # Формируем улучшенный промпт
        prompt = self._build_formula_prompt(query, column_names, sample_data, column_types)

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert Google Sheets formula generator.

CRITICAL RULES:
1. NEVER use spaces in formulas - formulas must be compact
2. Use ONLY valid Google Sheets syntax (not Excel!)
3. Column references must be exact: A, B, C or A2:A100
4. Always test logic before responding
5. Respond ONLY in valid JSON format

Example GOOD formula: =SORT(FILTER(A2:G,C2:C>500000),3,FALSE)
Example BAD formula: =SORT( FILTER( A2:G, C2:C > 500000 ), 3, FALSE )

NO SPACES IN FORMULAS!"""
                    },
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=600,
            )

            result = json.loads(response.choices[0].message.content)

            # Удаляем пробелы из формулы (на всякий случай)
            if "formula" in result:
                result["formula"] = self._clean_formula(result["formula"])

            result["processing_time"] = time.time() - start_time
            result["type"] = "formula"

            return result

        except Exception as e:
            return {
                "type": "error",
                "formula": "=ERROR()",
                "explanation": f"Ошибка генерации формулы: {str(e)}",
                "confidence": 0.0,
                "processing_time": time.time() - start_time
            }

    def _clean_formula(self, formula: str) -> str:
        """Удаляет лишние пробелы из формулы"""
        # Удаляем пробелы вокруг операторов
        formula = formula.replace(" >", ">").replace("> ", ">")
        formula = formula.replace(" <", "<").replace("< ", "<")
        formula = formula.replace(" =", "=").replace("= ", "=")
        formula = formula.replace(" ,", ",").replace(", ", ",")
        formula = formula.replace(" )", ")").replace("( ", "(")

        # Удаляем множественные пробелы
        while "  " in formula:
            formula = formula.replace("  ", "")

        return formula

    def _analyze_column_types(self, column_names: List[str], sample_data: List[List[Any]]) -> Dict[str, str]:
        """Определяет типы данных в колонках"""
        column_types = {}

        if not sample_data or len(sample_data) == 0:
            return column_types

        for i, col_name in enumerate(column_names):
            # Смотрим на первые несколько значений
            values = [row[i] if i < len(row) else None for row in sample_data[:5]]
            values = [v for v in values if v is not None]

            if not values:
                column_types[col_name] = "unknown"
                continue

            # Определяем тип
            if all(isinstance(v, (int, float)) for v in values):
                column_types[col_name] = "number"
            elif all(str(v).replace('.', '').replace(',', '').replace('%', '').replace('р', '').replace('p', '').strip().replace('-', '').isdigit() for v in values):
                column_types[col_name] = "number_formatted"
            else:
                column_types[col_name] = "text"

        return column_types

    def _build_formula_prompt(
        self, query: str, column_names: List[str], sample_data: List[List[Any]], column_types: Dict
    ) -> str:
        """Строит промпт для генерации формулы"""

        # Форматируем sample data красиво
        sample_rows = []
        if sample_data:
            for row in sample_data[:3]:
                sample_rows.append(" | ".join([str(v) for v in row]))

        columns_info = []
        for i, col in enumerate(column_names):
            col_letter = chr(65 + i)  # A, B, C...
            col_type = column_types.get(col, "unknown")
            columns_info.append(f"{col_letter}: {col} ({col_type})")

        prompt = f"""Generate a Google Sheets formula for this request.

TABLE STRUCTURE:
Columns: {len(column_names)}
{chr(10).join(columns_info)}

SAMPLE DATA (without headers):
{chr(10).join(sample_rows) if sample_rows else "No data"}

USER REQUEST (Russian): {query}

IMPORTANT REQUIREMENTS:
1. NO SPACES in formula - must be compact like =SORT(FILTER(A2:G,C2:C>500000),3,FALSE)
2. Use correct column letters (A, B, C, etc.)
3. Data starts from row 2 (row 1 is headers)
4. Use Google Sheets functions: FILTER, SORT, QUERY, SUMIF, AVERAGEIF, COUNTIF, etc.
5. For sorting: use SORT() function
6. For filtering: use FILTER() function
7. Respond in Russian but formula in English

Response format (JSON):
{{
  "formula": "=SORT(FILTER(A2:G,C2:C>500000),3,FALSE)",
  "explanation": "Подробное объяснение на русском что делает формула",
  "target_cell": "I2",
  "confidence": 0.95
}}

If request is unclear, set confidence < 0.6 and explain what's missing."""

        return prompt

    async def analyze_data(
        self, query: str, sample_data: List[List[Any]], column_names: List[str]
    ) -> dict:
        """
        Анализирует данные и возвращает развернутый ответ
        """
        start_time = time.time()

        # Формируем промпт для анализа
        sample_rows = []
        if sample_data:
            for row in sample_data[:10]:  # Берем больше данных для анализа
                sample_rows.append(row)

        prompt = f"""Analyze this Google Sheets data and answer the question.

COLUMNS: {', '.join(column_names)}

DATA (first 10 rows without headers):
{json.dumps(sample_rows, ensure_ascii=False)}

USER QUESTION (Russian): {query}

TASK:
1. Analyze the data based on the question
2. Provide detailed answer in Russian
3. If you need to calculate something, show the logic
4. Be specific and actionable

Response format (JSON):
{{
  "answer": "Подробный ответ на русском языке с конкретными цифрами и выводами",
  "insights": ["Инсайт 1", "Инсайт 2"],
  "suggested_actions": ["Рекомендация 1", "Рекомендация 2"],
  "confidence": 0.9
}}"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional data analyst. Provide detailed, actionable insights in Russian."
                    },
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=1000,
            )

            result = json.loads(response.choices[0].message.content)
            result["processing_time"] = time.time() - start_time
            result["type"] = "analysis"

            return result

        except Exception as e:
            return {
                "type": "error",
                "answer": f"Ошибка анализа: {str(e)}",
                "insights": [],
                "suggested_actions": [],
                "confidence": 0.0,
                "processing_time": time.time() - start_time
            }

    async def answer_question(
        self, query: str, sample_data: List[List[Any]], column_names: List[str]
    ) -> dict:
        """Отвечает на вопрос о данных"""
        # Используем ту же логику что и analyze_data
        return await self.analyze_data(query, sample_data, column_names)


# Синглтон
ai_service = AIService()
