"""
Hybrid Processor v9.0.0 - Гибридная архитектура обработки запросов

Архитектура:
┌─────────────────────────────────────────────────────────────┐
│                    HYBRID PROCESSOR v9.0.0                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Schema Extraction (локально, 0 tokens)                 │
│     → Определить типы колонок, уникальные значения         │
│                                                             │
│  2. Query Classification (локально, 0 tokens)              │
│     → SIMPLE / MEDIUM / COMPLEX                            │
│                                                             │
│  3. Execution Strategy:                                     │
│     ├─ SIMPLE  → Pattern Matching (0 tokens, 50ms)         │
│     ├─ MEDIUM  → Function Calling (300 tokens, 500ms)      │
│     └─ COMPLEX → Text-to-Pandas (800 tokens, 1500ms)       │
│                                                             │
│  4. Self-Correction Loop (до 3 попыток)                    │
│     → При ошибке: отправить ошибку + схему → retry         │
│                                                             │
│  5. Output Validation & Formatting                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘

Ожидаемый Success Rate: 98-99%
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from openai import AsyncOpenAI
from pathlib import Path
import os
import time
import logging

from .schema_extractor import SchemaExtractor, get_schema_extractor
from .smart_query_classifier import SmartQueryClassifier, QueryComplexity, get_smart_classifier
from .pandas_code_generator import PandasCodeGenerator, get_pandas_generator
from .function_registry import FunctionRegistry

# Load API key
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith("OPENAI_API_KEY="):
                os.environ["OPENAI_API_KEY"] = line.split("=", 1)[1].strip()
                break

logger = logging.getLogger(__name__)


class HybridProcessor:
    """
    Гибридный процессор запросов v9.0.0

    Объединяет:
    - Schema-aware processing
    - Smart query classification
    - Pattern matching для простых запросов
    - Function Calling для средних
    - Text-to-Pandas для сложных
    - Self-correction loop для retry при ошибках
    """

    # Конфигурация моделей
    MODELS = {
        "simple": None,           # Pattern matching - no LLM
        "medium": "gpt-4o-mini",  # Function Calling
        "complex": "gpt-4o"       # Code Generation
    }

    MAX_RETRIES = 2  # Количество retry при ошибке

    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.schema_extractor = get_schema_extractor()
        self.classifier = get_smart_classifier()
        self.pandas_generator = get_pandas_generator(self.client)
        self.function_registry = FunctionRegistry()

    async def process(
        self,
        query: str,
        df: pd.DataFrame,
        column_names: List[str],
        custom_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Главный метод обработки запроса.

        Args:
            query: Запрос пользователя
            df: DataFrame с данными
            column_names: Список названий колонок
            custom_context: Дополнительный контекст

        Returns:
            Результат обработки с метаданными
        """
        start_time = time.time()

        try:
            # ===== STEP 1: Schema Extraction =====
            logger.info(f"[HYBRID v9] Processing: {query[:50]}...")
            schema = self.schema_extractor.extract_schema(df)
            schema_prompt = self.schema_extractor.schema_to_prompt(schema)
            logger.info(f"[HYBRID v9] Schema extracted: {schema['column_count']} columns, {schema['row_count']} rows")

            # ===== STEP 2: Query Classification =====
            classification = self.classifier.classify(query, column_names)
            logger.info(f"[HYBRID v9] Classification: {classification.complexity.value} (confidence={classification.confidence:.2f})")

            # ===== STEP 3: Execute based on complexity =====
            result = await self._execute_with_retry(
                query=query,
                df=df,
                schema=schema,
                schema_prompt=schema_prompt,
                classification=classification,
                custom_context=custom_context
            )

            # ===== STEP 4: Format and return =====
            elapsed = time.time() - start_time
            result["processing_time"] = f"{elapsed:.2f}s"
            result["processor_version"] = "9.0.0"
            result["complexity"] = classification.complexity.value
            result["strategy"] = self._get_strategy_name(classification.complexity)

            logger.info(f"[HYBRID v9] Success! Time: {elapsed:.2f}s, Strategy: {result['strategy']}")

            return result

        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"[HYBRID v9] Error after {elapsed:.2f}s: {str(e)}")
            return self._create_error_response(str(e), elapsed)

    async def _execute_with_retry(
        self,
        query: str,
        df: pd.DataFrame,
        schema: Dict[str, Any],
        schema_prompt: str,
        classification: Any,
        custom_context: Optional[str],
        previous_error: Optional[str] = None,
        attempt: int = 0
    ) -> Dict[str, Any]:
        """
        Выполняет запрос с retry при ошибке.
        Self-correction: при ошибке передаём её в следующую попытку.
        """
        try:
            if classification.complexity == QueryComplexity.SIMPLE:
                result = await self._execute_simple(query, df, classification)
            elif classification.complexity == QueryComplexity.MEDIUM:
                result = await self._execute_medium(query, df, schema_prompt, custom_context, previous_error)
            else:  # COMPLEX
                result = await self._execute_complex(query, df, schema_prompt, custom_context, previous_error)

            # Валидация результата
            if not self._validate_result(result):
                raise ValueError("Результат не прошёл валидацию")

            result["retry_count"] = attempt
            return result

        except Exception as e:
            error_msg = str(e)
            logger.warning(f"[HYBRID v9] Attempt {attempt + 1} failed: {error_msg}")

            if attempt < self.MAX_RETRIES:
                # Self-correction: escalate to higher complexity if needed
                new_classification = self._escalate_complexity(classification, error_msg)

                logger.info(f"[HYBRID v9] Retrying with {new_classification.complexity.value}...")

                return await self._execute_with_retry(
                    query=query,
                    df=df,
                    schema=schema,
                    schema_prompt=schema_prompt,
                    classification=new_classification,
                    custom_context=custom_context,
                    previous_error=error_msg,
                    attempt=attempt + 1
                )

            raise

    def _escalate_complexity(self, classification: Any, error: str) -> Any:
        """
        Повышает уровень сложности при ошибке.
        SIMPLE → MEDIUM → COMPLEX
        """
        from .smart_query_classifier import ClassificationResult

        if classification.complexity == QueryComplexity.SIMPLE:
            return ClassificationResult(
                complexity=QueryComplexity.MEDIUM,
                confidence=0.8,
                reason=f"Escalated from SIMPLE due to error: {error[:50]}"
            )
        elif classification.complexity == QueryComplexity.MEDIUM:
            return ClassificationResult(
                complexity=QueryComplexity.COMPLEX,
                confidence=0.8,
                reason=f"Escalated from MEDIUM due to error: {error[:50]}"
            )
        else:
            return classification  # Already at max complexity

    async def _execute_simple(
        self,
        query: str,
        df: pd.DataFrame,
        classification: Any
    ) -> Dict[str, Any]:
        """
        Выполняет SIMPLE запрос через Pattern Matching.
        0 tokens, ~50ms
        """
        if not classification.suggested_function:
            raise ValueError("No function suggested for SIMPLE query")

        func_name = classification.suggested_function
        params = classification.extracted_params or {}

        # Выполняем функцию
        result = self.function_registry.execute(func_name, df, **params)

        if not result.get("success"):
            raise ValueError(result.get("error", "Function execution failed"))

        return self._format_function_result(result, func_name, params)

    async def _execute_medium(
        self,
        query: str,
        df: pd.DataFrame,
        schema_prompt: str,
        custom_context: Optional[str],
        previous_error: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Выполняет MEDIUM запрос через Function Calling.
        ~300 tokens, ~500ms
        """
        # Получаем релевантные функции
        from app.utils.query_classifier import QueryClassifier
        classifier = QueryClassifier()
        relevant_funcs = classifier.classify(query)

        # Ограничиваем до 10 функций
        tools = self.function_registry.get_tools_for_openai(relevant_funcs[:10])

        system_prompt = f"""Ты AI-ассистент для анализа данных в таблицах.

СХЕМА ДАННЫХ:
{schema_prompt}

ВАЖНО:
- Используй ТОЧНЫЕ названия колонок из схемы
- Для числовых колонок используй числовые операции
- Для категориальных колонок используй точные значения из списка
"""

        if custom_context:
            system_prompt += f"\n\nКОНТЕКСТ: {custom_context}"

        if previous_error:
            system_prompt += f"\n\nПРЕДЫДУЩАЯ ОШИБКА (избегай её): {previous_error}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]

        response = await self.client.chat.completions.create(
            model=self.MODELS["medium"],
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=0.1
        )

        # Обрабатываем tool call
        message = response.choices[0].message

        if message.tool_calls:
            tool_call = message.tool_calls[0]
            func_name = tool_call.function.name
            import json
            params = json.loads(tool_call.function.arguments)

            # Выполняем функцию
            result = self.function_registry.execute(func_name, df, **params)

            if not result.get("success"):
                raise ValueError(result.get("error", "Function execution failed"))

            return self._format_function_result(result, func_name, params)
        else:
            # Нет tool call - возвращаем текстовый ответ
            return {
                "success": True,
                "response_type": "text",
                "summary": message.content,
                "explanation": message.content
            }

    async def _execute_complex(
        self,
        query: str,
        df: pd.DataFrame,
        schema_prompt: str,
        custom_context: Optional[str],
        previous_error: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Выполняет COMPLEX запрос через Text-to-Pandas.
        ~800 tokens, ~1500ms
        """
        gen_result = await self.pandas_generator.generate_and_execute(
            query=query,
            df=df,
            schema_prompt=schema_prompt,
            max_retries=1  # Internal retries
        )

        if not gen_result["success"]:
            raise ValueError(gen_result.get("error", "Code generation failed"))

        # Форматируем результат
        formatted = self.pandas_generator.format_result(gen_result["result"])

        return {
            "success": True,
            "response_type": formatted["type"],
            "summary": formatted.get("summary", ""),
            "structured_data": formatted.get("structured_data"),
            "value": formatted.get("value"),
            "code_generated": gen_result.get("code"),
            "python_executed": True
        }

    def _format_function_result(
        self,
        result: Dict[str, Any],
        func_name: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Форматирует результат выполнения функции."""
        func_result = result.get("result")

        formatted = {
            "success": True,
            "function_used": func_name,
            "parameters": params
        }

        if isinstance(func_result, pd.DataFrame):
            formatted["response_type"] = "table"
            formatted["structured_data"] = {
                "headers": func_result.columns.tolist(),
                "rows": func_result.values.tolist()
            }
            formatted["summary"] = f"Результат: {len(func_result)} строк"

        elif isinstance(func_result, pd.Series):
            formatted["response_type"] = "series"
            formatted["structured_data"] = {
                "headers": [func_result.name or "Значение"],
                "rows": [[v] for v in func_result.tolist()]
            }

        elif isinstance(func_result, (int, float, np.number)):
            formatted["response_type"] = "number"
            formatted["value"] = float(func_result)
            formatted["summary"] = f"Результат: {func_result:,.2f}"

        elif isinstance(func_result, dict):
            # Highlight rows result
            if "highlight_rows" in func_result:
                formatted["response_type"] = "highlight"
                formatted["highlight_rows"] = func_result["highlight_rows"]
                formatted["highlight_color"] = func_result.get("color", "yellow")
                formatted["summary"] = f"Выделено {len(func_result['highlight_rows'])} строк"

            elif "rows" in func_result or "headers" in func_result:
                formatted["response_type"] = "table"
                formatted["structured_data"] = func_result
            else:
                formatted["response_type"] = "dict"
                formatted["value"] = func_result

        else:
            formatted["response_type"] = "text"
            formatted["summary"] = str(func_result)

        return formatted

    def _validate_result(self, result: Dict[str, Any]) -> bool:
        """Валидирует результат выполнения."""
        if not result.get("success", False):
            return False

        # Проверяем наличие данных
        has_data = any([
            result.get("structured_data"),
            result.get("value") is not None,
            result.get("summary"),
            result.get("highlight_rows")
        ])

        return has_data

    def _get_strategy_name(self, complexity: QueryComplexity) -> str:
        """Возвращает человекочитаемое название стратегии."""
        return {
            QueryComplexity.SIMPLE: "Pattern Matching (0 tokens)",
            QueryComplexity.MEDIUM: "Function Calling (gpt-4o-mini)",
            QueryComplexity.COMPLEX: "Text-to-Pandas (gpt-4o)"
        }[complexity]

    def _create_error_response(self, error: str, elapsed: float) -> Dict[str, Any]:
        """Создаёт response при ошибке."""
        return {
            "success": False,
            "error": error,
            "response_type": "error",
            "summary": f"Ошибка: {error}",
            "processing_time": f"{elapsed:.2f}s",
            "processor_version": "9.0.0"
        }


# Singleton
_processor = None

def get_hybrid_processor() -> HybridProcessor:
    """Возвращает singleton instance HybridProcessor."""
    global _processor
    if _processor is None:
        _processor = HybridProcessor()
    return _processor
