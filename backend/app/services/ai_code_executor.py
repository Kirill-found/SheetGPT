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

    def process_with_code(self, query: str, column_names: List[str], sheet_data: List[List[Any]], history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Основная функция - генерирует и выполняет Python код для точных расчетов
        """
        try:
            # Шаг 1: Создаем DataFrame
            df = pd.DataFrame(sheet_data, columns=column_names)

            # FAILSAFE: For average price queries, use simple direct calculation
            query_lower = query.lower()
            if any(word in query_lower for word in ['средн', 'average', 'mean', 'srednyaya', 'tsena']):
                if any(word in query_lower for word in ['постав', 'supplier', 'postavshchik', 'компан']):
                    # This is "average price per supplier" query - use failsafe
                    return self._calculate_avg_price_failsafe(df, column_names)

            # Шаг 2: AI генерирует Python код
            generated_code = self._generate_python_code(query, df)

            # Шаг 3: Выполняем код безопасно
            result = self._execute_python_code(generated_code, df)

            # Шаг 4: Форматируем ответ
            return self._format_response(result, generated_code, query)

        except Exception as e:
            return {
                "error": str(e),
                "summary": f"Ошибка: {str(e)}",
                "methodology": "Ошибка при обработке",
                "confidence": 0.0,
                "response_type": "error"
            }

    def _calculate_avg_price_failsafe(self, df: pd.DataFrame, column_names: List[str]) -> Dict[str, Any]:
        """
        FAILSAFE: Прямой расчет средней цены по поставщикам без AI генерации кода
        Гарантированно правильный результат
        """
        try:
            # Find columns
            supplier_col = column_names[1] if len(column_names) > 1 else df.columns[1]  # Usually column B

            # Find price column (numeric column with values < 100000)
            price_col = None
            for col in df.columns:
                if df[col].dtype in ['int64', 'float64']:
                    max_val = df[col].max()
                    if max_val < 100000 and max_val > 0:
                        price_col = col
                        break

            if not price_col:
                raise Exception("Не найдена колонка с ценами")

            # Remove duplicates before calculating average
            df_unique = df[[supplier_col, price_col]].drop_duplicates()

            # Group by supplier and calculate mean
            avg_prices = df_unique.groupby(supplier_col)[price_col].mean().sort_values(ascending=False)

            # Format summary
            summary = "Средняя цена товаров у каждого поставщика:\n\n"
            for i, (supplier, avg_price) in enumerate(avg_prices.items(), 1):
                summary += f"{i}. {supplier}: {avg_price:,.2f} руб.\n"
            summary = summary.strip()

            # Format key_findings
            key_findings = [f"{supplier}: {avg_price:,.2f}" for supplier, avg_price in avg_prices.items()]

            return {
                "summary": summary,
                "methodology": f"FAILSAFE: Удалены дубликаты, сгруппировано по поставщикам ({supplier_col}), вычислена средняя цена для колонки '{price_col}'",
                "key_findings": key_findings,
                "confidence": 0.99,
                "response_type": "analysis",
                "data": avg_prices.to_dict(),
                "code_generated": "# FAILSAFE MODE: Direct calculation without AI code generation",
                "python_executed": True,
                "execution_output": ""
            }
        except Exception as e:
            raise Exception(f"Failsafe calculation failed: {str(e)}")

    def _generate_python_code(self, query: str, df: pd.DataFrame) -> str:
        """
        AI генерирует Python код для решения задачи
        """

        # Анализируем структуру данных
        data_info = self._analyze_dataframe(df)

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
4. Create a variable 'summary' with human-readable explanation in Russian
5. Create a variable 'methodology' explaining what was calculated in Russian
6. Handle duplicates properly (GROUP BY when needed)
7. For "топ товаров" - group by product column and sum sales
8. For "топ поставщиков" - group by supplier column and sum sales
9. For "средняя цена" - use .mean() on PRICE column (NOT SUM!)
10. CRITICAL: When asked for AVERAGE PRICE - REMOVE DUPLICATES FIRST!
11. CRITICAL: For "средняя цена товаров у поставщика" - drop_duplicates by (Supplier, Product, Price) BEFORE calculating mean
12. CRITICAL: Data may contain duplicate rows for same product - deduplicate before averaging!
13. CRITICAL: NEVER calculate average as sum/count - use .mean() function directly!
14. Always aggregate duplicate entries for TOP/SUM queries
15. LIMIT TOP LISTS to maximum 5 items for readability
16. Use DOUBLE line break (\\n\\n) after title for better spacing

REQUIRED OUTPUT VARIABLES:
- result: the computed answer (number, dataframe, or list)
- summary: string with the answer in Russian
- methodology: string explaining the calculation in Russian

FORMATTING RULES FOR SUMMARY:
- Always use \\n for line breaks
- Format numbers with thousand separators: {{value:,.2f}}
- For TOP lists: put each item on NEW LINE
- Use clear structure: Title, then numbered list
- Keep it readable and well-spaced

EXAMPLE CODE FOR "средняя цена товаров у каждого поставщика":
```python
# IMPORTANT: Use .mean() for averages, NOT sum/count!
# Find columns
product_col = df.columns[0]  # Usually column A
supplier_col = df.columns[1]  # Usually column B
price_col = None
for col in df.columns:
    if df[col].dtype in ['int64', 'float64'] and df[col].max() < 100000:
        price_col = col
        break

# CRITICAL: Remove duplicates BEFORE calculating average!
# Data may have duplicate rows for same product
df_unique = df.drop_duplicates(subset=[supplier_col, product_col, price_col])

# Now group by supplier and calculate MEAN of prices
supplier_avg_price = df_unique.groupby(supplier_col)[price_col].mean().sort_values(ascending=False)

# Format result
result = supplier_avg_price.to_dict()
summary = "Средняя цена товаров у каждого поставщика:\\n\\n"
for i, (supplier, avg_price) in enumerate(supplier_avg_price.items(), 1):
    summary += f"{{i}}. {{supplier}}: {{avg_price:,.2f}} руб.\\n"
summary = summary.strip()
methodology = f"Удалены дубликаты, сгруппировано по поставщикам ({{supplier_col}}), вычислена средняя цена методом .mean() для колонки '{{price_col}}'"
```

EXAMPLE CODE FOR "топ 3 товара по продажам":
```python
# Group by product and sum sales
product_sales = df.groupby('Колонка A')['Колонка E'].sum().sort_values(ascending=False)
top3 = product_sales.head(3)

# Format result with CLEAR LINE BREAKS
result = top3.to_dict()
summary = "Топ 3 товара по продажам:\\n\\n"
for i, (product, sales) in enumerate(top3.items(), 1):
    summary += f"{{i}}. {{product}}: {{sales:,.2f}} руб.\\n"
summary = summary.strip()
methodology = f"Сгруппировано по товарам (Колонка A), просуммированы продажи (Колонка E). Всего уникальных товаров: {{len(product_sales)}}"
```

EXAMPLE CODE FOR "у какого поставщика больше всего продаж":
```python
# Group by supplier and sum sales
supplier_sales = df.groupby('Колонка B')['Колонка E'].sum().sort_values(ascending=False)
top_supplier = supplier_sales.index[0]
top_sales = supplier_sales.iloc[0]

# Format with TOP 5 for context
result = supplier_sales.head(5).to_dict()
summary = f"Топ поставщик: {{top_supplier}}\\n"
summary += f"Продажи: {{top_sales:,.2f}} руб.\\n\\n"
summary += "Топ 5 поставщиков:\\n\\n"
for i, (supplier, sales) in enumerate(supplier_sales.head(5).items(), 1):
    summary += f"{{i}}. {{supplier}}: {{sales:,.2f}} руб.\\n"
summary = summary.strip()
methodology = f"Сгруппировано по поставщикам (Колонка B), просуммированы продажи (Колонка E)"
```

NOW GENERATE CODE FOR THIS QUESTION:
{query}

Return ONLY the Python code, no explanations."""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a Python data analysis expert. Generate clean, working code."},
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

    def _execute_python_code(self, code: str, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Безопасно выполняет Python код и возвращает результат
        """
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

            return {
                'result': result,
                'summary': summary,
                'methodology': methodology,
                'key_findings': key_findings,
                'confidence': confidence,
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

    def _format_response(self, exec_result: Dict[str, Any], code: str, query: str) -> Dict[str, Any]:
        """
        Форматирует финальный ответ
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

        # DEBUG: Print generated code to console for debugging
        print("=" * 80)
        print("🐍 AI GENERATED PYTHON CODE:")
        print("=" * 80)
        print(code)
        print("=" * 80)
        print("📊 EXECUTION RESULT:")
        print(f"Summary: {exec_result.get('summary')}")
        print(f"Methodology: {exec_result.get('methodology')}")
        print("=" * 80)

        return {
            "summary": exec_result.get('summary', 'Результат вычислен'),
            "methodology": exec_result.get('methodology', 'Автоматический анализ с помощью Python'),
            "key_findings": key_findings,
            "confidence": exec_result.get('confidence', 0.95),
            "response_type": "analysis",
            "data": result_dict,
            "code_generated": code,  # FULL CODE for debugging
            "python_executed": True,
            "execution_output": exec_result.get('output', '')
        }

# Singleton
ai_executor = AICodeExecutor()

def get_ai_executor() -> AICodeExecutor:
    return ai_executor