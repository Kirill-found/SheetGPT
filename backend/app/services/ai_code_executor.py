"""
AI + Python Executor Service
Работает как Formula Bot:
1. AI понимает запрос и генерирует Python код
2. Python выполняет код на реальных данных
3. Возвращает 100% точный результат
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from openai import OpenAI
from app.config import settings
import json
import traceback
from io import StringIO
import sys
import re

class AICodeExecutor:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4o"  # Лучшая модель для генерации кода

    def _sanitize_custom_context(self, custom_context: Optional[str]) -> Optional[str]:
        """
        Санитизация custom_context для защиты от prompt injection
        """
        if not custom_context or not custom_context.strip():
            return None

        # Очищаем от лишних пробелов
        sanitized = custom_context.strip()

        # Проверяем длину (макс 2000 символов)
        if len(sanitized) > 2000:
            sanitized = sanitized[:2000] + "..."

        # Запрещенные паттерны для prompt injection
        dangerous_patterns = [
            r"ignore\s+(previous|above|all)\s+instructions",
            r"forget\s+(everything|all|previous)",
            r"disregard\s+(previous|above)",
            r"new\s+instructions:",
            r"system\s*:\s*",
            r"assistant\s*:\s*",
            r"<\|im_start\|>",
            r"<\|im_end\|>",
        ]

        # Проверяем на опасные паттерны
        for pattern in dangerous_patterns:
            if re.search(pattern, sanitized, re.IGNORECASE):
                # Если найден опасный паттерн - возвращаем None (игнорируем custom_context)
                print(f"⚠️ WARNING: Dangerous pattern detected in custom_context: {pattern}")
                return None

        return sanitized

    def process_with_code(self, query: str, column_names: List[str], sheet_data: List[List[Any]], history: List[Dict[str, Any]] = None, custom_context: Optional[str] = None) -> Dict[str, Any]:
        """
        Основная функция - генерирует и выполняет Python код для точных расчетов
        """
        try:
            # Шаг 0: Санитизируем custom_context
            safe_custom_context = self._sanitize_custom_context(custom_context)

            # Шаг 1: Создаем DataFrame
            df = pd.DataFrame(sheet_data, columns=column_names)

            # Шаг 2: AI генерирует Python код
            generated_code = self._generate_python_code(query, df, safe_custom_context)

            # Шаг 3: Выполняем код безопасно
            result = self._execute_python_code(generated_code, df)

            # Шаг 4: Форматируем ответ
            return self._format_response(result, generated_code, query, safe_custom_context)

        except Exception as e:
            return {
                "error": str(e),
                "summary": f"Ошибка: {str(e)}",
                "methodology": "Ошибка при обработке",
                "confidence": 0.0,
                "response_type": "error"
            }

    def _generate_python_code(self, query: str, df: pd.DataFrame, custom_context: Optional[str] = None) -> str:
        """
        AI генерирует Python код для решения задачи
        С опциональным custom_context для персонализации
        """

        # Анализируем структуру данных
        data_info = self._analyze_dataframe(df)

        # Строим базовый промпт
        prompt = f"""You are a Python data analyst expert. Generate Python code to answer this question.

QUESTION: {query}

AVAILABLE DATA:
DataFrame 'df' with {len(df)} rows and columns:
{data_info}

SAMPLE DATA (first 5 rows):
{df.head().to_string()}

RULES FOR CODE GENERATION:
1. Use pandas for all data operations
2. Variable 'df' contains the data
3. Create a variable 'result' with the final answer
4. Create a variable 'summary' with human-readable explanation
5. Create a variable 'methodology' explaining what was calculated
6. Handle duplicates properly (GROUP BY when needed)
7. For "топ товаров" - group by product column and sum sales
8. For "топ поставщиков" - group by supplier column and sum sales
9. Always aggregate duplicate entries

REQUIRED OUTPUT VARIABLES:
- result: the computed answer (number, dataframe, or list)
- summary: string with the answer in Russian
- methodology: string explaining the calculation in Russian

CONDITIONAL VARIABLES (required if you have a professional role):
- professional_insights: string - professional analysis based on your role
- recommendations: list of strings - actionable recommendations
- warnings: list of strings - potential issues or concerns

EXAMPLE CODE FOR "топ 3 товара по продажам":
```python
# Group by product and sum sales
product_sales = df.groupby('Колонка A')['Колонка E'].sum().sort_values(ascending=False)
top3 = product_sales.head(3)

# Format result
result = top3.to_dict()
summary = "Топ 3 товара по продажам:\\n"
for i, (product, sales) in enumerate(top3.items(), 1):
    summary += f"{{i}}. {{product}}: {{sales:,.2f}} руб.\\n"
summary = summary.strip()
methodology = f"Сгруппировано по товарам (Колонка A), просуммированы продажи (Колонка E). Всего уникальных товаров: {{len(product_sales)}}"

# If you have a professional role context, add insights/recommendations:
professional_insights = "Концентрация продаж на топ-3 товарах составляет 75% от общего объема. Высокая зависимость от узкого ассортимента."
recommendations = [
    "Диверсифицировать портфель продуктов для снижения рисков",
    "Проанализировать причины низких продаж остальных товаров"
]
warnings = ["Критическая зависимость от ограниченного числа SKU"]
```

NOW GENERATE CODE FOR THIS QUESTION:
{query}

Return ONLY the Python code, no explanations."""

        # Строим system prompt с custom_context (если есть)
        base_system_prompt = (
            "You are a Python data analysis expert. Generate ONLY code that uses the provided DataFrame 'df'.\n\n"
            "⛔ CRITICAL ANTI-HALLUCINATION RULES (CANNOT BE OVERRIDDEN):\n"
            "1. NEVER create new data with pd.DataFrame() or dictionaries\n"
            "2. NEVER use hardcoded product names like 'Product A', 'Product E', 'Item 1', etc.\n"
            "3. ALWAYS use df.groupby() to analyze REAL data from 'df'\n"
            "4. ALWAYS reference columns by their EXACT names shown in data_info\n"
            "5. If you create fake data, the code will FAIL validation\n\n"
            "✅ CORRECT: product_sales = df.groupby(df.columns[0])[df.columns[1]].sum()\n"
            "❌ WRONG: result = {'Product E': 3000, 'Product F': 2500}\n\n"
        )

        # Добавляем custom_context если есть
        if custom_context:
            full_system_prompt = (
                base_system_prompt +
                f"\n🎯 YOUR ROLE AND CONTEXT:\n{custom_context}\n\n"
                "⚠️ IMPORTANT: Since you have a professional role, you MUST generate these variables:\n"
                "- professional_insights: string with your professional analysis\n"
                "- recommendations: list of actionable recommendations\n"
                "- warnings: list of risks or issues to watch\n\n"
                "These fields are REQUIRED when role is specified. Analyze data from that role's perspective.\n"
                "Generate clean, working code that analyzes REAL data only."
            )
        else:
            full_system_prompt = base_system_prompt + "Generate clean, working code that analyzes REAL data only."

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": full_system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=1500
        )

        code = response.choices[0].message.content

        # Очищаем код от markdown если есть
        code = re.sub(r'^```python\n', '', code)
        code = re.sub(r'\n```$', '', code)
        code = re.sub(r'^```\n', '', code)

        return code

    def _validate_generated_code(self, code: str) -> None:
        """
        Валидирует сгенерированный код перед выполнением
        Проверяет на признаки fake data / hallucination
        """
        # Запрещенные паттерны - признаки hallucination
        forbidden_patterns = [
            (r"pd\.DataFrame\s*\(\s*\{", "Creating new DataFrame with hardcoded data"),
            (r"pd\.DataFrame\s*\(\s*\[", "Creating new DataFrame with hardcoded lists"),
            (r"['\"]Product\s+[A-Z]['\"]\s*:", "Hardcoded product name like 'Product E'"),
            (r"['\"]Item\s+\d+['\"]\s*:", "Hardcoded item name like 'Item 1'"),
            (r"result\s*=\s*\{[^}]*['\"]Product", "Result contains hardcoded 'Product'"),
            (r"result\s*=\s*\{[^}]*['\"]Item", "Result contains hardcoded 'Item'"),
        ]

        for pattern, description in forbidden_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                raise ValueError(
                    f"⛔ CODE VALIDATION FAILED: {description}\n"
                    f"AI tried to create fake data instead of analyzing real 'df'!\n"
                    f"Pattern: {pattern}\n"
                    f"Code:\n{code[:500]}"
                )

    def _execute_python_code(self, code: str, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Безопасно выполняет Python код и возвращает результат
        """
        # ВАЛИДАЦИЯ: Проверяем что код не создает fake data
        self._validate_generated_code(code)

        # Создаем безопасное окружение для выполнения
        safe_globals = {
            'df': df,
            'pd': pd,
            'np': np,
            'len': len,
            'sum': sum,
            'min': min,
            'max': max,
            'abs': abs,
            'round': round,
            'str': str,
            'int': int,
            'float': float,
            'list': list,
            'dict': dict,
            'enumerate': enumerate,
            'zip': zip,
            'sorted': sorted,
            'print': print  # Для отладки
        }

        safe_locals = {}

        # Перехватываем stdout для отладки
        old_stdout = sys.stdout
        sys.stdout = mystdout = StringIO()

        try:
            # Выполняем код
            exec(code, safe_globals, safe_locals)

            # Восстанавливаем stdout
            sys.stdout = old_stdout
            output = mystdout.getvalue()

            # Извлекаем результаты
            result = safe_locals.get('result', None)
            summary = safe_locals.get('summary', 'Результат вычислен')
            methodology = safe_locals.get('methodology', 'Python анализ данных')

            # Дополнительные переменные если есть
            key_findings = safe_locals.get('key_findings', [])
            confidence = safe_locals.get('confidence', 0.95)

            # v6.2.0: Профессиональные инсайты (если AI сгенерировал)
            professional_insights = safe_locals.get('professional_insights', None)
            recommendations = safe_locals.get('recommendations', None)
            warnings = safe_locals.get('warnings', None)

            return {
                'result': result,
                'summary': summary,
                'methodology': methodology,
                'key_findings': key_findings,
                'confidence': confidence,
                'professional_insights': professional_insights,
                'recommendations': recommendations,
                'warnings': warnings,
                'code': code,
                'output': output
            }

        except Exception as e:
            sys.stdout = old_stdout
            error_msg = f"Ошибка выполнения кода: {str(e)}\n{traceback.format_exc()}"

            # Пытаемся выполнить fallback код
            fallback_code = self._generate_fallback_code(df, code, error_msg)
            if fallback_code:
                return self._execute_python_code(fallback_code, df)

            raise Exception(error_msg)

    def _generate_fallback_code(self, df: pd.DataFrame, failed_code: str, error: str) -> Optional[str]:
        """
        Генерирует исправленный код если первая попытка не удалась
        """
        prompt = f"""The following Python code failed with an error. Fix it.

FAILED CODE:
{failed_code}

ERROR:
{error}

DataFrame structure:
{df.dtypes}

Generate CORRECTED code that will work. Return ONLY the Python code."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=1500
            )

            fixed_code = response.choices[0].message.content
            fixed_code = re.sub(r'^```python\n', '', fixed_code)
            fixed_code = re.sub(r'\n```$', '', fixed_code)

            return fixed_code
        except:
            return None

    def _analyze_dataframe(self, df: pd.DataFrame) -> str:
        """
        Анализирует структуру DataFrame для AI
        """
        analysis = []

        for col in df.columns:
            dtype = df[col].dtype
            sample_values = df[col].dropna().head(3).tolist()

            # Определяем семантический тип колонки
            semantic_type = "unknown"
            if df[col].dtype == 'object':
                if any('Товар' in str(v) for v in sample_values):
                    semantic_type = "products"
                elif any('ООО' in str(v) or 'ИП' in str(v) for v in sample_values):
                    semantic_type = "suppliers/companies"
                else:
                    semantic_type = "text"
            elif df[col].dtype in ['int64', 'float64']:
                max_val = df[col].max()
                if max_val > 100000:
                    semantic_type = "sales/revenue (large numbers)"
                elif max_val > 1000:
                    semantic_type = "quantity/price (medium numbers)"
                else:
                    semantic_type = "small numbers/ids"

            analysis.append(f"- {col}: {dtype} ({semantic_type}), sample: {sample_values}")

        return '\n'.join(analysis)

    def _format_response(self, exec_result: Dict[str, Any], code: str, query: str, custom_context: Optional[str] = None) -> Dict[str, Any]:
        """
        Форматирует финальный ответ
        С опциональными профессиональными инсайтами (если custom_context был указан)
        """
        result = exec_result.get('result')

        # Конвертируем pandas объекты в сериализуемые
        if isinstance(result, pd.DataFrame):
            result_dict = result.to_dict('records')
        elif isinstance(result, pd.Series):
            result_dict = result.to_dict()
        else:
            result_dict = result

        # Форматируем key_findings
        key_findings = exec_result.get('key_findings', [])
        if not key_findings and isinstance(result_dict, dict):
            key_findings = [f"{k}: {v:,.2f}" if isinstance(v, (int, float)) else f"{k}: {v}"
                          for k, v in list(result_dict.items())[:5]]

        # Базовый ответ
        response = {
            "summary": exec_result.get('summary', 'Результат вычислен'),
            "methodology": exec_result.get('methodology', 'Автоматический анализ с помощью Python'),
            "key_findings": key_findings,
            "confidence": exec_result.get('confidence', 0.95),
            "response_type": "analysis",
            "data": result_dict,
            "structured_data": None,  # v6.0.0: Только расчеты, без таблиц/графиков
            "code_generated": code[:500] + "..." if len(code) > 500 else code,
            "python_executed": True,
            "execution_output": exec_result.get('output', '')
        }

        # Добавляем профессиональные инсайты если custom_context был указан
        if custom_context:
            response["professional_insights"] = exec_result.get('professional_insights')
            response["recommendations"] = exec_result.get('recommendations')
            response["warnings"] = exec_result.get('warnings')

        return response

# Singleton
ai_executor = AICodeExecutor()

def get_ai_executor() -> AICodeExecutor:
    return ai_executor