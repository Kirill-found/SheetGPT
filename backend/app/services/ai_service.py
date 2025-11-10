from openai import AsyncOpenAI
import json
import time
import asyncio
import re
from typing import List, Any, Dict, Optional
from app.core.config import settings
from app.services.formula_validator import FormulaValidator
from app.services.formula_fixer import FormulaFixer
from app.services.formula_executor import MockFormulaExecutor
from app.services.healing_service import HealingService
import pandas as pd
import numpy as np

# PHASE 1.3: Константы для timeout и limits
# EMERGENCY DEPLOYMENT: 2025-11-10 15:00 UTC - v1.5.0 - GPT-4o ONLY (Railway cache issue)
MAX_HEAL_ATTEMPTS = 3
TOTAL_GENERATION_TIMEOUT = 30.0  # секунд
PER_ATTEMPT_TIMEOUT = 10.0  # секунд на одну попытку healing


class AIService:
    """Профессиональный AI помощник для Google Sheets"""

    def __init__(self, openai_api_key: Optional[str] = None, enable_test_and_heal: bool = False):
        """
        Args:
            openai_api_key: OpenAI API key (если None, использует settings.OPENAI_API_KEY)
            enable_test_and_heal: Включить Test-and-Heal loop (требует Google credentials)
        """
        api_key = openai_api_key or settings.OPENAI_API_KEY
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = "gpt-4o"  # Upgraded from gpt-4o-mini for better reasoning

        # Validator & Fixer для автоматического исправления формул
        self.validator = FormulaValidator()
        self.fixer = FormulaFixer()

        # Test-and-Heal компоненты (опциональные)
        self.enable_test_and_heal = enable_test_and_heal
        if enable_test_and_heal:
            self.executor = MockFormulaExecutor()  # Mock для тестов, в проде нужен реальный
            self.healing_service = HealingService(self.client)
        else:
            self.executor = None
            self.healing_service = None

        # Статистика
        self.stats = {
            "total_requests": 0,
            "template_hits": 0,
            "gpt_calls": 0,
            "auto_fixes": 0,
            "healing_attempts": 0,
            "healing_successes": 0
        }

    async def process_query(
        self, query: str, column_names: List[str], sample_data: List[List[Any]] = None, history: List[dict] = None,
        selected_range: str = None, active_cell: str = None
    ) -> dict:
        """
        Главная функция - определяет тип запроса через AI и обрабатывает соответственно

        Args:
            query: Запрос пользователя
            column_names: Названия колонок
            sample_data: Данные таблицы
            history: История предыдущих действий для контекста
            selected_range: Выделенный диапазон (например 'H5:H17')
            active_cell: Активная ячейка (например 'H5')

        Returns:
            dict с типом ответа и данными
        """
        # CRITICAL: column_names передаются отдельно, поэтому sample_data УЖЕ без заголовков!
        # НЕ удаляем первую строку - это реальные данные!
        data_without_headers = sample_data if sample_data else []

        # Используем AI для определения намерения (вместо хардкодных ключевых слов)
        intent_analysis = await self._analyze_intent(query, column_names, data_without_headers, history)

        intent = intent_analysis.get("intent", "ANALYZE_PROBLEM")

        # Действия на основе намерения
        if intent in ["VISUALIZE_DATA", "FORMAT_PRESENTATION", "CREATE_STRUCTURE", "COMPARE_DATA", "FIND_INSIGHTS"]:
            # Все что требует действий (графики, форматирование, структуры) - отправляем в action plan
            return await self.generate_action_plan(query, column_names, data_without_headers, history, selected_range, active_cell)
        elif intent == "CALCULATE":
            # Нужна формула
            return await self.generate_formula(query, column_names, data_without_headers, selected_range, active_cell)
        elif intent in ["QUESTION", "ANALYZE_PROBLEM", "QUERY_DATA"]:
            # Вопросы, анализ проблем и запросы данных требуют текстового ответа
            return await self.analyze_data(query, data_without_headers, column_names)
        else:
            # Текстовый ответ по умолчанию
            return await self.analyze_data(query, data_without_headers, column_names)


    async def generate_formula(
        self, query: str, column_names: List[str], sample_data: List[List[Any]] = None,
        selected_range: str = None, active_cell: str = None
    ) -> dict:
        """Генерирует Google Sheets формулу"""
        start_time = time.time()

        # ШАГ 1: Пробуем найти подходящий template (быстро и надежно)
        from app.services.template_matcher import TemplateMatcher
        matcher = TemplateMatcher()
        template_result = matcher.find_template(query, column_names)

        if template_result:
            # Нашли шаблон - используем его
            template, params = template_result

            try:
                # Подставляем параметры в шаблон
                formula = template.formula_pattern.format(**params)

                # Валидация и автоисправление (ДО локализации)
                formula, validation_issues = self._validate_and_fix_formula(formula, column_names, sample_data)

                # Применяем локализацию (clean_formula делает русификацию)
                formula = self._clean_formula(formula, column_names, sample_data)

                # PHASE 2.4: Calculate confidence for templates
                confidence = self._calculate_confidence("template", validation_issues)

                return {
                    "type": "formula",
                    "formula": formula,
                    "explanation": f"{template.description} (шаблон: {template.name})",
                    "target_cell": active_cell or "A1",
                    "confidence": confidence,
                    "processing_time": time.time() - start_time,
                    "source": "template",  # Помечаем что это из шаблона
                    "validation_log": {
                        "issues_found": len(validation_issues),
                        "auto_fixed": True
                    } if validation_issues else None
                }
            except Exception as e:
                # Если не удалось применить шаблон, fallback на AI
                print(f"Template application failed: {e}, falling back to AI")

        # ШАГ 2: Fallback на AI reasoning (гибкий но медленнее)
        # Анализируем типы данных в колонках
        column_types = self._analyze_column_types(column_names, sample_data)

        # Формируем улучшенный промпт
        prompt = self._build_formula_prompt(query, column_names, sample_data, column_types, selected_range, active_cell)

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

Example GOOD formula: =SORT(FILTER(A2:G;C2:C>500000);3;FALSE)
Example BAD formula: =SORT( FILTER( A2:G; C2:C > 500000 ); 3; FALSE )

NO SPACES IN FORMULAS!"""
                    },
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
                max_tokens=600,
            )

            result = json.loads(response.choices[0].message.content)

            # Валидация и автоисправление AI формулы (ДО локализации)
            if "formula" in result:
                formula, validation_issues = self._validate_and_fix_formula(
                    result["formula"],
                    column_names,
                    sample_data
                )

                # Удаляем пробелы и локализуем
                result["formula"] = self._clean_formula(formula, column_names, sample_data)

                # PHASE 2.4: Calculate confidence score
                confidence = self._calculate_confidence("gpt", validation_issues)
                result["confidence"] = confidence

                # Добавляем информацию о валидации если были проблемы
                if validation_issues:
                    critical_issues = [i for i in validation_issues if i.severity == "critical"]
                    if critical_issues:
                        result["validation_log"] = {
                            "issues_found": len(validation_issues),
                            "critical_issues": len(critical_issues),
                            "auto_fixed": True,
                            "confidence_impact": f"-{100 - int(confidence * 100)}%"
                        }

            result["processing_time"] = time.time() - start_time
            result["type"] = "formula"
            result["source"] = "gpt"  # Mark as GPT-generated

            return result

        except Exception as e:
            return {
                "type": "error",
                "formula": "=ERROR()",
                "explanation": f"Ошибка генерации формулы: {str(e)}",
                "confidence": 0.0,
                "processing_time": time.time() - start_time
            }

    def _clean_formula(self, formula: str, column_names: List[str] = None, sample_data: List[List[Any]] = None) -> str:
        """Удаляет лишние пробелы из формулы.

        ВАЖНО: Google Sheets автоматически переводит английские формулы на язык интерфейса пользователя,
        поэтому мы всегда используем АНГЛИЙСКИЕ названия функций (SUM, AVERAGE, VLOOKUP, IF, etc.)
        """
        # Удаляем пробелы вокруг операторов
        formula = formula.replace(" >", ">").replace("> ", ">")
        formula = formula.replace(" <", "<").replace("< ", "<")
        formula = formula.replace(" =", "=").replace("= ", "=")
        formula = formula.replace(" ,", ",").replace(", ", ",")
        formula = formula.replace(" )", ")").replace("( ", "(")

        # Удаляем множественные пробелы
        while "  " in formula:
            formula = formula.replace("  ", "")

        # NOTE: Локализация УДАЛЕНА - используем только английские формулы
        # Google Sheets сам переведет их на нужный язык
        import re

        # ИСПРАВЛЕНИЕ QUERY СИНТАКСИСА: A/B/C → Col1/Col2/Col3
        # AI часто генерирует неправильный синтаксис QUERY, исправляем автоматически
        if 'QUERY(' in formula.upper():
            import re
            # Паттерн для поиска SELECT запросов внутри кавычек
            pattern = r'"(SELECT[^"]+)"'

            def fix_query_columns(match):
                sql = match.group(1)
                # Заменяем буквенные ссылки на Col1, Col2, etc.
                # Используем regex с word boundaries для замены только изолированных букв
                column_map = {
                    'A': 'Col1', 'B': 'Col2', 'C': 'Col3', 'D': 'Col4',
                    'E': 'Col5', 'F': 'Col6', 'G': 'Col7', 'H': 'Col8',
                    'I': 'Col9', 'J': 'Col10', 'K': 'Col11', 'L': 'Col12',
                    'M': 'Col13', 'N': 'Col14', 'O': 'Col15', 'P': 'Col16',
                }

                # Заменяем каждую букву столбца, но только если она стоит изолированно
                # Паттерн: буква окружена пробелами, запятыми, скобками или началом/концом строки
                for letter, col in column_map.items():
                    # Паттерн: (?<![A-Z]) означает "не после буквы", (?![A-Z]) означает "не перед буквой"
                    # Это гарантирует что мы не заменим B в слове "BY" или "GROUP BY"
                    sql = re.sub(
                        rf'(?<![A-Za-z])({letter})(?![A-Za-z])',
                        col,
                        sql,
                        flags=re.IGNORECASE
                    )

                return f'"{sql}"'

            formula = re.sub(pattern, fix_query_columns, formula, flags=re.IGNORECASE)

        # ИСПРАВЛЕНИЕ VLOOKUP В ARRAYFORMULA: VLOOKUP → INDEX/MATCH
        # VLOOKUP не работает в ARRAYFORMULA, заменяем на INDEX/MATCH автоматически
        if 'ARRAYFORMULA' in formula.upper() and 'VLOOKUP' in formula.upper():
            import re
            # Паттерн для поиска VLOOKUP(lookup_value; table_range; col_index; [FALSE])
            # \s* добавлено для учета пробелов после точек с запятой
            vlookup_pattern = r'VLOOKUP\(([^;]+);\s*([^;]+);\s*(\d+);?\s*([^)]*)\)'

            def replace_vlookup_with_index_match(match):
                lookup_value = match.group(1).strip()
                table_range = match.group(2).strip()
                col_index = int(match.group(3).strip())

                # Разбираем table_range на колонки
                # Например: H:I или $H:$I или H2:I100
                if ':' in table_range:
                    parts = table_range.split(':')
                    first_col = parts[0].strip()
                    last_col = parts[1].strip()

                    # Сохраняем $ если они были
                    has_dollar = '$' in first_col or '$' in last_col
                    dollar_prefix = '$' if has_dollar else ''

                    # Извлекаем буквы колонок (убираем цифры и $)
                    first_col_letter = ''.join([c for c in first_col if c.isalpha()])
                    last_col_letter = ''.join([c for c in last_col if c.isalpha()])

                    # Определяем result_col по col_index
                    # col_index=1 → первая колонка, col_index=2 → вторая колонка
                    if col_index == 1:
                        result_col_letter = first_col_letter
                    elif col_index == 2:
                        result_col_letter = last_col_letter
                    else:
                        # Для col_index > 2 вычисляем нужную колонку
                        first_col_num = ord(first_col_letter.upper()) - ord('A')
                        result_col_num = first_col_num + col_index - 1
                        result_col_letter = chr(ord('A') + result_col_num)

                    # Формируем диапазоны с сохранением абсолютных ссылок
                    search_col = f"{dollar_prefix}{first_col_letter}:{dollar_prefix}{first_col_letter}"
                    result_col = f"{dollar_prefix}{result_col_letter}:{dollar_prefix}{result_col_letter}"

                    return f'INDEX({result_col}; MATCH({lookup_value}; {search_col}; 0))'
                else:
                    # Если table_range не содержит :, оставляем как есть
                    return match.group(0)

            formula = re.sub(vlookup_pattern, replace_vlookup_with_index_match, formula, flags=re.IGNORECASE)

        # ИСПРАВЛЕНИЕ INDEX/MATCH: автоматическое исправление поиска текста в числовых столбцах
        # AI часто генерирует INDEX/MATCH с неправильными ссылками на столбцы
        # Поддерживаем как английские (INDEX/MATCH), так и русские (ИНДЕКС/ПОИСКПОЗ) названия функций
        has_index_match = ('INDEX' in formula.upper() and 'MATCH' in formula.upper()) or \
                          ('ИНДЕКС' in formula and 'ПОИСКПОЗ' in formula)

        if has_index_match and column_names and sample_data:
            import re

            # Анализируем типы данных в столбцах
            column_types = self._analyze_column_types(column_names, sample_data)

            # Паттерны для INDEX/MATCH (английский и русский варианты)
            index_match_pattern_en = r'INDEX\(([^;]+);\s*MATCH\(([^;]+);\s*([^;]+);\s*0\)\)'
            index_match_pattern_ru = r'ИНДЕКС\(([^;(]+);\s*ПОИСКПОЗ\(([^;]+);\s*([^;]+);\s*0\)\)'

            def fix_index_match_columns(match, is_russian=False):
                result_col = match.group(1).strip()
                lookup_value = match.group(2).strip()
                search_col = match.group(3).strip()

                # Извлекаем букву столбца для lookup_value (например, B2:B → B)
                lookup_col_letter = None
                lookup_match = re.search(r'\$?([A-Z]+)\d*:\$?[A-Z]+', lookup_value)
                if lookup_match:
                    lookup_col_letter = lookup_match.group(1)

                # Извлекаем букву столбца для search_col (например, $H:$H → H)
                search_col_letter = None
                search_match = re.search(r'\$?([A-Z]+):\$?\1', search_col)
                if search_match:
                    search_col_letter = search_match.group(1)

                # Извлекаем букву столбца для result_col (например, $I:$I → I)
                result_col_letter = None
                result_match = re.search(r'\$?([A-Z]+):\$?\1', result_col)
                if result_match:
                    result_col_letter = result_match.group(1)

                if not lookup_col_letter or not search_col_letter or not result_col_letter:
                    return match.group(0)  # Не можем разобрать, оставляем как есть

                # Определяем индексы столбцов (A=0, B=1, C=2, ...)
                lookup_col_idx = sum((ord(c) - ord('A') + 1) * (26 ** i) for i, c in enumerate(reversed(lookup_col_letter))) - 1
                search_col_idx = sum((ord(c) - ord('A') + 1) * (26 ** i) for i, c in enumerate(reversed(search_col_letter))) - 1
                result_col_idx = sum((ord(c) - ord('A') + 1) * (26 ** i) for i, c in enumerate(reversed(result_col_letter))) - 1

                # Проверяем валидность индексов (только lookup и search критичны)
                if lookup_col_idx >= len(column_names) or search_col_idx >= len(column_names):
                    return match.group(0)

                # Получаем типы данных
                lookup_col_name = column_names[lookup_col_idx]
                search_col_name = column_names[search_col_idx]

                # result_col может выходить за пределы - это нормально, AI иногда ошибается
                result_col_name = column_names[result_col_idx] if result_col_idx < len(column_names) else None

                lookup_type = column_types.get(lookup_col_name, "unknown")
                search_type = column_types.get(search_col_name, "unknown")
                result_type = column_types.get(result_col_name, "unknown") if result_col_name else "unknown"

                # ПРОВЕРКА ОШИБКИ: Если ищем текст в числовом столбце
                if lookup_type == "text" and search_type in ["number", "number_formatted"]:
                    # Ищем правильный текстовый столбец рядом с search_col
                    # Обычно это предыдущий столбец (например, H числа → G текст)
                    correct_search_idx = None

                    # Сначала проверяем столбец слева от search_col
                    if search_col_idx > 0:
                        neighbor_col_name = column_names[search_col_idx - 1]
                        neighbor_type = column_types.get(neighbor_col_name, "unknown")
                        if neighbor_type == "text" and neighbor_col_name:  # не пустой столбец
                            correct_search_idx = search_col_idx - 1

                    # Если не нашли слева, ищем справа
                    if correct_search_idx is None and search_col_idx + 1 < len(column_names):
                        neighbor_col_name = column_names[search_col_idx + 1]
                        neighbor_type = column_types.get(neighbor_col_name, "unknown")
                        if neighbor_type == "text" and neighbor_col_name:
                            correct_search_idx = search_col_idx + 1

                    # Если нашли правильный столбец, заменяем ссылки
                    if correct_search_idx is not None:
                        # Определяем букву для нового search_col
                        correct_search_letter = chr(ord('A') + correct_search_idx)

                        # Определяем букву для нового result_col (должен быть числовой столбец)
                        # Обычно это исходный search_col (который был числовым)
                        correct_result_letter = search_col_letter

                        # Сохраняем $ если они были
                        has_dollar = '$' in search_col
                        dollar_prefix = '$' if has_dollar else ''

                        # Формируем новые ссылки
                        new_search_col = f"{dollar_prefix}{correct_search_letter}:{dollar_prefix}{correct_search_letter}"
                        new_result_col = f"{dollar_prefix}{correct_result_letter}:{dollar_prefix}{correct_result_letter}"

                        # Возвращаем формулу на нужном языке
                        if is_russian:
                            return f'ИНДЕКС({new_result_col}; ПОИСКПОЗ({lookup_value}; {new_search_col}; 0))'
                        else:
                            return f'INDEX({new_result_col}; MATCH({lookup_value}; {new_search_col}; 0))'

                # Если ошибки не обнаружено, возвращаем как есть
                return match.group(0)

            # Определяем язык формулы и применяем соответствующий паттерн
            is_russian = 'ИНДЕКС' in formula and 'ПОИСКПОЗ' in formula

            if is_russian:
                # Применяем русский паттерн
                formula = re.sub(index_match_pattern_ru, lambda m: fix_index_match_columns(m, is_russian=True), formula)
            else:
                # Применяем английский паттерн
                formula = re.sub(index_match_pattern_en, lambda m: fix_index_match_columns(m, is_russian=False), formula, flags=re.IGNORECASE)

        # ЗАМЕНА INDEX/MATCH на VLOOKUP внутри ARRAYFORMULA
        # INDEX/MATCH не работает с массивами в ARRAYFORMULA, нужно использовать VLOOKUP
        is_in_arrayformula = 'ARRAYFORMULA' in formula.upper() or 'ФОРМУЛАМАССИВА' in formula
        has_index_match_after = ('INDEX' in formula.upper() and 'MATCH' in formula.upper()) or \
                                ('ИНДЕКС' in formula and 'ПОИСКПОЗ' in formula)

        if is_in_arrayformula and has_index_match_after and column_names:
            # Паттерны для поиска INDEX/MATCH с массивами
            # Ищем паттерн: INDEX($H:$H; MATCH(B2:B; $G:$G; 0)) или INDEX($H$2:$H; MATCH(B2:B; $G$2:$G; 0))
            # Поддерживаем диапазоны: $H:$H, $H$2:$H, $H$2:$H$999
            index_match_array_pattern_en = r'INDEX\((\$?[A-Z]+(?:\$\d+)?:\$?[A-Z]+(?:\$\d+)?);\s*MATCH\(([A-Z]+\d+:[A-Z]+);\s*(\$?[A-Z]+(?:\$\d+)?:\$?[A-Z]+(?:\$\d+)?);\s*0\)\)'
            index_match_array_pattern_ru = r'ИНДЕКС\((\$?[A-Z]+(?:\$\d+)?:\$?[A-Z]+(?:\$\d+)?);\s*ПОИСКПОЗ\(([A-Z]+\d+:[A-Z]+);\s*(\$?[A-Z]+(?:\$\d+)?:\$?[A-Z]+(?:\$\d+)?);\s*0\)\)'

            def replace_with_vlookup(match, is_russian=False):
                result_col_ref = match.group(1).strip()  # $H:$H
                lookup_array = match.group(2).strip()     # B2:B
                search_col_ref = match.group(3).strip()   # $G:$G

                # Извлекаем буквы столбцов
                result_col_letter = re.search(r'([A-Z]+)', result_col_ref).group(1)
                search_col_letter = re.search(r'([A-Z]+)', search_col_ref).group(1)

                # Вычисляем индексы столбцов
                result_col_idx = sum((ord(c) - ord('A') + 1) * (26 ** i) for i, c in enumerate(reversed(result_col_letter))) - 1
                search_col_idx = sum((ord(c) - ord('A') + 1) * (26 ** i) for i, c in enumerate(reversed(search_col_letter))) - 1

                # Индекс столбца для VLOOKUP (относительно начала таблицы)
                vlookup_col_index = result_col_idx - search_col_idx + 1

                # Формируем диапазон для VLOOKUP: $G$2:$H
                has_dollar = '$' in search_col_ref
                dollar_prefix = '$' if has_dollar else ''
                table_range = f"{dollar_prefix}{search_col_letter}{dollar_prefix}2:{dollar_prefix}{result_col_letter}"

                # Возвращаем VLOOKUP на нужном языке
                if is_russian:
                    return f'ВПР({lookup_array}; {table_range}; {vlookup_col_index}; ЛОЖЬ)'
                else:
                    return f'VLOOKUP({lookup_array}; {table_range}; {vlookup_col_index}; FALSE)'

            # Применяем замену
            is_russian_after = 'ИНДЕКС' in formula and 'ПОИСКПОЗ' in formula

            if is_russian_after:
                formula = re.sub(index_match_array_pattern_ru, lambda m: replace_with_vlookup(m, is_russian=True), formula)
            else:
                formula = re.sub(index_match_array_pattern_en, lambda m: replace_with_vlookup(m, is_russian=False), formula, flags=re.IGNORECASE)

        return formula

    def _validate_and_fix_formula(
        self,
        formula: str,
        column_names: List[str] = None,
        sample_data: List[List[Any]] = None
    ) -> tuple[str, list]:
        """
        Валидирует формулу и автоматически исправляет типичные ошибки

        Returns:
            (fixed_formula, issues) - исправленная формула и список найденных проблем
        """
        # PHASE 2.2: Добавляем column_count в context для column reference validation
        context = {
            "row_count": len(sample_data) if sample_data else 100,
            "column_names": column_names or [],
            "column_count": len(column_names) if column_names else 0
        }

        # Шаг 1: Валидация
        issues = self.validator.validate(formula, context)

        if not issues:
            return formula, []

        # Шаг 2: Автоматическое исправление
        fixable_issues = [i for i in issues if i.auto_fixable]

        if fixable_issues:
            fixed_formula = self.fixer.fix(formula, fixable_issues, context)
            return fixed_formula, issues

        # Если нет auto-fixable проблем, возвращаем оригинал
        return formula, issues

    def _calculate_confidence(
        self,
        source: str,
        validation_issues: list
    ) -> float:
        """
        PHASE 2.4: Расчет confidence score (0.0 - 1.0)

        Args:
            source: "template" или "gpt"
            validation_issues: список ValidationIssue

        Returns:
            Confidence score от 0.0 до 1.0

        Формула:
        - Template baseline: 0.95
        - GPT baseline: 0.70
        - Каждая issue уменьшает score:
          - critical (не авто-фиксится): -0.20
          - critical (авто-фикс): -0.10
          - high: -0.08
          - medium: -0.05
          - low: -0.02
        """
        # Базовый score зависит от источника
        if source == "template":
            base_score = 0.95
        elif source == "gpt":
            base_score = 0.70
        else:
            base_score = 0.50

        if not validation_issues:
            return base_score

        # Считаем штраф за каждую issue
        penalty = 0.0

        severity_penalties = {
            "critical": 0.20,  # Критичная ошибка
            "high": 0.08,       # Высокая важность
            "medium": 0.05,     # Средняя важность
            "low": 0.02         # Низкая важность
        }

        for issue in validation_issues:
            severity_penalty = severity_penalties.get(issue.severity, 0.05)

            # Если issue авто-фиксится, штраф меньше
            if issue.auto_fixable:
                severity_penalty *= 0.5

            penalty += severity_penalty

        # Финальный score (не меньше 0.1)
        final_score = max(0.1, base_score - penalty)

        return round(final_score, 2)

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
        self, query: str, column_names: List[str], sample_data: List[List[Any]], column_types: Dict,
        selected_range: str = None, active_cell: str = None
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

        # Добавляем информацию о выделенном диапазоне
        selection_info = ""
        if selected_range:
            selection_info = f"\n⚠️ ВАЖНО: Пользователь выделил диапазон {selected_range}. Формула должна начинаться с ячейки {selected_range.split(':')[0]}!"
        elif active_cell:
            selection_info = f"\nАктивная ячейка: {active_cell}"

        prompt = f"""Generate a Google Sheets formula for this request.

TABLE STRUCTURE:
Columns: {len(column_names)}
{chr(10).join(columns_info)}

SAMPLE DATA (without headers):
{chr(10).join(sample_rows) if sample_rows else "No data"}{selection_info}

USER REQUEST (Russian): {query}

# GOOGLE SHEETS QUICK REFERENCE

## Aggregation (Агрегация):
- SUM(A2:A) - сумма
- AVERAGE(A2:A) - среднее
- COUNT(A2:A) - количество чисел
- MAX(A2:A), MIN(A2:A) - макс/мин

## Conditional (Условные):
- SUMIF($A$2:$A,"Яблоко",$B$2:$B) - сумма по условию (используй $ для диапазонов!)
- SUMIFS($C$2:$C,$A$2:$A,"Яблоко",$B$2:$B,">100") - сумма по нескольким условиям
- COUNTIF($A$2:$A,"Яблоко") - подсчет по условию
- AVERAGEIF($A$2:$A,"Яблоко",$B$2:$B) - среднее по условию
- IF(A2>100,"Да","Нет") - условие
⚠️ В ARRAYFORMULA с SUMIF/COUNTIF: всегда используй $ для диапазонов поиска/суммирования!

## Arrays (Массивы - MODERN!):
- UNIQUE(A2:A) - уникальные значения
- FILTER(A2:B,B2:B>1000) - фильтрация
- SORT(A2:B,2,FALSE) - сортировка (колонка 2, по убыванию)
- QUERY(A2:C,"SELECT Col1, SUM(Col2) GROUP BY Col1",0) - SQL-запросы
  ⚠️ КРИТИЧЕСКИ ВАЖНО для QUERY: используй Col1, Col2, Col3 (НЕ A, B, C!)
  Диапазон ДОЛЖЕН включать ВСЕ нужные столбцы!

## Lookup (Поиск) - КРИТИЧЕСКИ ВАЖНО!:
⚠️ В ARRAYFORMULA ВСЕГДА используй INDEX/MATCH, НЕ VLOOKUP!

🔍 КАК ОПРЕДЕЛИТЬ LOOKUP ТАБЛИЦУ:
Если пользователь говорит "из второй таблицы", "из справочника", "из таблицы окладов/цен" -
это означает LOOKUP таблицу (обычно справа от основных данных, разделенная пустыми столбцами).

📋 СТРУКТУРА LOOKUP ТАБЛИЦЫ:
Lookup таблица ВСЕГДА состоит из двух столбцов (могут быть не рядом):
1. Search column (ключ) - столбец с ТЕКСТОВЫМИ значениями для поиска
2. Result column (значение) - столбец с данными которые нужно вернуть

📝 ПРИМЕРЫ:
Правильно:
- Lookup table G:H → search in G, return from H
  =INDEX($H:$H,MATCH(B2,$G:$G,0))

- Lookup table D:E → search in D, return from E
  =INDEX($E:$E,MATCH(A2,$D:$D,0))

- В ARRAYFORMULA с условием:
  =ARRAYFORMULA(IF(B2:B="","",IF(C2:C<5,INDEX($H:$H,MATCH(B2:B,$G:$G,0)),INDEX($H:$H,MATCH(B2:B,$G:$G,0))*1.05)))

Неправильно:
❌ =INDEX($H:$H,MATCH(B2:B,$H:$H,0)) - нельзя искать в столбце с числами (H)!
❌ VLOOKUP в ARRAYFORMULA - не работает!

🎯 ПРАВИЛО INDEX/MATCH:
INDEX(result_column, MATCH(lookup_value, search_column, 0))
      ↑возвращаем          ↑ищем           ↑где искать

search_column = столбец с НАЗВАНИЯМИ/КЛЮЧАМИ (текст)
result_column = столбец с ДАННЫМИ для возврата (числа/текст)

🔴 КРИТИЧЕСКОЕ ПРАВИЛО ОПРЕДЕЛЕНИЯ СТОЛБЦОВ:
1. Смотри на lookup_value (что ищем) - это обычно ТЕКСТ из левой части таблицы
2. Найди в СПРАВОЧНОЙ ТАБЛИЦЕ столбец с ТЕМ ЖЕ ТИПОМ ДАННЫХ (text → text)
3. Этот столбец = search_column (где искать)
4. Следующий столбец справа = result_column (что возвращать)

ПРИМЕР АНАЛИЗА:
Дано: column_names = ["Должность" (text), "Стаж" (number), "Оклад" (empty), ..., "Должность (справочник)" (text), "Базовый оклад" (number)]
                        ↑A                ↑B               ↑C                      ↑G                           ↑H

Задача: "вписать оклад по должности"
1. lookup_value = B2:B (Должность) - это ТЕКСТ
2. Справочная таблица: G:H
3. G = "Должность (справочник)" (text) - совпадает с lookup_value по типу! → search_column = $G:$G
4. H = "Базовый оклад" (number) - следующий столбец → result_column = $H:$H
5. Формула: INDEX($H:$H, MATCH(B2:B, $G:$G, 0))

❌ НЕПРАВИЛЬНО: INDEX($H:$H, MATCH(B2:B, $H:$H, 0)) - ищет текст "Должность" в числах!
✅ ПРАВИЛЬНО: INDEX($H:$H, MATCH(B2:B, $G:$G, 0)) - ищет текст "Должность" в текстах!

🚨 ЧАСТЫЕ ОШИБКИ - НЕ ПОВТОРЯЙ ЭТИ ОШИБКИ!!!

ОШИБКА #1: Поиск текста в столбце с числами
❌ ПЛОХО: INDEX(I:I; MATCH(B2:B; H:H; 0))
   где B2:B содержит "Аналитика" (текст), а H:H содержит 55000 (число)
   РЕЗУЛЬТАТ: #ERROR! потому что MATCH ищет "Аналитика" в числах!

✅ ХОРОШО: INDEX(H:H; MATCH(B2:B; G:G; 0))
   где B2:B содержит "Аналитика" (текст), G:G содержит "Аналитика" (текст), H:H содержит 55000 (число)
   РЕЗУЛЬТАТ: 55000 (работает!)

ОШИБКА #2: Путаница между search_column и result_column
Формула INDEX/MATCH работает так:
INDEX(откуда_взять_результат; MATCH(что_ищем; где_искать; 0))

❌ ПЛОХО: INDEX(G:G; MATCH(B2:B; H:H; 0)) - возвращает текст вместо чисел!
✅ ХОРОШО: INDEX(H:H; MATCH(B2:B; G:G; 0)) - возвращает числа из H, ищет в G

ОШИБКА #3: Неправильное определение lookup таблицы
Если видишь column_names = ["Отдел", "Стаж", "Оклад", "", "", "Отделы", "Базовый оклад"]
                              ↑A       ↑B      ↑C     ↑D  ↑E   ↑G          ↑H
Пустые колонки D,E разделяют основную таблицу от справочника!
Справочник = G:H (G=текст "Отделы", H=число "Базовый оклад")

❌ ПЛОХО: искать в H:H (числа), возвращать из I:I
✅ ХОРОШО: искать в G:G (текст), возвращать из H:H (числа)

АЛГОРИТМ ПРОВЕРКИ перед генерацией формулы:
1. lookup_value (что ищем) = B2:B → смотрю на sample_data → это ТЕКСТ ("Аналитика", "HR")
2. Ищу в column_names справочную таблицу (после пустых колонок "")
3. Первый столбец справочника с ТЕКСТОМ = search_column для MATCH
4. Следующий столбец = result_column для INDEX
5. Проверка: lookup_value (текст) должен искаться в столбце с ТЕКСТОМ, не с ЧИСЛАМИ!

## Text (Текст):
- A2&" "&B2 - объединение
- LEFT(A2,5), RIGHT(A2,5) - первые/последние символы
- UPPER(A2), LOWER(A2) - регистр

## Dates (Даты):
- TODAY() - сегодня
- YEAR(A2), MONTH(A2), DAY(A2) - части даты

## Common Patterns (Частые паттерны):
"сводная таблица" → UNIQUE(A2:A) + SUMIF($A$2:$A,E2,$B$2:$B)
"топ 10" → SORT(A2:B,2,FALSE)
"средний чек" → AVERAGE(B2:B) или SUM()/COUNT()
"динамика" → формулы с разницей =(B3-B2)/B2*100
"процент от общего" → B2/SUM($B$2:$B)*100

🔴 КРИТИЧЕСКИ ВАЖНО - СУММИРОВАНИЕ ПРОИЗВЕДЕНИЙ:
⚠️ SUMIF НЕ поддерживает умножение диапазонов!

❌ НЕПРАВИЛЬНО:
=SUMIF($B$2:$B,"Критерий",$C$2:$C*$D$2:$D)  // ОШИБКА! SUMIF не умножает диапазоны

✅ ПРАВИЛЬНО - используй SUMPRODUCT:
=SUMPRODUCT(($B$2:$B="Критерий")*($C$2:$C*$D$2:$D))

Примеры использования SUMPRODUCT:
- "сумма продаж по поставщику" (цена × объем) → =SUMPRODUCT(($B$2:$B="Поставщик1")*($C$2:$C*$D$2:$D))
- "общая выручка где регион=Москва" → =SUMPRODUCT(($A$2:$A="Москва")*($B$2:$B*$C$2:$C))
- "итого с НДС для категории X" → =SUMPRODUCT(($B$2:$B="Категория X")*($C$2:$C*1.2))

Правило: Если нужно суммировать ПРОИЗВЕДЕНИЕ колонок с условием → SUMPRODUCT, НЕ SUMIF!

🔍 ЧАСТИЧНЫЙ ПОИСК ПО ПОДСТРОКЕ (для SUMPRODUCT с текстовыми условиями):
Если пользователь указывает ЧАСТЬ названия (например "Радость" вместо "ООО Радость"):
❌ НЕПРАВИЛЬНО (точное совпадение): =SUMPRODUCT(($B$2:$B="Радость")*($C$2:$C*$D$2:$D))
✅ ПРАВИЛЬНО (поиск подстроки): =SUMPRODUCT(ISNUMBER(SEARCH("Радость";$B$2:$B))*($C$2:$C*$D$2:$D))

SEARCH ищет подстроку в тексте (без учета регистра).
Примеры с точкой с запятой:
- "сумма продаж Радость" → =SUMPRODUCT(ISNUMBER(SEARCH("Радость";$B$2:$B))*($C$2:$C*$D$2:$D))
- "выручка по Москва" → =SUMPRODUCT(ISNUMBER(SEARCH("Москва";$A$2:$A))*($B$2:$B*$C$2:$C))

IMPORTANT REQUIREMENTS:
1. 🔴 КРИТИЧЕСКИ ВАЖНО: Используй ТОЧКУ С ЗАПЯТОЙ (;) как разделитель аргументов в формулах!
   ❌ НЕПРАВИЛЬНО: =SUMPRODUCT(A2:A,B2:B) или =IFERROR(A2,"")
   ✅ ПРАВИЛЬНО: =SUMPRODUCT(A2:A;B2:B) или =IFERROR(A2;"")
2. NO SPACES in formula - must be compact like =SORT(FILTER(A2:G;C2:C>500000);3;FALSE)
3. Use correct column letters (A, B, C, etc.)
4. Data starts from row 2 (row 1 is headers)
5. Use open ranges (A2:A, not A2:A100) when referencing entire column
6. Use $ for absolute references when needed ($A$2:$A)
7. Respond in Russian but formula in English

Response format (JSON):
{{
  "formula": "=SORT(FILTER(A2:G;C2:C>500000);3;FALSE)",
  "explanation": "Подробное объяснение на русском что делает формула",
  "target_cell": "I2",
  "confidence": 0.95
}}

If request is unclear, set confidence < 0.6 and explain what's missing."""

        return prompt

    def _detect_aggregation_need(self, query: str) -> Optional[Dict[str, str]]:
        """
        Определяет нужна ли Python-агрегация по ключевым словам в запросе

        Returns:
            Dict с типом агрегации и параметрами, или None если агрегация не нужна
        """
        query_lower = query.lower()

        # Паттерны для определения агрегации
        aggregation_patterns = [
            (r'(какой|который|кто|что)\s+\S+\s+(продал|продаж|выручк|сумм|количеств).*(больше всего|меньше всего|максимум|минимум)', 'group_sum'),
            (r'(у\s+кого|где)\s+(больше всего|меньше всего|максимум|минимум)', 'group_sum'),
            (r'топ\s+\d+\s+\S+\s+по\s+(продаж|сумм|выручк|количеств)', 'group_sum_top'),
            (r'(сколько|количество)\s+\S+\s+(у|от|по)\s+\S+', 'group_count'),
            (r'средн.+\s+(продаж|сумм|выручк)\s+(у|от|по)\s+\S+', 'group_avg'),
        ]

        for pattern, agg_type in aggregation_patterns:
            if re.search(pattern, query_lower):
                return {'type': agg_type, 'query': query}

        return None

    def _perform_python_aggregation(
        self,
        query: str,
        sample_data: List[List[Any]],
        column_names: List[str],
        agg_config: Dict[str, str]
    ) -> Optional[Dict]:
        """
        Выполняет реальную Python-агрегацию данных с pandas

        Args:
            query: Запрос пользователя
            sample_data: Данные таблицы
            column_names: Названия колонок
            agg_config: Конфигурация агрегации из _detect_aggregation_need

        Returns:
            Dict с результатами агрегации или None если не удалось
        """
        try:
            # Создаём DataFrame
            df = pd.DataFrame(sample_data, columns=column_names)

            print(f"\n🔢 Python aggregation started:")
            print(f"Query: {query}")
            print(f"Agg type: {agg_config['type']}")
            print(f"DataFrame shape: {df.shape}")
            print(f"Columns: {column_names}")

            # Определяем по каким колонкам группировать и агрегировать
            # КРИТИЧЕСКИ ВАЖНО: анализируем ЗАПРОС, а не просто берём первую колонку!
            group_column = None
            value_column = None
            query_lower = query.lower()

            print(f"\n🔍 COLUMN DETECTION DEBUG:")
            print(f"📝 Query (lowercase): '{query_lower}'")
            print(f"📊 Available columns: {column_names}")

            # Определяем колонку для группировки - ищем упоминание в ЗАПРОСЕ
            group_keywords = {
                'поставщик': ['поставщик'],
                'товар': ['товар', 'продукт'],
                'менеджер': ['менеджер', 'продавец'],
                'регион': ['регион', 'город', 'область'],
                'категор': ['категор'],
                'клиент': ['клиент', 'покупател']
            }

            # Находим какое ключевое слово упомянуто в запросе
            for keyword_group, synonyms in group_keywords.items():
                query_has_keyword = any(syn in query_lower for syn in synonyms)
                if query_has_keyword:
                    print(f"🔑 Found keyword '{keyword_group}' in query (synonyms: {synonyms})")
                    # Ищем колонку с этим ключевым словом
                    for col in column_names:
                        col_lower = col.lower()
                        col_has_keyword = any(syn in col_lower for syn in synonyms)
                        print(f"  Checking column '{col}': keyword match = {col_has_keyword}, has 'справочник' = {'справочник' in col_lower}")
                        if col_has_keyword and 'справочник' not in col_lower:
                            group_column = col
                            print(f"✅ SELECTED group column: '{col}' (matched keyword '{keyword_group}')")
                            break
                    if group_column:
                        break

            # Если не нашли по запросу - берём первую подходящую
            if not group_column:
                all_group_keywords = ['поставщик', 'товар', 'продукт', 'менеджер', 'регион', 'категор', 'клиент']
                for col in column_names:
                    col_lower = col.lower()
                    if any(keyword in col_lower for keyword in all_group_keywords):
                        if 'справочник' not in col_lower:
                            group_column = col
                            print(f"⚠️  Group column by fallback: '{col}'")
                            break

            # Определяем колонку для агрегации - приоритет "продажам" если упомянуты
            print(f"\n🔢 VALUE COLUMN DETECTION:")
            value_priority_keywords = [
                (['продаж', 'продал'], ['продаж']),
                (['сумм', 'выручк'], ['сумм', 'выручк']),
                (['количеств', 'объем'], ['количеств', 'объем']),
            ]

            # Ищем по запросу
            for query_keywords, column_keywords in value_priority_keywords:
                query_has_value_keyword = any(kw in query_lower for kw in query_keywords)
                if query_has_value_keyword:
                    print(f"🔑 Found value keyword in query: {[kw for kw in query_keywords if kw in query_lower]}")
                    for col in column_names:
                        col_lower = col.lower()
                        col_has_keyword = any(kw in col_lower for kw in column_keywords)
                        print(f"  Checking column '{col}': keyword match = {col_has_keyword}")
                        if col_has_keyword:
                            try:
                                df[col] = pd.to_numeric(df[col], errors='coerce')
                                has_values = df[col].notna().any()
                                print(f"  '{col}' is numeric: {has_values}")
                                if has_values:
                                    value_column = col
                                    print(f"✅ SELECTED value column: '{col}' (matched keywords {column_keywords})")
                                    break
                            except Exception as e:
                                print(f"  '{col}' conversion error: {e}")
                                continue
                    if value_column:
                        break

            # Если не нашли по запросу - берём первую числовую подходящую
            if not value_column:
                for col in column_names:
                    col_lower = col.lower()
                    if any(kw in col_lower for kw in ['продаж', 'сумм', 'выручк', 'количеств', 'объем']):
                        try:
                            df[col] = pd.to_numeric(df[col], errors='coerce')
                            if df[col].notna().any():
                                value_column = col
                                print(f"⚠️  Value column by fallback: '{col}'")
                                break
                        except:
                            continue

            if not group_column or not value_column:
                print(f"⚠️  Could not detect columns: group={group_column}, value={value_column}")
                return None

            print(f"✅ Detected: group_by='{group_column}', aggregate='{value_column}'")
            print(f"\n📋 DataFrame before aggregation (first 5 rows):")
            print(df[[group_column, value_column]].head())

            # Выполняем агрегацию
            if agg_config['type'] in ['group_sum', 'group_sum_top']:
                # GROUP BY + SUM
                print(f"\n🔄 Executing: df.groupby('{group_column}')['{value_column}'].sum()")
                result_df = df.groupby(group_column, as_index=False)[value_column].sum()
                result_df = result_df.sort_values(value_column, ascending=False)
                print(f"✅ Aggregation complete. Top result: {result_df.iloc[0][group_column]} = {result_df.iloc[0][value_column]}")

                # Для топ-N берём только нужное количество
                if agg_config['type'] == 'group_sum_top':
                    top_match = re.search(r'топ\s+(\d+)', query.lower())
                    if top_match:
                        top_n = int(top_match.group(1))
                        result_df = result_df.head(top_n)

                print(f"📊 Aggregation result:\n{result_df}")

                # Формируем ответ
                top_entity = result_df.iloc[0]
                summary = f"{top_entity[group_column]} продал больше всего: {top_entity[value_column]:,.2f}"

                key_findings = []
                for idx, row in result_df.head(5).iterrows():
                    key_findings.append(
                        f"{idx+1}️⃣ {row[group_column]}: {row[value_column]:,.2f}"
                    )

                return {
                    'summary': summary,
                    'methodology': f"🔍 Как посчитано: сгруппировал данные по колонке '{group_column}', просуммировал все значения в колонке '{value_column}' для каждой группы, отсортировал по убыванию",
                    'key_findings': key_findings,
                    'explanation': f"Проанализировал {len(df)} строк данных. Для каждого значения в '{group_column}' просуммировал все продажи.",
                    'confidence': 0.98,
                    'source': 'python_aggregation'
                }

            elif agg_config['type'] == 'group_count':
                # GROUP BY + COUNT
                result_df = df.groupby(group_column, as_index=False)[value_column].count()
                result_df = result_df.sort_values(value_column, ascending=False)

                top_entity = result_df.iloc[0]
                summary = f"{top_entity[group_column]}: {top_entity[value_column]} записей"

                return {
                    'summary': summary,
                    'methodology': f"🔍 Как посчитано: подсчитал количество записей для каждого '{group_column}'",
                    'key_findings': [f"{row[group_column]}: {row[value_column]} шт" for _, row in result_df.head(5).iterrows()],
                    'explanation': f"Подсчитано количество строк для каждого значения '{group_column}'",
                    'confidence': 0.98,
                    'source': 'python_aggregation'
                }

            elif agg_config['type'] == 'group_avg':
                # GROUP BY + AVG
                result_df = df.groupby(group_column, as_index=False)[value_column].mean()
                result_df = result_df.sort_values(value_column, ascending=False)

                top_entity = result_df.iloc[0]
                summary = f"{top_entity[group_column]}: среднее {top_entity[value_column]:,.2f}"

                return {
                    'summary': summary,
                    'methodology': f"🔍 Как посчитано: вычислил среднее значение '{value_column}' для каждого '{group_column}'",
                    'key_findings': [f"{row[group_column]}: {row[value_column]:,.2f} (среднее)" for _, row in result_df.head(5).iterrows()],
                    'explanation': f"Посчитано среднее арифметическое для каждого '{group_column}'",
                    'confidence': 0.98,
                    'source': 'python_aggregation'
                }

            return None

        except Exception as e:
            print(f"❌ Python aggregation error: {e}")
            import traceback
            traceback.print_exc()
            return None

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

        # DEBUG: Log input data
        print(f"\n🔍 DEBUG analyze_data:")
        print(f"Query: {query}")
        print(f"Columns: {column_names}")
        print(f"Sample data (first 5): {sample_rows[:5]}")

        # CRITICAL: Check if Python aggregation is needed
        agg_config = self._detect_aggregation_need(query)
        if agg_config and sample_data:
            print(f"🔢 Python aggregation detected: {agg_config['type']}")
            python_result = self._perform_python_aggregation(query, sample_data, column_names, agg_config)
            if python_result:
                print(f"✅ Python aggregation successful!")
                python_result["processing_time"] = time.time() - start_time
                python_result["type"] = "analysis"
                return python_result
            else:
                print(f"⚠️  Python aggregation failed, falling back to GPT")

        prompt = f"""Analyze this Google Sheets data.

📋 TABLE:
Columns: {', '.join(column_names)}

Data (first 10 rows):
{json.dumps(sample_rows, ensure_ascii=False)}

❓ USER QUESTION: {query}

🔴 CRITICAL: You MUST return ALL fields below. NO optional fields!

📤 REQUIRED JSON FORMAT:
{{
  "summary": "Краткий ответ в 1 предложении (50-80 символов)",
  "methodology": "🔍 Как посчитано: [ОБЯЗАТЕЛЬНО укажи названия колонок и метод расчета - сортировка/сумма/среднее/подсчет]",
  "key_findings": [
    "Находка 1 с цифрами",
    "Находка 2 с цифрами"
  ],
  "explanation": "Детальное объяснение результата",
  "confidence": 0.9
}}

🎯 METHODOLOGY EXAMPLES:
- "🔍 Как посчитано: отсортировал колонку 'Продажи' (B) по убыванию, выбрал топ-3"
- "🔍 Как посчитано: просуммировал значения в колонке 'Сумма' (C), где колонка 'Регион' (A) = 'Москва'"
- "🔍 Как посчитано: подсчитал количество строк где колонка 'Статус' (D) = 'Активный'"

🔴 METHODOLOGY RULES:
1. ВСЕГДА начинай с "🔍 Как посчитано:"
2. ОБЯЗАТЕЛЬНО укажи ИМЯ колонки в кавычках (не букву!)
3. УКАЖИ метод: сортировка/сумма/среднее/подсчет/фильтр
4. Длина: 80-120 символов

RULES:
1. summary - КРАТКИЙ главный вывод (1-2 предложения, макс 100 символов)
2. methodology - 🔍 КАК ты это посчитал: какие колонки использовал, какие расчеты делал, по каким критериям (100-150 символов)
   - ОБЯЗАТЕЛЬНО начинай с "🔍 Как я это посчитал:"
   - УКАЖИ конкретные названия колонок
   - УКАЖИ метод расчета (сумма, среднее, сортировка, сравнение и т.д.)
3. key_findings - КОНКРЕТНЫЕ находки с цифрами (3-5 пунктов по 50-80 символов)
4. insights - Короткие инсайты с эмодзи 💡 (2-4 пункта по 50-80 символов)
5. suggested_actions - Конкретные действия с эмодзи ✅ (2-3 пункта по 50-80 символов)

DETERMINISTIC SORTING (CRITICAL FOR "ТОП N" QUERIES):
- ALWAYS sort by value DESCENDING (highest first)
- If values are equal, sort alphabetically by name ASCENDING (A to Z)
- NEVER randomize or vary results between calls
- Example: For "топ 3 товара по продажам" with sales [800, 800, 600]:
  * If "Товар A" and "Товар B" both have 800 sales → sort alphabetically: "Товар A" comes first
  * Result MUST be consistent: [Товар A (800), Товар B (800), Товар C (600)]

EXAMPLES:

Good summary: "Продажи упали на 40% за год. Критическое падение в Q4."
Bad summary: "Анализируя данные продаж за год, можно заметить что произошло значительное снижение показателей..."

Good methodology: "🔍 Как я это посчитал: проанализировал колонку 'Продажи', суммировал значения по каждому месяцу, вычислил процентное изменение между Q1 и Q4"
Bad methodology: "Я проанализировал данные и посчитал результаты"

Good key_finding: "Октябрь-декабрь: падение с 150к до 90к (-40%)"
Bad key_finding: "В период с октября по декабрь наблюдается снижение продаж..."

Good insight: "💡 Худшие результаты за весь год в декабре"
Bad insight: "Можно заметить что декабрь показал самые низкие результаты..."

Good action: "✅ Срочно проверить работу отдела продаж в Q4"
Bad action: "Рекомендуется обратить внимание на работу сотрудников..."

🔴🔴🔴 CRITICAL: AGGREGATION AND GROUPING 🔴🔴🔴

When query asks "какой [ENTITY] [больше всего/меньше всего] [METRIC]":
- ENTITY = category to group by (поставщик, товар, регион, менеджер, etc.)
- METRIC = value to aggregate (продажи, количество, сумма, etc.)

YOU MUST:
1. **GROUP BY** ENTITY column
2. **SUM/COUNT/AVG** METRIC column for each group
3. **FIND** which ENTITY has max/min total

❌ WRONG APPROACH (just sorting):
Query: "какой поставщик продал больше всего?"
Wrong: Sort 'Продажи' column → find max value → return supplier from that ONE row
Problem: Ignores that supplier may have MULTIPLE sales!

✅ CORRECT APPROACH (group + aggregate):
Query: "какой поставщик продал больше всего?"
Step 1: GROUP BY 'Поставщик' column
Step 2: SUM 'Продажи' for each supplier (sum ALL rows for each supplier!)
Step 3: Find supplier with maximum total
Example:
- ООО "Время": row 4 (44297.96) + row 7 (145550.44) + row 16 (88595.92) = 278444.32
- ООО "Радость": row 10 (378191.85) = 378191.85
Result: ООО "Радость" has maximum total

Methodology: "🔍 Как посчитано: сгруппировал данные по колонке 'Поставщик', просуммировал все продажи для каждого поставщика, выбрал максимум"

🔴 AGGREGATION KEYWORDS:
- "какой/который [X] больше всего/меньше всего" → GROUP BY X, SUM metric
- "у кого/где больше всего" → GROUP BY, SUM/COUNT
- "топ 3 [X] по [metric]" → GROUP BY X, SUM metric, sort, take top 3

CRITICAL FOR METHODOLOGY:
- If query asks "топ 3 товара" → explain: which column was used for products, which for sorting, how top 3 was selected
- If query asks "у какого поставщика больше всего товаров" → explain: which column for suppliers, which for products, how count was calculated
- If query asks "как ты это посчитал" → provide DETAILED explanation of previous calculation

🔴 EXAMPLE FOR "ТОП 3 ТОВАРА ПО ПРОДАЖАМ":
Input:
Columns: Товар, Продажи, Количество
Data: [["Товар A", 800, 50], ["Товар B", 800, 45], ["Товар C", 600, 30], ["Товар D", 400, 20]]

CORRECT RESPONSE:
{{
  "summary": "Лидируют Товар A и Товар B с 800 продажами каждый",
  "methodology": "🔍 Как посчитано: отсортировал колонку 'Продажи' по убыванию, при равных значениях - по алфавиту, выбрал топ-3",
  "key_findings": [
    "1️⃣ Товар A: 800 продаж (топ-1)",
    "2️⃣ Товар B: 800 продаж (топ-2)",
    "3️⃣ Товар C: 600 продаж (топ-3)"
  ],
  "explanation": "Товар A и Товар B показывают одинаковые результаты по продажам (800), на третьем месте Товар C с 600 продажами.",
  "confidence": 0.95
}}

Be CONCISE, SPECIFIC, SCANNABLE!"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are a data analyst who creates STRUCTURED, SCANNABLE reports.

CRITICAL:
- NO walls of text - users won't read them
- Each point must be SHORT (50-80 chars max)
- Use CONCRETE numbers, not vague descriptions
- Be SPECIFIC and ACTIONABLE
- All text in Russian with emojis for visual structure
- DETERMINISTIC: Always sort data the same way (descending by value, then alphabetically by name)
- CONSISTENCY: Same query MUST return same results every time"""
                    },
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
                max_tokens=1000,
            )

            result = json.loads(response.choices[0].message.content)

            # DEBUG: Log GPT response
            print(f"📤 GPT-4o response keys: {list(result.keys())}")
            print(f"📤 Has methodology: {('methodology' in result)}")
            if 'methodology' in result:
                print(f"📤 methodology value: {result['methodology']}")

            result["processing_time"] = time.time() - start_time
            result["type"] = "analysis"

            # CRITICAL FIX: If GPT-4o didn't return methodology, generate default one
            if not result.get("methodology"):
                print("⚠️  GPT didn't return methodology, generating fallback...")
                column_list = ", ".join([f"'{col}'" for col in column_names[:5]])  # First 5 columns
                if len(column_names) > 5:
                    column_list += f" и ещё {len(column_names) - 5}"
                result["methodology"] = f"🔍 Как посчитано: проанализированы данные из таблицы (колонки: {column_list})"
                print(f"✅ Fallback methodology: {result['methodology']}")

            print(f"✅ Final result keys before return: {list(result.keys())}")
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

    async def _analyze_intent(
        self, query: str, column_names: List[str], sample_data: List[List[Any]] = None, history: List[dict] = None
    ) -> dict:
        """
        Step 1: Анализирует намерение пользователя и определяет глубину ответа

        Args:
            query: Запрос пользователя
            column_names: Названия колонок
            sample_data: Данные таблицы
            history: История предыдущих действий
        """
        row_count = len(sample_data) if sample_data else 0

        # Форматируем историю если есть
        history_text = ""
        if history and len(history) > 0:
            history_text = "\n\n# PREVIOUS ACTIONS (CONTEXT)\n"
            for i, item in enumerate(history[-3:]):  # Последние 3 действия
                # Безопасная проверка типа item
                if not isinstance(item, dict):
                    continue

                history_text += f"\n{i+1}. User: \"{item.get('query', '')}\"\n"
                if 'actions' in item:
                    actions = item['actions']
                    # Проверяем что actions это список
                    if not isinstance(actions, list):
                        continue

                    history_text += f"   Actions performed: {len(actions)} actions\n"
                    for action in actions:
                        # Проверяем что action это словарь
                        if not isinstance(action, dict):
                            continue
                        history_text += f"   - {action.get('type')}: {action.get('config', {})}\n"

        prompt = f"""Analyze user's intent and determine what they REALLY want.

USER REQUEST: "{query}"

DATA AVAILABLE:
- Columns: {', '.join(column_names)}
- {row_count} rows of data{history_text}

# INTENT CATEGORIES (PRIORITY ORDER - CHECK FROM TOP!)

1. QUESTION - User asks HOW/WHY/WHAT and wants text explanation (NOT actions!)
   CRITICAL Keywords: "как ты", "почему ты", "зачем ты", "по каким критерием", "по какому критерию", "объясни", "расскажи как"
   Examples: "как ты это посчитал?", "почему ты выбрал этот вариант?", "по каким критериям ты оценил?"
   ⚠️ PRIORITY: If query has "как ты/почему ты/по каким" → ALWAYS use QUESTION!

2. QUERY_DATA - User wants TEXT LIST of items (top, best, worst) WITHOUT chart
   CRITICAL Rule: Has "топ/лучш/худш/самые/больше всего/меньше всего" BUT NO "график/диаграмма/покажи/построй/визуализируй"
   Examples:
   - "топ 3 товара по продажам" → QUERY_DATA (text list!)
   - "у какого поставщика больше всего товаров" → QUERY_DATA (text answer!)
   - "лучшие продажи" → QUERY_DATA (text list!)
   - "худшие результаты" → QUERY_DATA (text list!)
   ⚠️ CRITICAL: "топ/лучш/худш" WITHOUT visualization keywords → QUERY_DATA!

3. VISUALIZE_DATA - User EXPLICITLY asks for chart/graph/visualization
   CRITICAL Keywords: "график", "диаграмма", "покажи на графике", "визуализируй", "построй график", "построй диаграмму"
   Examples:
   - "покажи график топ 3" → VISUALIZE_DATA (has "график"!)
   - "построй диаграмму продаж" → VISUALIZE_DATA (has "диаграмму"!)
   - "топ 3 товара график" → VISUALIZE_DATA (has "график"!)
   ⚠️ ONLY if query explicitly mentions chart/graph!

4. ANALYZE_PROBLEM - User wants detailed data analysis with text insights
   Keywords: "проанализируй", "изучи", "исследуй", "дай анализ"

5. FIND_INSIGHTS - User wants to discover patterns/trends with actions
   Keywords: "найди", "выяви", "определи", "тренд", "динамика"

6. COMPARE_DATA - User wants to compare values
   Keywords: "сравни", "vs", "разница"

7. FORMAT_PRESENTATION - User wants to make data look good
   Keywords: "оформи", "красиво", "выдели", "отформатируй"

8. CREATE_STRUCTURE - User wants to create data structure (pivot, summary table, etc)
   Keywords: "сделай", "создай", "сводную", "pivot", "таблицу", "структуру"

9. CALCULATE - User wants computed value
   Keywords: "посчитай", "сколько", "сумма", "формула"

# CRITICAL DECISION ALGORITHM (CHECK IN ORDER!):

STEP 1: Check for QUESTION keywords first
- Has "как ты/почему ты/по каким/объясни/расскажи как"? → QUESTION

STEP 2: Check for visualization keywords
- Has "график/диаграмма/покажи на графике/построй/визуализируй"? → VISUALIZE_DATA

STEP 3: Check for data query keywords WITHOUT visualization
- Has "топ/лучш/худш/самые/больше всего/меньше всего" AND NO visualization keywords? → QUERY_DATA

STEP 4: Other intents...

# OUTPUT FORMAT (valid JSON):
{{
  "intent": "QUERY_DATA",
  "depth": 1,
  "must_include": [],
  "context": "User wants text list of top items"
}}

# CRITICAL TEST CASES - MUST PASS ALL:

✅ "топ 3 товара по продажам" → {{"intent": "QUERY_DATA", "depth": 1}} (text list, NO visualization!)
✅ "у какого поставщика больше всего товаров" → {{"intent": "QUERY_DATA", "depth": 1}} (text answer!)
✅ "как ты это посчитал?" → {{"intent": "QUESTION", "depth": 1}} (explanation!)
✅ "по каким критериям ты оценил?" → {{"intent": "QUESTION", "depth": 1}} (explanation!)
✅ "лучшие продажи" → {{"intent": "QUERY_DATA", "depth": 1}} (text list!)
✅ "покажи график топ 3" → {{"intent": "VISUALIZE_DATA", "depth": 1}} (has "график"!)
✅ "топ 3 товара график" → {{"intent": "VISUALIZE_DATA", "depth": 1}} (has "график"!)
✅ "построй диаграмму продаж" → {{"intent": "VISUALIZE_DATA", "depth": 1}} (has "диаграмму"!)

# CONTEXT-AWARE MODIFICATIONS
If history exists AND user modifies previous action:
- Previous: create_chart, User: "не учитывай итого" → {{"intent": "VISUALIZE_DATA"}}
- Previous: create_chart, User: "переименуй в Продажи" → {{"intent": "VISUALIZE_DATA"}}

Return ONLY valid JSON. No explanations."""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an intent analyzer. Output valid JSON only, no explanations."
                    },
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
                max_tokens=200,
            )

            return json.loads(response.choices[0].message.content)
        except Exception as e:
            # Fallback: попытка определить intent по ключевым словам
            query_lower = query.lower()

            # Priority 1: Questions
            if any(kw in query_lower for kw in ["как ты", "почему ты", "зачем ты", "по каким", "по какому", "объясни"]):
                return {"intent": "QUESTION", "depth": 1, "must_include": [], "context": "Question fallback"}

            # Priority 2: Query data (top/best/worst WITHOUT visualization)
            has_query_keywords = any(kw in query_lower for kw in ["топ ", "лучш", "худш", "самые", "больше всего", "меньше всего"])
            has_viz_keywords = any(kw in query_lower for kw in ["график", "диаграмм", "визуализ", "построй", "покажи на"])

            if has_query_keywords and not has_viz_keywords:
                return {"intent": "QUERY_DATA", "depth": 1, "must_include": [], "context": "Query data fallback"}

            # Priority 3: Visualization
            if has_viz_keywords or "график" in query_lower or "диаграмм" in query_lower:
                return {"intent": "VISUALIZE_DATA", "depth": 1, "must_include": ["create_chart"], "context": "Visualization fallback"}

            # Default: text answer (safer than creating chart)
            return {"intent": "QUESTION", "depth": 1, "must_include": [], "context": "Default fallback"}

    async def generate_action_plan(
        self, query: str, column_names: List[str], sample_data: List[List[Any]] = None, history: List[dict] = None,
        selected_range: str = None, active_cell: str = None
    ) -> dict:
        """
        Генерирует план действий для сложных задач (2-step prompting)
        Step 1: Analyze intent
        Step 2: Generate minimal actions

        Args:
            query: Запрос пользователя
            column_names: Названия колонок
            sample_data: Данные таблицы
            history: История предыдущих действий для контекста
            selected_range: Выделенный диапазон (например 'H5:H17')
            active_cell: Активная ячейка (например 'H5')
        """
        start_time = time.time()

        # STEP 1: Analyze intent
        intent_analysis = await self._analyze_intent(query, column_names, sample_data, history)

        # Форматируем данные о колонках
        columns_info = []
        for i, col in enumerate(column_names):
            col_letter = chr(65 + i)  # A, B, C...
            columns_info.append(f"{col_letter}: {col}")

        # Берем sample data для контекста
        sample_rows = []
        if sample_data:
            for row in sample_data[:5]:
                sample_rows.append(row)

        # Форматируем историю для промпта
        history_context = ""
        if history and len(history) > 0:
            history_context = "\n\n# PREVIOUS ACTIONS (CONVERSATION HISTORY)\n"
            history_context += "User has already performed these actions:\n"
            for i, item in enumerate(history[-3:]):  # Последние 3 действия
                # Безопасная проверка типа item
                if not isinstance(item, dict):
                    continue

                history_context += f"\n{i+1}. User asked: \"{item.get('query', '')}\"\n"
                if 'actions' in item:
                    actions = item['actions']
                    # Проверяем что actions это список
                    if not isinstance(actions, list):
                        continue

                    history_context += f"   We performed {len(actions)} action(s):\n"
                    for action in actions:
                        # Проверяем что action это словарь
                        if not isinstance(action, dict):
                            continue
                        config_str = str(action.get('config', {}))[:100]  # First 100 chars
                        history_context += f"   - {action.get('type')}: {config_str}\n"
            history_context += "\n# CRITICAL RULES FOR MODIFYING EXISTING OBJECTS:\n"
            history_context += "\nIf user says 'эта диаграмма', 'этот график', 'эту таблицу', 'назови это' - they refer to objects from PREVIOUS ACTIONS!\n"
            history_context += "\nWhen MODIFYING existing object:\n"
            history_context += "1. COPY ALL parameters from the last matching action in history\n"
            history_context += "2. ONLY change the parameter user asks to change\n"
            history_context += "3. Keep everything else EXACTLY the same (type, dataRange, colors, etc.)\n"
            history_context += "\nEXAMPLE:\n"
            history_context += "Previous: {\"type\": \"create_chart\", \"config\": {\"type\": \"pie\", \"dataRange\": \"A2:B10\", \"title\": \"График\"}}\n"
            history_context += "User says: 'назови эту диаграмму Продажи'\n"
            history_context += "Correct response: {\"type\": \"create_chart\", \"config\": {\"type\": \"pie\", \"dataRange\": \"A2:B10\", \"title\": \"Продажи\"}}\n"
            history_context += "WRONG: Changing type from 'pie' to 'column' - USER DID NOT ASK FOR THIS!\n"

        # STEP 2: Generate actions based on intent
        prompt = f"""Create minimal executable actions based on intent analysis.

# INTENT ANALYSIS
{json.dumps(intent_analysis, ensure_ascii=False)}

# DATA CONTEXT

Columns: {', '.join(columns_info)}
Sample data (5 rows): {json.dumps(sample_rows[:5], ensure_ascii=False) if sample_rows else "[]"}

USER REQUEST: "{query}"{history_context}

# AVAILABLE ACTIONS (USE ONLY THESE 5 TYPES!)

1. create_chart (for graphs/charts)
   Config: {{"dataRange": "A2:B10", "type": "column|bar|line|pie|area", "title": "..."}}

2. format_cells (for static highlighting/coloring of specific cells)
   Config: {{"range": "A1:B10", "backgroundColor": "#hex", "textColor": "#hex", "bold": true, "fontSize": 12}}

3. apply_conditional_format (for DYNAMIC formatting based on conditions - when user wants cells to auto-update color based on value/date)

   SCENARIO A - Ready expiration date column exists:
   Config: {{"range": "A2:H100", "type": "date_expired", "column": "I", "backgroundColor": "#f4cccc"}}
   Use when: There's a column with END date (e.g., "Дата окончания", "Срок действия договора" as DATE, "Deadline")

   SCENARIO B - Need to calculate expiration (start date + duration in days):
   Config: {{"range": "A2:H100", "type": "custom_formula", "formula": "=$G2+$I2<TODAY()", "backgroundColor": "#f4cccc"}}
   Use when: You have START date column (e.g., "Дата заключения") + DURATION column (e.g., "Срок в днях": 60, 90, 270)
   Formula pattern: =$START_COL2+$DURATION_COL2<TODAY()
   Example: If "Дата заключения" is column G and "Срок действия в днях" is column I, use: "=$G2+$I2<TODAY()"

   SCENARIO C - Custom conditions:
   Config: {{"range": "A2:C100", "type": "custom_formula", "formula": "=$B2>1000", "backgroundColor": "#d9ead3"}}

   USE THIS WHEN:
   - User says "выделить строки где...", "подсветить если...", "окрасить когда срок истёк"
   - Formatting should CHANGE automatically when data changes
   - Checking dates (expired, upcoming), comparing values, conditional highlighting

   CRITICAL DECISION LOGIC FOR DATE EXPIRATION:
   1. Check column names carefully - look for "срок действия В ДНЯХ", "продолжительность", "длительность" (these are DURATIONS, not dates!)
   2. If you see duration in DAYS (number like 60, 90, 270), use SCENARIO B with custom_formula: =$START_DATE_COL+$DURATION_COL<TODAY()
   3. If you see actual END DATE (date like 01.05.2023), use SCENARIO A with type="date_expired"
   4. "range" must cover ALL data rows from A to last column (e.g., A2:I100, not A2:H5)
   5. Formula in custom_formula uses $ for absolute column reference (e.g., =$G2, not =G2)

4. insert_formula (for calculations/formulas)
   Config: {{"formula": "=SUM(A2:A10)", "cell": "B2"}}

5. sort_data (for sorting data)
   Config: {{"range": "A2:C10", "column": 2, "ascending": true}}

CRITICAL: NEVER invent new action types. ONLY use these 5 types above!

# ACTION TEMPLATES BY INTENT

## ANALYZE_PROBLEM (depth=3) - Need: sort + format + chart + formula
Example for declining sales analysis:
[
  {{"type": "sort_data", "config": {{"range": "A2:B13", "column": 2, "ascending": false}}}},
  {{"type": "format_cells", "config": {{"range": "B2:B3", "backgroundColor": "#ff0000", "textColor": "#ffffff", "bold": true}}}},
  {{"type": "insert_formula", "config": {{"cell": "C2", "formula": "=AVERAGE(B2:B13)"}}}},
  {{"type": "create_chart", "config": {{"dataRange": "A2:B13", "type": "line", "title": "Динамика продаж"}}}}
]

## VISUALIZE_DATA (depth=1) - Need: single chart only
[
  {{"type": "create_chart", "config": {{"dataRange": "A2:B10", "type": "column", "title": "График"}}}}
]

## FIND_INSIGHTS (depth=3) - Need: formula + format + chart
[
  {{"type": "insert_formula", "config": {{"cell": "C2", "formula": "=AVERAGE(B:B)"}}}},
  {{"type": "format_cells", "config": {{"range": "B2:B10", "backgroundColor": "#ffeb3b"}}}},
  {{"type": "create_chart", "config": {{"dataRange": "A2:B10", "type": "line", "title": "Тренд"}}}}
]

## COMPARE_DATA (depth=2) - Need: sort + chart
[
  {{"type": "sort_data", "config": {{"range": "A2:B10", "column": 2, "ascending": false}}}},
  {{"type": "create_chart", "config": {{"dataRange": "A2:B10", "type": "bar", "title": "Сравнение"}}}}
]

## FORMAT_PRESENTATION (depth=1) - Need: formatting only
[
  {{"type": "format_cells", "config": {{"range": "A1:B1", "bold": true, "fontSize": 14}}}}
]

## CREATE_STRUCTURE (depth=2-3) - Use REASONING FRAMEWORK!
Think: What data structure is needed? Apply Steps 1-4.

## All Operations - APPLY REASONING FIRST!
Don't look for examples - THINK through Steps 1-4 from system message!

# YOUR TASK
Based on intent analysis above, generate MINIMAL actions to fulfill user's request.
- Use EXACT column letters from DATA CONTEXT
- Match depth level from intent (1 action for depth=1, 2-3 for depth=2, 4+ for depth=3)
- Use must_include actions from intent
- Chart types: column (compare), line (trend), pie (proportions), bar (rankings)
- Titles max 30 chars in Russian
- Be SPECIFIC with ranges

# OUTPUT FORMAT (valid JSON):
{{
  "explanation": "Brief action description in Russian (max 50 chars)",
  "actions": [
    {{"type": "...", "config": {{...}}}}
  ],
  "confidence": 0.85
}}

CRITICAL: Response must be valid JSON. No extra text."""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an action generator with REASONING capabilities. Think step-by-step before generating actions.

CRITICAL RESTRICTIONS:
- ONLY 5 action types allowed: create_chart, format_cells, apply_conditional_format, insert_formula, sort_data
- NEVER invent new types like "highlight_trends", "add_summary", etc.
- Output valid JSON only, all explanations in Russian (max 50 chars)
- Use apply_conditional_format (NOT format_cells) when user wants DYNAMIC highlighting based on conditions

# REASONING FRAMEWORK (USE THIS TO THINK!)

Before generating ANY formula, ask yourself these questions:

## STEP 1: Task Scope Analysis
Q: Does this task apply to ONE cell or ALL rows?

Indicators for ALL ROWS:
- Keywords: "соедини", "объедини", "склей", "для каждого", "все строки", "в столбце X"
- User wants NEW column with computed values for each row
- Result should auto-fill as data grows

Indicators for ONE CELL:
- Keywords: "сумма", "среднее", "сколько всего", "итого"
- User wants single aggregate value
- Result is one number/text

Decision: If ALL ROWS → MUST use ARRAYFORMULA pattern!

## STEP 2: Operation Type & Context Analysis
What is the core operation?
- Text merge: A&" "&B&" "&C
- Math aggregate: SUM(), AVERAGE(), COUNT()
- Conditional aggregate: SUMIF(), COUNTIF(), AVERAGEIF()
- Unique values: UNIQUE()
- Lookup: VLOOKUP() or INDEX/MATCH
- Grouping: UNIQUE() + SUMIF/COUNTIF or QUERY

⚠️ КРИТИЧЕСКИЙ ВЫБОР: SUMIF vs QUERY
🚨 THIS IS THE MOST IMPORTANT DECISION! 🚨

STEP-BY-STEP ANALYSIS:
1. Does user mention TWO DIFFERENT columns? (e.g., "из столбца G" + "в столбце H")
2. Check for these EXACT phrases:
   - "для каждого X из столбца Y"
   - "для каждого поставщика из столбца G"
   - "для значений из столбца Y"
   - "по каждому X из столбца Y"
   - "в столбце H для X из столбца G"
   - ANY variation with "из столбца" (from column)

If ANY of these phrases found → 100% use SUMIF!

If YES (есть готовый список) - USE SUMIF:
- Keywords: "для каждого X из столбца Y", "в столбце H для значений из G", "из столбца"
- User mentions TWO columns: criteria column (where to get values FROM) + result column (where to put sums INTO)
- Example: "в столбце H посчитай суммы для каждого поставщика из столбца G"
  → Column G = criteria list (already exists)
  → Column H = where to put results
→ MUST use: ARRAYFORMULA with SUMIF($source$; criteria_column; $sum_column$)
→ Example: =ARRAYFORMULA(IF(G2:G=""; ""; SUMIF($D$2:$D; G2:G; $B$2:$B)))

If NO (нет готового списка) - USE QUERY:
- Keywords: "получи суммы по всем", "сводная таблица", "группировка", "список всех"
- User does NOT mention existing criteria column
- User wants to CREATE new unique list + aggregation
→ Use QUERY or UNIQUE() + SUMIF pattern

🚨 BEFORE choosing QUERY, ask yourself: "Did user say 'из столбца X'?" If YES → SUMIF!

## STEP 3: Formula Construction
Apply the correct pattern based on Steps 1 & 2:

### Pattern for ALL ROWS (ARRAYFORMULA):
```
=ARRAYFORMULA(IF(first_col:first_col=""; ""; operation_here))
```
⚠️ КРИТИЧЕСКИ ВАЖНО: Используй ТОЧКИ С ЗАПЯТОЙ (;) вместо запятых!
Русская версия Google Sheets требует точки с запятой как разделитель аргументов.

Why IF check? Avoids errors on empty rows.

Example thinking:
- User: "соедини ФИО в столбце D"
- Step 1: "в столбце D" = ALL ROWS ✓
- Step 2: "соедини" = text merge → A&" "&B&" "&C
- Step 3: Apply pattern → =ARRAYFORMULA(IF(A2:A="";"";A2:A&" "&B2:B&" "&C2:C))

### Pattern for ONE CELL (simple):
```
=OPERATION(range)
```

Example thinking:
- User: "средний чек"
- Step 1: ONE value = ONE CELL ✓
- Step 2: "средний" = AVERAGE()
- Step 3: =AVERAGE(B2:B)

## STEP 4: Actions Structure
For column operations, ALWAYS create 3 actions:
1. Header (D1) - insert_formula with text
2. Formula (D2) - insert_formula with actual formula
3. Format header (D1:D1) - format_cells bold

THINK THROUGH THESE STEPS FOR EVERY TASK!

# GOOGLE SHEETS FORMULA REFERENCE (QUICK LOOKUP ONLY)

⚠️ ВАЖНО: Все примеры используют ТОЧКИ С ЗАПЯТОЙ (;) как разделитель аргументов функций!
Это требование русской версии Google Sheets. НЕ используй запятые (,) внутри функций!

## 1. АГРЕГАЦИЯ И СТАТИСТИКА
- SUM(A2:A10) - сумма значений
- AVERAGE(A2:A10) - среднее значение
- COUNT(A2:A10) - количество чисел
- COUNTA(A2:A10) - количество непустых ячеек
- MAX(A2:A10) - максимальное значение
- MIN(A2:A10) - минимальное значение
- MEDIAN(A2:A10) - медиана
- STDEV(A2:A10) - стандартное отклонение

## 2. УСЛОВНЫЕ ФУНКЦИИ
- SUMIF($A$2:$A; "Яблоко"; $B$2:$B) - сумма по условию (с абсолютными ссылками!)
- SUMIFS($C$2:$C; $A$2:$A; "Яблоко"; $B$2:$B; ">100") - сумма по нескольким условиям
- COUNTIF($A$2:$A; "Яблоко") - подсчет по условию
- COUNTIFS($A$2:$A; "Яблоко"; $B$2:$B; ">100") - подсчет по нескольким условиям
- AVERAGEIF($A$2:$A; "Яблоко"; $B$2:$B) - среднее по условию
- AVERAGEIFS($C$2:$C; $A$2:$A; "Яблоко"; $B$2:$B; ">100") - среднее по нескольким условиям
- IF(A2>100; "Высокий"; "Низкий") - условие
- IFS(A2>1000; "Отлично"; A2>500; "Хорошо"; A2>0; "Плохо") - множественные условия

⚠️ КРИТИЧЕСКИ ВАЖНО для SUMIF/COUNTIF/AVERAGEIF в ARRAYFORMULA:
ВСЕГДА используй абсолютные ссылки ($) для диапазонов поиска и суммирования!
Пример: =ARRAYFORMULA(IF(G2:G=""; ""; SUMIF($D$2:$D; G2:G; $B$2:$B)))
        диапазоны D и B - абсолютные ($), критерий G - относительный (без $)

## 3. РАБОТА С МАССИВАМИ (СОВРЕМЕННЫЕ ФУНКЦИИ)
- UNIQUE(A2:A100) - уникальные значения (КЛЮЧЕВАЯ для сводных таблиц!)
- FILTER(A2:B100; B2:B100>1000) - фильтрация данных
- SORT(A2:B100; 2; FALSE) - сортировка (колонка 2, по убыванию)
- QUERY(A2:C100; "SELECT Col1, SUM(Col2) WHERE Col3='Категория' GROUP BY Col1"; 0) - SQL-подобные запросы
  ⚠️ КРИТИЧЕСКИ ВАЖНО для QUERY:
  1. Используй Col1, Col2, Col3... (НЕ A, B, C!)
  2. Диапазон ДОЛЖЕН включать ВСЕ столбцы, которые упоминаются в SELECT/WHERE
  3. Col1 = первый столбец диапазона, Col2 = второй, и т.д.
  4. Третий параметр (0 или 1) = количество строк заголовков
  Пример: Если нужны данные из столбцов B и D, диапазон должен быть A2:D (или B2:D),
  тогда в QUERY используй Col2 и Col4 (если A2:D) или Col1 и Col3 (если B2:D)
- ARRAYFORMULA(A2:A100 * B2:B100) - применить формулу к массиву

## 4. ПОИСК И СОПОСТАВЛЕНИЕ
- VLOOKUP(A2; D2:E100; 2; FALSE) - вертикальный поиск (ТОЛЬКО для одной ячейки!)
- XLOOKUP(A2; D2:D100; E2:E100) - современный поиск (если доступен)
- INDEX(D2:D100; MATCH(A2; C2:C100; 0)) - поиск через индекс
- MATCH(A2; C2:C100; 0) - позиция элемента в массиве

🚨 КРИТИЧЕСКИ ВАЖНО: VLOOKUP НЕ РАБОТАЕТ В ARRAYFORMULA!
❌ НЕПРАВИЛЬНО: =ARRAYFORMULA(IF(B2:B=""; ""; VLOOKUP(B2:B; H:I; 2; FALSE)))
✅ ПРАВИЛЬНО: =ARRAYFORMULA(IF(B2:B=""; ""; INDEX($H:$H; MATCH(B2:B; $I:$I; 0))))

Для массивных lookup операций ВСЕГДА используй INDEX/MATCH!
Пример с условием: =ARRAYFORMULA(IF(B2:B=""; ""; INDEX($H:$H; MATCH(B2:B; $I:$I; 0)) * IF(C2:C<5; 1; 1.05)))

## 5. ТЕКСТОВЫЕ ФУНКЦИИ
- CONCATENATE(A2; " "; B2) или A2&" "&B2 - объединение текста
- LEFT(A2; 5) - первые N символов
- RIGHT(A2; 5) - последние N символов
- MID(A2; 3; 5) - символы с позиции
- LEN(A2) - длина текста
- TRIM(A2) - удалить лишние пробелы
- UPPER(A2), LOWER(A2), PROPER(A2) - регистр текста

## 6. ДАТЫ И ВРЕМЯ
- TODAY() - текущая дата
- NOW() - текущая дата и время
- DATE(2024, 12, 31) - создать дату
- YEAR(A2), MONTH(A2), DAY(A2) - части даты
- DATEDIF(A2, B2, "D") - разница в днях
- EOMONTH(A2, 0) - конец месяца
- WEEKDAY(A2) - день недели (1-7)

## 7. COMMON PATTERNS (Apply reasoning first!)

Pivot table: UNIQUE() + SUMIF()
Concatenation: ARRAYFORMULA(IF(A2:A="","",A2:A&B2:B))
Top N: SORT() descending
Percentage: value/SUM($range)*100
Grouping: UNIQUE() + conditional functions

REMEMBER: Don't memorize patterns - THINK through Steps 1-4 for each task!"""
                    },
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
                max_tokens=800,
            )

            result = json.loads(response.choices[0].message.content)

            # Clean formulas in actions before mapping
            if 'actions' in result:
                for action in result['actions']:
                    if action.get('type') == 'insert_formula' and 'config' in action:
                        if 'formula' in action['config']:
                            action['config']['formula'] = self._clean_formula(action['config']['formula'])
                    # ВАЖНО: Применяем локализацию также к conditional_format формулам!
                    elif action.get('type') == 'apply_conditional_format' and 'config' in action:
                        if 'formula' in action['config']:
                            action['config']['formula'] = self._clean_formula(action['config']['formula'])

            # Map 'actions' to 'insights' for frontend compatibility
            if 'actions' in result:
                result['insights'] = result.pop('actions')

            # Add intent analysis metadata
            result["intent"] = intent_analysis.get("intent", "UNKNOWN")
            result["depth"] = intent_analysis.get("depth", 1)
            result["processing_time"] = time.time() - start_time
            result["type"] = "action"

            return result

        except Exception as e:
            return {
                "type": "error",
                "explanation": f"Ошибка генерации action plan: {str(e)}",
                "insights": [],
                "confidence": 0.0,
                "intent": "UNKNOWN",
                "depth": 0,
                "processing_time": time.time() - start_time
            }

    def get_stats(self) -> Dict[str, Any]:
        """
        Возвращает статистику работы сервиса
        """
        return self.stats.copy()

    async def generate_actions(
        self,
        query: str,
        sheet_data: Dict[str, Any],
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Генерирует действия для запроса с Test-and-Heal loop (если включен)
        PHASE 1.3: Добавлен timeout 30 секунд
        CONVERSATION HISTORY: Поддержка контекстных запросов

        Args:
            query: Запрос пользователя
            sheet_data: Данные о таблице:
                {
                    "columns": ["Имя", "Возраст", ...],
                    "row_count": 100,
                    "sample_data": [[...], [...], ...],
                    "sheet_id": "abc123"
                }
            conversation_id: ID разговора для контекстных запросов (опционально)

        Returns:
            {
                "success": True/False,
                "actions": [...],
                "source": "template" | "gpt",
                "validation_log": {...} (если были автофиксы),
                "execution": {...} (если Test-and-Heal включен),
                "conversation_id": "..." (для последующих запросов),
                "error": "..." (если ошибка)
            }
        """
        self.stats["total_requests"] += 1

        # PHASE 1.3: Timeout wrapper
        try:
            result = await asyncio.wait_for(
                self._generate_actions_internal(query, sheet_data, conversation_id),
                timeout=TOTAL_GENERATION_TIMEOUT
            )
            return result
        except asyncio.TimeoutError:
            # PHASE 1.5: Honest failure message
            return {
                "success": False,
                "error": f"Generation timeout ({TOTAL_GENERATION_TIMEOUT}s exceeded). Try simplifying your request or break it into smaller tasks.",
                "actions": [],
                "error_type": "timeout"
            }
        except Exception as e:
            # PHASE 1.5: Honest failure message
            return {
                "success": False,
                "error": f"Internal error: {str(e)}",
                "actions": [],
                "error_type": "internal_error"
            }

    async def _generate_actions_internal(
        self,
        query: str,
        sheet_data: Dict[str, Any],
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Internal implementation of generate_actions (wrapped with timeout)

        НОВАЯ АРХИТЕКТУРА (Interactive Builder):
        1. Intent Parser -> определяет намерение с certainty (с учетом истории!)
        2. Если certainty < 0.9 -> возвращает вопросы для уточнения
        3. Если certainty >= 0.9 -> Action Composer создает проверенный action
        4. Fallback на старый путь через GPT если что-то пошло не так
        5. CONVERSATION HISTORY: Поддержка reference queries ("попробуй еще раз", etc.)
        """

        try:
            # ===== INTERACTIVE BUILDER PATH =====
            from app.services.intent_parser import IntentParser, IntentType
            from app.services.clarification_dialog import ClarificationDialog
            from app.services.action_composer import ActionComposer, ActionCompositionError
            from app.services.intent_store import intent_store

            column_names = sheet_data.get("columns", [])
            sample_data = sheet_data.get("sample_data", [])
            row_count = sheet_data.get("row_count", len(sample_data) if sample_data else 100)

            context = {
                "columns": [chr(65 + i) for i in range(len(column_names))],  # A, B, C, ...
                "column_names": column_names,
                "sample_data": sample_data[:10] if sample_data else [],  # Первые 10 строк для контекста
                "row_count": row_count
            }

            # ШАГ 1: Получаем conversation и предыдущий intent (если есть)
            conversation = None
            previous_intent = None

            if conversation_id:
                conversation = intent_store.get_conversation(conversation_id)
                if conversation:
                    previous_intent = conversation.get_last_successful_intent()

            # Если conversation_id не передан, создаем новый
            if not conversation_id:
                conversation_id = intent_store.create_conversation()

            # ШАГ 2: Парсим intent с учетом истории (если есть)
            parser = IntentParser()

            if previous_intent:
                # Используем parse_with_history для обработки reference queries
                intent = parser.parse_with_history(query, context, previous_intent)
            else:
                # Обычный парсинг без истории
                intent = parser.parse(query, context)

            # ШАГ 2: Проверяем нужны ли уточнения
            dialog = ClarificationDialog(certainty_threshold=0.9)

            if dialog.needs_clarification(intent):
                # Генерируем вопросы для пользователя
                questions = dialog.generate_questions(intent)

                # Сохраняем Intent для последующего использования
                intent_id = intent_store.save(intent)

                result = {
                    "success": False,
                    "needs_clarification": True,
                    "intent_id": intent_id,  # ID для последующего запроса
                    "conversation_id": conversation_id,  # Возвращаем conversation_id
                    "questions": [
                        {
                            "parameter": q.parameter_name,
                            "text": q.question_text,
                            "type": q.question_type,
                            "options": q.options,
                            "required": q.required,
                            "help": q.help_text
                        }
                        for q in questions
                    ],
                    "intent_certainty": intent.certainty,
                    "message": "Пожалуйста, уточните параметры для создания точного результата"
                }

                # Сохраняем turn в conversation history (с clarification questions)
                intent_store.add_conversation_turn(
                    conversation_id=conversation_id,
                    query=query,
                    intent=intent,
                    result=result
                )

                return result

            # ШАГ 3: Создаем проверенный action через Action Composer
            composer = ActionComposer(min_certainty=0.9)

            try:
                action_obj = composer.compose(intent)

                # Конвертируем в формат старого API
                action = {
                    "type": action_obj.type,
                    "config": action_obj.config,
                    "reasoning": action_obj.explanation,
                    "source": "interactive_builder",  # Новый источник!
                    "confidence": action_obj.confidence
                }

                # ШАГ 4: Test-and-Heal loop (только для формул)
                if action["type"] == "insert_formula" and self.enable_test_and_heal and self.executor:
                    formula = action["config"]["formula"]
                    cell = action["config"]["cell"]

                    healing_result = await self._test_and_heal_formula(
                        formula,
                        cell,
                        sheet_data.get("sheet_id", "test-sheet"),
                        {
                            "query": query,
                            "columns": column_names
                        }
                    )

                    action["execution"] = healing_result

                    if not healing_result["success"]:
                        return {
                            "success": False,
                            "error": "Formula failed after healing attempts",
                            "actions": [action],
                            "conversation_id": conversation_id
                        }

                # Создаем результат
                result = {
                    "success": True,
                    "actions": [action],
                    "source": "interactive_builder",
                    "confidence": action_obj.confidence,
                    "explanation": action_obj.explanation,
                    "conversation_id": conversation_id  # Возвращаем conversation_id
                }

                # ШАГ 5: Сохраняем turn в conversation history
                intent_store.add_conversation_turn(
                    conversation_id=conversation_id,
                    query=query,
                    intent=intent,
                    result=result
                )

                return result

            except ActionCompositionError as e:
                # Action Composer не смог создать action - значит нужны уточнения
                # Но dialog.needs_clarification() не обнаружил это!
                # Это edge case - возвращаем ошибку
                return {
                    "success": False,
                    "error": f"Cannot create action: {str(e)}",
                    "needs_clarification": True,
                    "message": "Недостаточно информации для создания точного результата. Попробуйте уточнить запрос."
                }

        except Exception as interactive_error:
            # ===== FALLBACK TO OLD PATH =====
            # Если Interactive Builder не справился, используем старый путь
            print(f"[FALLBACK] Interactive Builder failed: {interactive_error}. Using old path.")

            try:
                # ШАГ 1: Генерируем формулу (через generate_formula)
                column_names = sheet_data.get("columns", [])
                sample_data = sheet_data.get("sample_data", [])

                formula_result = await self.generate_formula(
                    query,
                    column_names,
                    sample_data
                )

                if formula_result.get("type") == "error":
                    return {
                        "success": False,
                        "error": formula_result.get("explanation", "Unknown error"),
                        "actions": []
                    }

                formula = formula_result.get("formula")

                # Формируем action
                action = {
                    "type": "insert_formula",
                    "config": {
                        "cell": formula_result.get("target_cell", "D1"),
                        "formula": formula
                    },
                    "reasoning": formula_result.get("explanation", ""),
                    "source": formula_result.get("source", "gpt")
                }

                # ШАГ 2: Test-and-Heal loop (если включен)
                if self.enable_test_and_heal and self.executor:
                    healing_result = await self._test_and_heal_formula(
                        formula,
                        action["config"]["cell"],
                        sheet_data.get("sheet_id", "test-sheet"),
                        {
                            "query": query,
                            "columns": column_names
                        }
                    )

                    action["execution"] = healing_result

                    if not healing_result["success"]:
                        return {
                            "success": False,
                            "error": "Formula failed after healing attempts",
                            "actions": [action],
                            "validation_log": formula_result.get("validation_log")
                        }

                return {
                    "success": True,
                    "actions": [action],
                    "source": formula_result.get("source"),
                    "validation_log": formula_result.get("validation_log")
                }

            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "actions": []
                }

    async def apply_clarification(
        self,
        intent_id: str,
        answers: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Применяет ответы пользователя на clarification вопросы и создает action

        Args:
            intent_id: ID сохраненного Intent
            answers: Ответы пользователя {parameter_name: value}

        Returns:
            Результат с action или ошибкой
        """
        try:
            # Извлекаем сохраненный Intent
            from app.services.intent_store import intent_store
            from app.services.clarification_dialog import ClarificationDialog
            from app.services.action_composer import ActionComposer, ActionCompositionError

            intent = intent_store.get(intent_id)

            if not intent:
                return {
                    "success": False,
                    "error": "Intent not found or expired. Please start over.",
                    "error_type": "intent_expired"
                }

            # Применяем ответы к Intent
            dialog = ClarificationDialog()
            intent_with_answers = dialog.apply_answers(intent, answers)

            # Создаем action через Action Composer
            composer = ActionComposer(min_certainty=0.9)

            try:
                action_obj = composer.compose(intent_with_answers)

                # Конвертируем в формат API
                action = {
                    "type": action_obj.type,
                    "config": action_obj.config,
                    "reasoning": action_obj.explanation,
                    "source": "interactive_builder",
                    "confidence": action_obj.confidence
                }

                # Удаляем Intent из store (больше не нужен)
                intent_store.delete(intent_id)

                return {
                    "success": True,
                    "actions": [action],
                    "source": "interactive_builder",
                    "confidence": action_obj.confidence,
                    "explanation": action_obj.explanation
                }

            except ActionCompositionError as e:
                # Все еще недостаточно информации
                return {
                    "success": False,
                    "error": f"Cannot create action: {str(e)}",
                    "needs_more_clarification": True
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": "internal_error"
            }

    async def _test_and_heal_formula(
        self,
        formula: str,
        cell: str,
        sheet_id: str,
        context: Dict[str, Any],
        max_attempts: int = MAX_HEAL_ATTEMPTS  # PHASE 1.3: Use constant
    ) -> Dict[str, Any]:
        """
        Test-and-Heal loop

        Пытается выполнить формулу в Sheets, если не работает - лечит и повторяет

        Returns:
            {
                "tested": True,
                "success": True/False,
                "attempts": 2,
                "healed": True/False,
                "final_formula": "=...",
                "error": "..." (если не удалось)
            }
        """

        current_formula = formula
        attempt = 1

        while attempt <= max_attempts:
            # Выполняем формулу
            exec_result = await self.executor.execute_and_verify(
                sheet_id,
                cell,
                current_formula
            )

            if exec_result.success:
                # Успех!
                return {
                    "tested": True,
                    "success": True,
                    "attempts": attempt,
                    "healed": attempt > 1,
                    "final_formula": current_formula
                }

            # Формула не сработала - пробуем вылечить
            self.stats["healing_attempts"] += 1

            if attempt >= max_attempts:
                # PHASE 1.5: Honest failure message - исчерпали попытки
                return {
                    "tested": True,
                    "success": False,
                    "attempts": attempt,
                    "healed": False,
                    "error": f"Formula failed after {max_attempts} attempts. Last error: {exec_result.error}",
                    "error_type": exec_result.error_type,
                    "suggestion": "Try rephrasing your request or breaking it into smaller steps"
                }

            # Пробуем healing
            healed_formula = await self.healing_service.heal_formula(
                current_formula,
                {
                    "error_type": exec_result.error_type,
                    "error_message": exec_result.error,
                    "result_preview": exec_result.result_preview
                },
                context,
                attempt
            )

            if healed_formula and healed_formula != current_formula:
                # Получили новую формулу - пробуем её
                current_formula = healed_formula
                attempt += 1
                continue
            else:
                # PHASE 1.5: Honest failure - healing не смог помочь
                return {
                    "tested": True,
                    "success": False,
                    "attempts": attempt,
                    "healed": False,
                    "error": f"Unable to fix formula automatically. Original error: {exec_result.error}",
                    "error_type": exec_result.error_type,
                    "suggestion": "This task may be too complex for automatic formula generation. Consider manual approach or break into simpler steps."
                }

        # PHASE 1.5: Honest failure - fallback case
        return {
            "tested": True,
            "success": False,
            "attempts": max_attempts,
            "healed": False,
            "error": f"Formula generation failed after {max_attempts} attempts",
            "suggestion": "Try breaking your task into smaller, simpler steps"
        }


# Синглтон
ai_service = AIService()
