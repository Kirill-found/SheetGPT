"""
Валидатор формул Google Sheets.
Находит типичные ошибки которые делает GPT.
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
import re


@dataclass
class ValidationIssue:
    """Описание найденной проблемы"""
    issue_type: str  # тип ошибки
    severity: str  # "critical", "high", "medium", "low"
    message: str  # описание проблемы
    location: Optional[str] = None  # где в формуле
    suggested_fix: Optional[str] = None  # предложенное исправление
    auto_fixable: bool = False  # можно ли автоматически исправить


class FormulaValidator:
    """
    Проверяет формулы на типичные ошибки GPT
    """
    
    def __init__(self):
        self.validation_rules = self._init_validation_rules()
    
    def validate(
        self, 
        formula: str, 
        context: Optional[Dict] = None
    ) -> List[ValidationIssue]:
        """
        Проверяет формулу и возвращает список проблем
        
        Args:
            formula: формула для проверки
            context: дополнительный контекст (row_count, column_names, etc)
            
        Returns:
            Список найденных проблем
        """
        issues = []

        # Не делаем early return - пусть проверки найдут все проблемы
        # if not formula or not formula.startswith('='):
        #     issues.append(ValidationIssue(
        #         issue_type="invalid_formula",
        #         severity="critical",
        #         message="Формула должна начинаться с =",
        #         auto_fixable=False
        #     ))
        #     return issues
        
        # Прогоняем через все правила валидации
        for rule in self.validation_rules:
            rule_issues = rule(formula, context or {})
            issues.extend(rule_issues)
        
        return issues
    
    def _init_validation_rules(self) -> List:
        """Инициализирует правила валидации"""
        return [
            self._check_english_functions,  # НОВОЕ: проверка локализации
            self._check_arrayformula_open_range,
            self._check_vlookup_missing_false,
            self._check_concatenation_no_empty_check,
            self._check_date_operations_no_datevalue,
            self._check_missing_iferror,
            self._check_cyrillic_in_ranges,
            self._check_sumif_argument_order,
            self._check_if_direct_empty_comparison,
            self._check_concatenation_no_trim,
            self._check_vlookup_no_iferror,
            self._check_percentage_division,
            self._check_wrong_round_function,
            self._check_count_vs_counta,
            self._check_direct_date_comparison,
            self._check_multiple_spaces,
            self._check_quote_escaping,  # PHASE 1.1: Fix \" → ""
            # PHASE 1.2: Basic syntax validation
            self._check_unbalanced_parentheses,
            self._check_starts_with_equals,
            self._check_invalid_cell_ranges,
            # PHASE 2.2: Column reference validation
            self._check_invalid_column_references
        ]

    # =============================================================================
    # ПРАВИЛО #0: Проверка локализации функций (для русской версии Google Sheets)
    # =============================================================================

    def _check_english_functions(
        self,
        formula: str,
        context: Dict
    ) -> List[ValidationIssue]:
        """
        КРИТИЧНО: Английские функции в формулах → не работают в русской версии Google Sheets
        Должны быть русские: TODAY→СЕГОДНЯ, IF→ЕСЛИ, SUM→СУММ, и т.д.
        """
        issues = []

        # Словарь английских функций которые нужно локализовать
        # (такой же как в ai_service._clean_formula)
        english_functions = [
            'TODAY', 'IF', 'ISBLANK', 'ISNUMBER', 'ISTEXT', 'ISERROR', 'ISNA',
            'MATCH', 'INDEX', 'VLOOKUP', 'HLOOKUP',
            'COUNTIF', 'COUNTIFS', 'SUMIF', 'SUMIFS', 'AVERAGEIF', 'AVERAGEIFS',
            'FALSE', 'TRUE', 'AND', 'OR', 'NOT',
            'LEFT', 'RIGHT', 'MID', 'LEN', 'TRIM', 'UPPER', 'LOWER', 'CONCATENATE',
            'SUM', 'AVERAGE', 'COUNT', 'COUNTA', 'MAX', 'MIN',
            'SEARCH', 'FIND', 'SUBSTITUTE'
        ]

        # Проверяем наличие английских функций
        found_functions = []
        for func in english_functions:
            # Паттерн: функция + открывающая скобка (word boundary для точности)
            pattern = r'\b' + func + r'(?=\()'
            if re.search(pattern, formula, re.IGNORECASE):
                found_functions.append(func)

        if found_functions:
            issues.append(ValidationIssue(
                issue_type="not_localized",
                severity="low",  # LOW severity чтобы применялась ПОСЛЕДНЕЙ после всех фиксов
                message=f"Функции на английском: {', '.join(found_functions)} - не работают в русской версии Google Sheets",
                location=', '.join(found_functions),
                suggested_fix="Заменить на русские функции (TODAY→СЕГОДНЯ, IF→ЕСЛИ, и т.д.)",
                auto_fixable=True
            ))

        return issues

    # =============================================================================
    # ПРАВИЛО #1: ARRAYFORMULA с open range
    # =============================================================================
    
    def _check_arrayformula_open_range(
        self, 
        formula: str, 
        context: Dict
    ) -> List[ValidationIssue]:
        """
        КРИТИЧНО: ARRAYFORMULA(A2:A...) → ошибка
        Должно быть: ARRAYFORMULA(A2:A100...)
        """
        issues = []
        
        if "ARRAYFORMULA" not in formula.upper():
            return issues
        
        # Паттерн: буква + число + : + буква БЕЗ числа
        # Примеры: A2:A, B5:B, C2:C
        pattern = r'([A-Z]+)(\d+):([A-Z]+)(?![0-9])'
        matches = re.finditer(pattern, formula)
        
        for match in matches:
            col1, row1, col2 = match.groups()
            
            # Если это внутри ARRAYFORMULA - это ошибка
            # Проверяем что match находится внутри ARRAYFORMULA
            start_pos = match.start()
            
            # Найдем ближайший ARRAYFORMULA перед этой позицией
            arrayformula_pos = formula.upper().rfind("ARRAYFORMULA", 0, start_pos)
            
            if arrayformula_pos != -1:
                # Проверим что между ARRAYFORMULA и match нет закрывающей скобки
                between = formula[arrayformula_pos:start_pos]
                open_count = between.count('(')
                close_count = between.count(')')
                
                if open_count > close_count:  # мы внутри ARRAYFORMULA
                    # Определяем end_row из контекста
                    end_row = context.get('row_count', 100)
                    
                    issues.append(ValidationIssue(
                        issue_type="arrayformula_open_range",
                        severity="critical",
                        message=f"ARRAYFORMULA с open range {match.group(0)} - не работает!",
                        location=match.group(0),
                        suggested_fix=f"{col1}{row1}:{col2}{end_row}",
                        auto_fixable=True
                    ))
        
        return issues
    
    # =============================================================================
    # ПРАВИЛО #2: VLOOKUP без FALSE
    # =============================================================================
    
    def _check_vlookup_missing_false(
        self, 
        formula: str, 
        context: Dict
    ) -> List[ValidationIssue]:
        """
        VLOOKUP(...) без FALSE → approximate match (обычно неправильно)
        Должно быть: VLOOKUP(..., FALSE)
        """
        issues = []
        
        if "VLOOKUP" not in formula.upper():
            return issues
        
        # Паттерн: VLOOKUP с 3 или 4 аргументами
        # VLOOKUP(A2, B:C, 2) - 3 аргумента (плохо)
        # VLOOKUP(A2, B:C, 2, FALSE) - 4 аргумента (хорошо)
        
        # Найдем все VLOOKUP
        pattern = r'VLOOKUP\s*\([^)]+\)'
        matches = re.finditer(pattern, formula, re.IGNORECASE)
        
        for match in matches:
            vlookup_content = match.group(0)
            
            # Проверяем есть ли FALSE или 0 в конце
            has_false = 'FALSE' in vlookup_content.upper()
            has_zero = re.search(r',\s*0\s*\)', vlookup_content)
            
            if not has_false and not has_zero:
                issues.append(ValidationIssue(
                    issue_type="vlookup_missing_false",
                    severity="high",
                    message="VLOOKUP без FALSE - будет искать приблизительное совпадение",
                    location=vlookup_content,
                    suggested_fix=vlookup_content.rstrip(')') + ',FALSE)',
                    auto_fixable=True
                ))
        
        return issues
    
    # =============================================================================
    # ПРАВИЛО #3: Конкатенация без проверки пустых
    # =============================================================================
    
    def _check_concatenation_no_empty_check(
        self, 
        formula: str, 
        context: Dict
    ) -> List[ValidationIssue]:
        """
        =A2&" "&B2 без проверки на пустые ячейки
        Проблема: если A2 пустое → результат " John" (лишний пробел)
        """
        issues = []
        
        # Паттерн: прямая конкатенация без IF
        # A2&" "&B2 или A2&","&B2
        if '&' in formula and 'IF' not in formula.upper():
            # Простая эвристика: если есть & и нет IF - вероятно проблема
            
            # Более точная проверка: найти все конкатенации
            concat_pattern = r'[A-Z]+\d+\s*&\s*["\'][^"\']*["\']\s*&\s*[A-Z]+\d+'
            
            if re.search(concat_pattern, formula):
                issues.append(ValidationIssue(
                    issue_type="concatenation_no_empty_check",
                    severity="medium",
                    message="Конкатенация без проверки пустых ячеек - могут быть лишние разделители",
                    location="concatenation",
                    suggested_fix="Обернуть в IF(LEN(...)=0,...)",
                    auto_fixable=True
                ))
        
        return issues
    
    # =============================================================================
    # ПРАВИЛО #4: Операции с датами без DATEVALUE
    # =============================================================================
    
    def _check_date_operations_no_datevalue(
        self, 
        formula: str, 
        context: Dict
    ) -> List[ValidationIssue]:
        """
        =TODAY()-A2 где A2 это текст вида "15.11.2024"
        Должно быть: =TODAY()-DATEVALUE(A2)
        """
        issues = []
        
        # Если есть TODAY() или NOW() и операция с ячейкой
        if ('TODAY()' in formula.upper() or 'NOW()' in formula.upper()):
            # И есть операция вычитания с ячейкой
            if re.search(r'(TODAY|NOW)\(\)\s*[-+]\s*[A-Z]+\d+', formula, re.IGNORECASE):
                # И нет DATEVALUE
                if 'DATEVALUE' not in formula.upper():
                    issues.append(ValidationIssue(
                        issue_type="date_operation_no_datevalue",
                        severity="high",
                        message="Операция с датой без DATEVALUE - может не работать если дата в текстовом формате",
                        location="date operation",
                        suggested_fix="Обернуть ячейку в DATEVALUE()",
                        auto_fixable=True
                    ))
        
        return issues
    
    # =============================================================================
    # ПРАВИЛО #5: Отсутствие IFERROR для рискованных функций
    # =============================================================================
    
    def _check_missing_iferror(
        self, 
        formula: str, 
        context: Dict
    ) -> List[ValidationIssue]:
        """
        Рискованные функции без IFERROR: VLOOKUP, INDEX, MATCH, INDIRECT
        """
        issues = []
        
        risky_functions = ['VLOOKUP', 'INDEX', 'MATCH', 'INDIRECT', 'FIND', 'SEARCH']
        
        # Проверяем есть ли рискованная функция
        has_risky = any(func in formula.upper() for func in risky_functions)
        
        if has_risky and 'IFERROR' not in formula.upper():
            issues.append(ValidationIssue(
                issue_type="missing_iferror",
                severity="medium",
                message="Рискованная функция без IFERROR - может показать #N/A или #ERROR",
                location="formula",
                suggested_fix="Обернуть в IFERROR(..., default_value)",
                auto_fixable=True
            ))
        
        return issues
    
    # =============================================================================
    # ПРАВИЛО #6: Кириллица в именах диапазонов
    # =============================================================================
    
    def _check_cyrillic_in_ranges(
        self, 
        formula: str, 
        context: Dict
    ) -> List[ValidationIssue]:
        """
        =SUM(Продажи2:Продажи10) - не работает!
        Google Sheets не поддерживает кириллицу в диапазонах
        """
        issues = []
        
        # Паттерн: кириллические буквы + цифры в диапазоне
        pattern = r'[А-Яа-я]+\d+:[А-Яа-я]+\d+'
        
        if re.search(pattern, formula):
            issues.append(ValidationIssue(
                issue_type="cyrillic_in_range",
                severity="critical",
                message="Кириллица в имени диапазона - не поддерживается!",
                location=re.search(pattern, formula).group(0),
                suggested_fix="Использовать буквы столбцов (A, B, C...)",
                auto_fixable=False  # нужен column mapping
            ))
        
        return issues
    
    # =============================================================================
    # ПРАВИЛО #7: Неправильный порядок аргументов SUMIF
    # =============================================================================
    
    def _check_sumif_argument_order(
        self, 
        formula: str, 
        context: Dict
    ) -> List[ValidationIssue]:
        """
        SUMIF(sum_range, criteria, criteria_range) - НЕПРАВИЛЬНО!
        Должно быть: SUMIF(criteria_range, criteria, sum_range)
        """
        issues = []
        
        # Это сложно проверить без парсинга аргументов
        # Простая эвристика: если SUMIF и диапазоны выглядят "подозрительно"
        
        # TODO: можно улучшить парсингом
        
        return issues
    
    # =============================================================================
    # ПРАВИЛО #8: IF с прямым сравнением с пустотой
    # =============================================================================
    
    def _check_if_direct_empty_comparison(
        self, 
        formula: str, 
        context: Dict
    ) -> List[ValidationIssue]:
        """
        =IF(A2="", ...) - может не работать надежно
        Лучше: =IF(LEN(A2)=0, ...)
        """
        issues = []
        
        # Паттерн: IF с проверкой на пустую строку
        pattern = r'IF\s*\(\s*[A-Z]+\d+\s*=\s*["\']["\']'
        
        if re.search(pattern, formula, re.IGNORECASE):
            issues.append(ValidationIssue(
                issue_type="if_direct_empty_comparison",
                severity="low",
                message="Прямое сравнение с пустой строкой - лучше использовать LEN()=0",
                location="IF condition",
                suggested_fix="Заменить A2=\"\" на LEN(A2)=0",
                auto_fixable=True
            ))
        
        return issues
    
    # =============================================================================
    # ПРАВИЛО #9: Конкатенация без TRIM
    # =============================================================================
    
    def _check_concatenation_no_trim(
        self, 
        formula: str, 
        context: Dict
    ) -> List[ValidationIssue]:
        """
        =A2&" "&B2 без TRIM - могут быть лишние пробелы
        """
        issues = []
        
        if '&' in formula and 'TRIM' not in formula.upper():
            # Если конкатенация без TRIM - предупреждение
            issues.append(ValidationIssue(
                issue_type="concatenation_no_trim",
                severity="low",
                message="Конкатенация без TRIM - могут быть лишние пробелы",
                location="concatenation",
                suggested_fix="Обернуть результат в TRIM()",
                auto_fixable=True
            ))
        
        return issues
    
    # =============================================================================
    # ПРАВИЛО #10: VLOOKUP без IFERROR (дубликат #5 но специфичный)
    # =============================================================================
    
    def _check_vlookup_no_iferror(
        self, 
        formula: str, 
        context: Dict
    ) -> List[ValidationIssue]:
        """
        VLOOKUP без IFERROR - будет показывать #N/A если не найдено
        """
        issues = []
        
        if 'VLOOKUP' in formula.upper() and 'IFERROR' not in formula.upper():
            issues.append(ValidationIssue(
                issue_type="vlookup_no_iferror",
                severity="high",
                message="VLOOKUP без IFERROR - покажет #N/A если значение не найдено",
                location="VLOOKUP",
                suggested_fix='IFERROR(VLOOKUP(...), "Не найдено")',
                auto_fixable=True
            ))
        
        return issues
    
    # =============================================================================
    # ПРАВИЛО #16: Quote Escaping (PHASE 1.1 - критичный фикс)
    # =============================================================================

    def _check_quote_escaping(
        self,
        formula: str,
        context: Dict
    ) -> List[ValidationIssue]:
        """
        КРИТИЧНО: Backslash escaping внутри строк не работает в Google Sheets.
        Вместо backslash+quote должны использоваться двойные кавычки.
        """
        issues = []

        # Проверяем наличие \" внутри формулы
        if '\\"' in formula or r'\"' in formula:
            issues.append(ValidationIssue(
                issue_type="wrong_quote_escaping",
                severity="critical",
                message='Неправильное экранирование кавычек: \\" не работает в Google Sheets',
                location=r'\"',
                suggested_fix='Используй двойные кавычки "" вместо \\"',
                auto_fixable=True
            ))

        return issues

    # =============================================================================
    # ПРАВИЛО #17-19: Basic Syntax Validation (PHASE 1.2)
    # =============================================================================

    def _check_unbalanced_parentheses(
        self,
        formula: str,
        context: Dict
    ) -> List[ValidationIssue]:
        """
        КРИТИЧНО: Несбалансированные скобки → синтаксическая ошибка.
        """
        issues = []

        # Считаем открывающие и закрывающие скобки
        open_count = formula.count('(')
        close_count = formula.count(')')

        if open_count != close_count:
            issues.append(ValidationIssue(
                issue_type="unbalanced_parentheses",
                severity="critical",
                message=f'Несбалансированные скобки: {open_count} открывающих, {close_count} закрывающих',
                location=formula,
                suggested_fix='Проверь количество скобок',
                auto_fixable=False  # Сложно автоматически исправить
            ))

        return issues

    def _check_starts_with_equals(
        self,
        formula: str,
        context: Dict
    ) -> List[ValidationIssue]:
        """
        КРИТИЧНО: Формула должна начинаться с =
        """
        issues = []

        if not formula.strip().startswith('='):
            issues.append(ValidationIssue(
                issue_type="missing_equals",
                severity="critical",
                message='Формула должна начинаться с =',
                location=formula[:10],
                suggested_fix='Добавь = в начало формулы',
                auto_fixable=True
            ))

        return issues

    def _check_invalid_cell_ranges(
        self,
        formula: str,
        context: Dict
    ) -> List[ValidationIssue]:
        """
        КРИТИЧНО: Некорректные диапазоны ячеек типа A2:10 или :B5
        """
        issues = []

        # Паттерн для некорректных диапазонов
        # Ищем : без ячейки с одной стороны
        invalid_patterns = [
            r'[^A-Z0-9]:[A-Z]+\d+',  # (:A10 или =:A10) - нет начальной ячейки
            r':\d+',  # :10 (нет начальной ячейки, только цифры)
            r'[A-Z]+:(?![A-Z])',  # A: (нет конечной ячейки)
            r'\d+:[A-Z]+\d+',  # 10:A5 (начинается с числа)
        ]

        for pattern in invalid_patterns:
            matches = re.findall(pattern, formula)
            if matches:
                issues.append(ValidationIssue(
                    issue_type="invalid_cell_range",
                    severity="high",
                    message=f'Некорректный диапазон ячеек: {matches[0]}',
                    location=matches[0],
                    suggested_fix='Используй корректный формат диапазона (например A2:A10)',
                    auto_fixable=False
                ))
                break  # Достаточно одной ошибки

        return issues

    # =============================================================================
    # ПРАВИЛО #20: Column Reference Validation (PHASE 2.2)
    # =============================================================================

    def _check_invalid_column_references(
        self,
        formula: str,
        context: Dict
    ) -> List[ValidationIssue]:
        """
        ПРЕДУПРЕЖДЕНИЕ: Ссылки на несуществующие колонки.
        Проверяет что все колонки в формуле существуют в таблице.

        Например, если в таблице колонки A, B, C (3 колонки),
        а формула ссылается на D5 → это ошибка.
        """
        issues = []

        # Получаем максимальную колонку из контекста
        column_count = context.get('column_count')
        column_names = context.get('column_names', [])

        if not column_count and not column_names:
            # Нет информации о колонках - пропускаем проверку
            return issues

        # Если есть column_count, вычисляем максимальную букву колонки
        if column_count:
            max_col_letter = self._number_to_column_letter(column_count)
        elif column_names:
            max_col_letter = self._number_to_column_letter(len(column_names))
        else:
            return issues

        # Находим все ссылки на колонки в формуле (A1, B2, AA5, etc)
        # Паттерн: буква(ы) + цифра(ы)
        pattern = r'\b([A-Z]+)\d+'
        matches = re.findall(pattern, formula)

        invalid_cols = []
        for col_letter in set(matches):
            col_number = self._column_letter_to_number(col_letter)
            if col_number > column_count if column_count else len(column_names):
                invalid_cols.append(col_letter)

        if invalid_cols:
            issues.append(ValidationIssue(
                issue_type="invalid_column_reference",
                severity="high",
                message=f'Ссылки на несуществующие колонки: {", ".join(invalid_cols)}. Таблица имеет только {column_count or len(column_names)} колонок (до {max_col_letter})',
                location=", ".join(invalid_cols),
                suggested_fix=f'Проверь что формула ссылается только на существующие колонки (A-{max_col_letter})',
                auto_fixable=False
            ))

        return issues

    def _column_letter_to_number(self, letters: str) -> int:
        """Конвертирует букву колонки в номер: A->1, B->2, Z->26, AA->27"""
        num = 0
        for char in letters:
            num = num * 26 + (ord(char) - ord('A') + 1)
        return num

    def _number_to_column_letter(self, num: int) -> str:
        """Конвертирует номер в букву колонки: 1->A, 2->B, 26->Z, 27->AA"""
        result = ""
        while num > 0:
            num -= 1
            result = chr(ord('A') + num % 26) + result
            num //= 26
        return result

    # =============================================================================
    # ОСТАЛЬНЫЕ ПРАВИЛА (упрощенные версии)
    # =============================================================================

    def _check_percentage_division(self, formula: str, context: Dict) -> List[ValidationIssue]:
        """Проверка деления на 100 для процентов"""
        # TODO: implement
        return []
    
    def _check_wrong_round_function(self, formula: str, context: Dict) -> List[ValidationIssue]:
        """ROUNDUP вместо ROUND"""
        # TODO: implement
        return []
    
    def _check_count_vs_counta(self, formula: str, context: Dict) -> List[ValidationIssue]:
        """COUNT vs COUNTA"""
        # TODO: implement
        return []
    
    def _check_direct_date_comparison(self, formula: str, context: Dict) -> List[ValidationIssue]:
        """Прямое сравнение дат"""
        # TODO: implement
        return []
    
    def _check_multiple_spaces(self, formula: str, context: Dict) -> List[ValidationIssue]:
        """Множественные пробелы"""
        # TODO: implement
        return []
    
    def is_valid(self, issues: List[ValidationIssue]) -> bool:
        """
        Проверяет есть ли критичные ошибки
        """
        critical_issues = [i for i in issues if i.severity == "critical"]
        return len(critical_issues) == 0
    
    def get_auto_fixable_issues(
        self, 
        issues: List[ValidationIssue]
    ) -> List[ValidationIssue]:
        """
        Возвращает только те проблемы которые можно автоматически исправить
        """
        return [i for i in issues if i.auto_fixable]