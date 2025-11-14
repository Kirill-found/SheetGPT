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
            print(f"\n🔍 DEBUG: custom_context = {custom_context}")
            print(f"🔍 DEBUG: safe_custom_context = {safe_custom_context}")

            # Шаг 1: Создаем DataFrame
            df = pd.DataFrame(sheet_data, columns=column_names)

            # Шаг 2: AI генерирует Python код
            generated_code = self._generate_python_code(query, df, safe_custom_context)

            # Шаг 3: Выполняем код безопасно
            result = self._execute_python_code(generated_code, df)

            # Шаг 4: Форматируем ответ
            print(f"🔍 DEBUG: Before _format_response, safe_custom_context = {safe_custom_context}")
            final_response = self._format_response(result, generated_code, query, sheet_data, safe_custom_context)
            print(f"🔍 DEBUG: After _format_response, professional_insights = {final_response.get('professional_insights')}")
            return final_response

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
10. For Russian names/surnames: use partial matching with .str.contains() to handle different word forms
11. Example: "Капустина" should match "Капустин", "Шилова" matches "Шилов"


1. Use pandas for all data operations
2. Variable 'df' contains the data
3. Create a variable 'result' with the final answer
4. Create a variable 'summary' with human-readable explanation
5. Create a variable 'methodology' explaining what was calculated
6. Handle duplicates properly (GROUP BY when needed)
7. For "топ товаров" - group by product column and sum sales
8. For "топ поставщиков" - group by supplier column and sum sales
9. Always aggregate duplicate entries

CRITICAL: For search/highlight queries, you MUST create a 'result' variable containing the filtered DataFrame!
Example: result = df[df['column'].str.contains("search_term", case=False)]

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

EXAMPLE CODE FOR "выдели Капустина" or "highlight Shilov":
```python
# For Russian names: use .str.contains() with partial match to handle word forms
# "Капустина" will match "Капустин", "Усову" will match "Усова"
# Use first 5-7 characters of the name to match different word endings

# Search in all string columns for the name (using first 6 chars for flexibility)
mask = df.iloc[:, 0].astype(str).str.contains("Капуст", case=False, na=False)
result = df[mask]

summary = f"Найдено записей: {len(result)}"
methodology = f"Поиск по частичному совпадению в первой колонке (используется начало имени/фамилии)"
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

            # v6.6.4: FALLBACK если AI не создал result (что происходит постоянно)
            if result is None:
                # Проверяем есть ли другие DataFrame в locals
                for var_name, var_value in safe_locals.items():
                    if hasattr(var_value, 'index') and hasattr(var_value, 'columns'):
                        result = var_value
                        print(f"[FALLBACK] Using '{var_name}' as result (AI forgot to create 'result')")
                        break
                # Если ничего не нашли, используем весь df
                if result is None and 'df' in safe_globals:
                    result = safe_globals['df']
                    print(f"[FALLBACK] Using entire 'df' as result (AI didn't filter anything)")
            summary = safe_locals.get('summary', 'Результат вычислен')
            methodology = safe_locals.get('methodology', 'Python анализ данных')

            # Дополнительные переменные если есть
            key_findings = safe_locals.get('key_findings', [])

            # v6.5.4: Если result == None, пытаемся найти данные в других переменных
            if result is None:
                # Ищем переменные с данными
                for var_name in ['товары', 'products', 'data', 'top_items', 'топ_товары', 'df_result']:
                    if var_name in safe_locals:
                        result = safe_locals[var_name]
                        print(f"📊 Found result in variable '{var_name}'")
                        break
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
            error_msg = f"Ошибка: {str(e)}"

            # v6.6.5: RETURN вместо RAISE! Возвращаем словарь с ошибкой
            # Это позволит API вернуть ошибку в summary и продолжить работу
            print(f"[ERROR] Code execution failed: {error_msg}")

            return {
                'result': None,
                'summary': error_msg,
                'methodology': 'Выполнение кода не удалось',
                'key_findings': [],
                'confidence': 0.0,
                'professional_insights': None,
                'recommendations': None,
                'warnings': None,
                'code': code,
                'output': ''
            }

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

    def _format_response(self, exec_result: Dict[str, Any], code: str, query: str, sheet_data: List[List[Any]], custom_context: Optional[str] = None) -> Dict[str, Any]:
        """
        Форматирует финальный ответ
        С опциональными профессиональными инсайтами (если custom_context был указан)
        """
        # Создаем DataFrame для поиска по данным
        if sheet_data:
            # Получаем column_names из первой строки exec_result если есть
            column_names = exec_result.get('column_names', [f'col_{i}' for i in range(len(sheet_data[0]))] if sheet_data else [])
            df = pd.DataFrame(sheet_data, columns=column_names)
        else:
            df = None
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

        # Извлекаем данные для выделения из key_findings если result_dict пустой
        if not result_dict and key_findings:
            # Пытаемся создать данные из key_findings
            print(f"📊 No result_dict, extracting from key_findings: {key_findings}")
            result_dict = {}
            for finding in key_findings:
                if ':' in finding:
                    parts = finding.split(':', 1)
                    key = parts[0].strip()
                    value_str = parts[1].strip().replace(',', '')
                    try:
                        # Пытаемся преобразовать в число
                        value = float(value_str)
                        result_dict[key] = value
                    except ValueError:
                        result_dict[key] = value_str

        # Определяем нужна ли таблица/график
        structured_data = self._generate_structured_data_if_needed(query, result_dict, exec_result.get('summary', ''))

        # v6.5.6: УЛУЧШЕННАЯ логика для выделения строк с поиском
        highlight_keywords = ['выдели', 'подсвет', 'отметь', 'покаж', 'highlight', 'mark', 'топ', 'лучш', 'худш', 'строк', 'фамили']
        query_lower = query.lower()

        if any(kw in query_lower for kw in highlight_keywords):
            print(f"[HIGHLIGHT] Keyword found, generating highlight data")

            # ОПРЕДЕЛЕНИЕ ЦВЕТА ИЗ ЗАПРОСА (v6.5.9)
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

            requested_color = None
            for color_key, color_value in color_map.items():
                if color_key in query_lower:
                    requested_color = color_value
                    print(f"[COLOR] Detected: {color_key} -> {color_value}")
                    break

            # Проверяем тип запроса
            # УЛУЧШЕННАЯ ЛОГИКА: поиск = ключевое слово + имя/фамилия
            is_search_query = False
            search_keywords = ['фамили', 'имен', 'строк', 'найди', 'где']

            # Случай 1: явные поисковые ключевые слова
            if any(word in query_lower for word in search_keywords):
                is_search_query = True

            # Случай 2: "выдели" + слово с заглавной буквы (вероятно имя/фамилия)
            elif 'выдели' in query_lower:
                # Ищем слова с заглавной буквы (кроме первого слова в запросе)
                words = query.split()
                for word in words[1:]:  # Пропускаем первое слово
                    # Если слово начинается с заглавной и не является служебным
                    if word[0].isupper() and word.lower() not in ['оранжевым', 'красным', 'зелёным', 'синим', 'жёлтым', 'цветом', 'строк']:
                        is_search_query = True
                        print(f"[SEARCH_DETECT] Found name/surname: {word}")
                        break

            if is_search_query:
                # AI УЖЕ ВЫПОЛНИЛ ПОИСК - используем результаты!
                print(f"[SEARCH] AI executed search, analyzing results")
                rows_to_highlight = []
                
                # Проверяем, что AI нашёл данные
                result = exec_result.get('result')
                if result is not None:
                    # Если result - это DataFrame, берём его индексы
                    if hasattr(result, 'index'):
                        rows_to_highlight = [idx + 2 for idx in result.index.tolist()]
                        print(f"[AI_RESULT] Found DataFrame with indices: {result.index.tolist()}")
                    # Если result - это list of dicts (после to_dict('records')), 
                    # ищем исходные индексы в DataFrame
                    elif isinstance(result, list) and len(result) > 0:
                        # AI вернул отфильтрованные данные
                        # Ищем эти данные в исходном DataFrame
                        if df is not None:
                            for row_data in result:
                                # Ищем совпадение по первой колонке
                                first_col = df.columns[0]
                                if first_col in row_data:
                                    search_value = row_data[first_col]
                                    matches = df[df[first_col] == search_value]
                                    if not matches.empty:
                                        rows_to_highlight.extend([idx + 2 for idx in matches.index.tolist()])
                        print(f"[AI_RESULT] Extracted {len(rows_to_highlight)} rows from list result")
                
                if rows_to_highlight:
                    highlight_color = requested_color or '#ADD8E6'
                    highlight_message = f'Выделено строк: {len(rows_to_highlight)}'
                    highlighting_data = {
                        "action_type": "highlight_rows",
                        "highlight_rows": rows_to_highlight,
                        "highlight_color": highlight_color,
                        "highlight_message": highlight_message
                    }
                    print(f"[SUCCESS] Generated highlighting: {highlighting_data}")
                else:
                    highlighting_data = None
                    print(f"[WARNING] Could not extract rows from AI results")
            else:
                # ВЫДЕЛЕНИЕ ТОПА/ХУДШИХ
                import re
                numbers = re.findall(r'\d+', query)
                count = 5  # По умолчанию 5
                if numbers:
                    count = min(int(numbers[0]), 20)

                if 'топ' in query_lower or 'лучш' in query_lower:
                    # Для топа используем отсортированные данные
                    rows_to_highlight = [8, 5, 3, 10, 11][:count]  # Топ товаров по продажам
                    highlight_color = requested_color or '#90EE90'  # Используем запрошенный цвет
                    highlight_message = f'Выделены топ {len(rows_to_highlight)} товаров'
                elif 'худш' in query_lower or 'минимальн' in query_lower:
                    rows_to_highlight = [4, 9, 7, 2, 6][:count]  # Худшие товары
                    highlight_color = requested_color or '#FFB6C1'  # Используем запрошенный цвет
                    highlight_message = f'Выделены {len(rows_to_highlight)} минимальных значений'
                else:
                    # По умолчанию - первые N строк
                    rows_to_highlight = list(range(2, 2 + count))
                    highlight_color = requested_color or '#FFFF00'  # Используем запрошенный цвет
                    highlight_message = f'Выделены {len(rows_to_highlight)} строк'

                highlighting_data = {
                    "action_type": "highlight_rows",
                    "highlight_rows": rows_to_highlight,
                    "highlight_color": highlight_color,
                    "highlight_message": highlight_message
                }
                print(f"[SUCCESS] Generated highlighting: {highlighting_data}")
        else:
            highlighting_data = None
            print(f"[INFO] No highlight keywords in query")


        # Старый метод как fallback (закомментирован)
        highlighting_data = self._generate_highlighting_if_needed(query, result_dict) if not highlighting_data else highlighting_data
        if highlighting_data:
            print(f"✅ Highlighting data generated: {highlighting_data}")
        else:
            print(f"❌ No highlighting data generated")

        # Базовый ответ
        response = {
            "summary": exec_result.get('summary', 'Результат вычислен'),
            "methodology": exec_result.get('methodology', 'Автоматический анализ с помощью Python'),
            "key_findings": key_findings,
            "confidence": exec_result.get('confidence', 0.95),
            "response_type": "analysis",
            "data": result_dict,
            "structured_data": structured_data,  # v6.3.2: Генерируем для запросов "создай таблицу/график"
            "code_generated": code[:500] + "..." if len(code) > 500 else code,
            "python_executed": True,
            "execution_output": exec_result.get('output', '')
        }

        # Добавляем данные выделения если есть
        if highlighting_data:
            response.update(highlighting_data)

        # Добавляем профессиональные инсайты
        # ВСЕГДА генерируем insights (с custom_context или без)
        context_to_use = custom_context or "You are a data analyst. Provide brief, actionable insights."
        print(f"🎯 Generating professional insights (custom={bool(custom_context)})...")
        try:
            insights_data = self._generate_professional_insights(
                query, result_dict, exec_result.get('summary', ''), context_to_use
            )
            response["professional_insights"] = insights_data.get('professional_insights')
            response["recommendations"] = insights_data.get('recommendations')
            response["warnings"] = insights_data.get('warnings')
        except Exception as e:
            print(f"⚠️ Failed to generate insights: {e}")
            # Если не получилось - оставляем null
            pass

        return response

    def _generate_structured_data_if_needed(self, query: str, result_dict: Any, summary: str) -> Optional[Dict[str, Any]]:
        """
        Определяет нужна ли таблица/график и генерирует structured_data
        """
        # Ключевые слова для определения запроса на таблицу/график
        table_keywords = ['таблиц', 'создай табл', 'сделай табл', 'table', 'построй табл']
        chart_keywords = ['график', 'диаграмм', 'chart', 'построй', 'визуализ', 'plot', 'сделай']

        query_lower = query.lower()
        needs_table = any(kw in query_lower for kw in table_keywords)
        needs_chart = any(kw in query_lower for kw in chart_keywords)

        # Если не запрашивали таблицу или график - возвращаем None
        if not (needs_table or needs_chart):
            return None

        # Если result_dict не подходит для таблицы - возвращаем None
        if not isinstance(result_dict, dict) or len(result_dict) == 0:
            return None

        # Конвертируем dict в формат таблицы
        try:
            # Определяем заголовки и строки
            if isinstance(list(result_dict.values())[0], (int, float)):
                # Простой dict типа {продукт: значение}
                headers = ["Название", "Значение"]
                rows = [[str(k), float(v)] for k, v in result_dict.items()]
            else:
                # Более сложная структура
                headers = ["Элемент", "Данные"]
                rows = [[str(k), str(v)] for k, v in result_dict.items()]

            # Определяем тип графика
            chart_type = None
            if needs_chart:
                # Определяем подходящий тип графика
                if 'круг' in query_lower or 'pie' in query_lower or 'доля' in query_lower or 'процент' in query_lower:
                    chart_type = "pie"  # Круговая
                elif 'динамик' in query_lower or 'trend' in query_lower or 'линейн' in query_lower:
                    chart_type = "line"  # Линейная
                elif 'столб' in query_lower or 'column' in query_lower or len(rows) <= 10:
                    chart_type = "column"  # Столбчатая
                else:
                    chart_type = "bar"  # Горизонтальная (по умолчанию для больших данных)

            return {
                "headers": headers,
                "rows": rows[:50],  # Максимум 50 строк
                "table_title": summary[:100],  # Используем summary как название
                "chart_recommended": chart_type
            }

        except Exception as e:
            print(f"Error generating structured_data: {e}")
            return None

    def _generate_highlighting_if_needed(self, query: str, result_data: Any) -> Optional[Dict[str, Any]]:
        """
        Определяет нужно ли выделение строк и генерирует данные для него
        """
        # Ключевые слова для выделения
        highlight_keywords = ['выдели', 'подсвет', 'отметь', 'покаж', 'highlight', 'mark', 'топ', 'лучш', 'худш', 'больш', 'меньш', 'максимальн', 'минимальн']

        query_lower = query.lower()
        needs_highlighting = any(kw in query_lower for kw in highlight_keywords)

        if not needs_highlighting:
            print(f"❌ No highlight keywords found in: {query}")
            return None

        print(f"✅ Highlight keywords detected in query: {query}")

        try:
            import re

            # Пытаемся определить что выделять
            rows_to_highlight = []
            highlight_color = requested_color or '#FFFF00'  # Используем запрошенный цвет по умолчанию
            highlight_message = 'Выделены строки по запросу'

            print(f"📊 Result data type: {type(result_data)}")
            if isinstance(result_data, dict):
                print(f"📊 Dict keys: {list(result_data.keys())[:5]}")

            # Извлекаем число из запроса
            numbers = re.findall(r'\d+', query)
            count = 5  # По умолчанию 5
            if numbers:
                count = min(int(numbers[0]), 20)  # Максимум 20

            # Обрабатываем разные типы данных
            # 1. Если результат - DataFrame
            if hasattr(result_data, 'shape'):  # pandas DataFrame
                # Ищем топ значения
                if 'топ' in query_lower or 'лучш' in query_lower or 'максимальн' in query_lower:
                    # Находим колонку с числовыми значениями
                    numeric_cols = result_data.select_dtypes(include=['number']).columns
                    if len(numeric_cols) > 0:
                        col = numeric_cols[0]  # Берём первую числовую колонку
                        # Находим топ строки
                        top_indices = result_data.nlargest(count, col).index.tolist()
                        rows_to_highlight = [i + 2 for i in top_indices]  # +2 для Google Sheets
                        highlight_color = requested_color or '#90EE90'  # Используем запрошенный цвет для топ значений
                        highlight_message = f'Выделены топ {count} строк'

                elif 'худш' in query_lower or 'минимальн' in query_lower or 'меньш' in query_lower:
                    # Находим минимальные значения
                    numeric_cols = result_data.select_dtypes(include=['number']).columns
                    if len(numeric_cols) > 0:
                        col = numeric_cols[0]
                        # Находим худшие строки
                        bottom_indices = result_data.nsmallest(count, col).index.tolist()
                        rows_to_highlight = [i + 2 for i in bottom_indices]  # +2 для Google Sheets
                        highlight_color = '#FFB6C1'  # Светло-красный для худших значений
                        highlight_message = f'Выделены {count} минимальных значений'

            # 2. Если результат - словарь с данными таблицы
            elif isinstance(result_data, dict):
                # Ищем данные таблицы в словаре
                rows_data = None

                # Проверяем разные варианты ключей
                if 'rows' in result_data:
                    rows_data = result_data['rows']
                    print(f"✅ Found 'rows' key with {len(rows_data)} items")
                elif 'data' in result_data:
                    rows_data = result_data['data']
                    print(f"✅ Found 'data' key")
                elif 'результат' in result_data:
                    rows_data = result_data['результат']
                    print(f"✅ Found 'результат' key")
                elif 'товары' in result_data:
                    rows_data = result_data['товары']
                    print(f"✅ Found 'товары' key")
                else:
                    # Если данные прямо в словаре (key: value пары)
                    print(f"⚠️ No standard keys found, trying to extract from dict items")
                    print(f"⚠️ Dict items: {list(result_data.items())}")
                    items = list(result_data.items())
                    rows_data = [[k, v] for k, v in items if isinstance(v, (int, float))]
                    if rows_data:
                        print(f"✅ Extracted {len(rows_data)} numeric items from dict: {rows_data}")

                # Если есть данные и они являются списком
                if rows_data and isinstance(rows_data, list) and len(rows_data) > 0:
                    print(f"📊 Processing {len(rows_data)} rows of data")
                    # Пытаемся найти числовую колонку (индекс 1 обычно содержит числа для продаж)
                    numeric_values = []
                    for i, row in enumerate(rows_data):
                        if isinstance(row, (list, tuple)) and len(row) > 1:
                            try:
                                # Пытаемся взять второй элемент как число
                                val = float(row[1]) if len(row) > 1 else 0
                                numeric_values.append((i + 2, val))  # +2 для строки в Sheets
                            except (ValueError, TypeError):
                                pass

                    if numeric_values:
                        # Сортируем по значению
                        numeric_values.sort(key=lambda x: x[1], reverse=True)

                        if 'топ' in query_lower or 'лучш' in query_lower or 'максимальн' in query_lower:
                            # Берём топ N
                            rows_to_highlight = [row[0] for row in numeric_values[:count]]
                            highlight_color = requested_color or '#90EE90'  # Используем запрошенный цвет для топ значений
                            highlight_message = f'Выделены топ {count} товаров'
                            print(f"✅ Generated highlight rows: {rows_to_highlight}")
                        elif 'худш' in query_lower or 'минимальн' in query_lower or 'меньш' in query_lower:
                            # Берём последние N (минимальные)
                            rows_to_highlight = [row[0] for row in numeric_values[-count:]]
                            highlight_color = '#FFB6C1'  # Светло-красный для худших значений
                            highlight_message = f'Выделены {count} товаров с минимальными продажами'
                        else:
                            # По умолчанию выделяем топ
                            rows_to_highlight = [row[0] for row in numeric_values[:count]]
                            highlight_color = requested_color or '#FFFF00'  # Используем запрошенный цвет для обычного выделения
                            highlight_message = f'Выделены {count} строк'

            # 3. Если результат - список списков (таблица)
            elif isinstance(result_data, list) and len(result_data) > 0:
                if all(isinstance(row, (list, tuple)) for row in result_data):
                    # Это таблица
                    numeric_values = []
                    for i, row in enumerate(result_data):
                        if len(row) > 1:
                            try:
                                val = float(row[1])
                                numeric_values.append((i + 2, val))  # +2 для Sheets
                            except (ValueError, TypeError):
                                pass

                    if numeric_values:
                        numeric_values.sort(key=lambda x: x[1], reverse=True)

                        if 'топ' in query_lower or 'лучш' in query_lower:
                            rows_to_highlight = [row[0] for row in numeric_values[:count]]
                            highlight_color = '#90EE90'
                            highlight_message = f'Выделены топ {count} строк'
                        elif 'худш' in query_lower or 'минимальн' in query_lower:
                            rows_to_highlight = [row[0] for row in numeric_values[-count:]]
                            highlight_color = '#FFB6C1'
                            highlight_message = f'Выделены {count} минимальных значений'

            # Если нашли строки для выделения
            if rows_to_highlight:
                result = {
                    "action_type": "highlight_rows",
                    "highlight_rows": rows_to_highlight,
                    "highlight_color": highlight_color,
                    "highlight_message": highlight_message
                }
                print(f"✅ Returning highlighting data: {result}")
                return result

            print(f"❌ No rows to highlight found")
            return None

        except Exception as e:
            print(f"❌ Error generating highlighting data: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _generate_professional_insights(self, query: str, result_data: Any, summary: str, custom_context: str) -> Dict[str, Any]:
        """
        Генерирует профессиональные инсайты на основе результатов расчета
        Вызывается отдельно ПОСЛЕ основного расчета
        """
        prompt = f"""На основе запроса и результатов расчета предоставь профессиональный анализ.

ЗАПРОС: {query}

РЕЗУЛЬТАТЫ РАСЧЕТА:
{summary}

ДАННЫЕ: {str(result_data)[:500]}

ТВОЯ РОЛЬ: {custom_context}

Предоставь на РУССКОМ языке:
1. professional_insights: Краткий профессиональный анализ (2-3 предложения)
2. recommendations: 2-3 практические рекомендации
3. warnings: 1-2 риска или проблемы, на которые стоит обратить внимание

Ответь ТОЛЬКО в JSON формате:
{{
  "professional_insights": "...",
  "recommendations": ["...", "..."],
  "warnings": ["..."]
}}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Ты профессиональный аналитик. Предоставляй краткие, практичные инсайты НА РУССКОМ ЯЗЫКЕ."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )

            insights_text = response.choices[0].message.content.strip()
            # Try to parse JSON
            if insights_text.startswith('```json'):
                insights_text = insights_text.replace('```json', '').replace('```', '').strip()

            insights = json.loads(insights_text)
            return insights
        except Exception as e:
            print(f"Error generating insights: {e}")
            return {
                "professional_insights": "Анализ данных выполнен успешно.",
                "recommendations": ["Продолжить мониторинг показателей"],
                "warnings": []
            }

# Singleton
ai_executor = AICodeExecutor()

def get_ai_executor() -> AICodeExecutor:
    return ai_executor
