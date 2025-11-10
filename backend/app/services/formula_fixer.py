"""
Автоматический fixer для формул.
Исправляет типичные ошибки которые находит validator.
"""

import re
from typing import Dict, Optional
from .formula_validator import ValidationIssue


class FormulaFixer:
    """
    Автоматически исправляет формулы
    """
    
    def fix(
        self, 
        formula: str, 
        issues: list[ValidationIssue],
        context: Optional[Dict] = None
    ) -> str:
        """
        Применяет автоматические исправления
        
        Args:
            formula: оригинальная формула
            issues: список проблем от validator
            context: контекст (row_count, etc)
            
        Returns:
            Исправленная формула
        """
        fixed_formula = formula
        context = context or {}
        
        # Применяем фиксы по приоритету (critical → high → medium → low)
        sorted_issues = sorted(
            issues, 
            key=lambda x: {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}.get(x.severity, 99)
        )
        
        for issue in sorted_issues:
            if not issue.auto_fixable:
                continue
            
            # Применяем соответствующий fix
            if issue.issue_type == "arrayformula_open_range":
                fixed_formula = self._fix_arrayformula_open_range(
                    fixed_formula, 
                    context
                )
            
            elif issue.issue_type == "vlookup_missing_false":
                fixed_formula = self._fix_vlookup_missing_false(fixed_formula)
            
            elif issue.issue_type == "concatenation_no_empty_check":
                fixed_formula = self._fix_concatenation_empty_check(fixed_formula)
            
            elif issue.issue_type == "date_operation_no_datevalue":
                fixed_formula = self._fix_date_operation_datevalue(fixed_formula)
            
            elif issue.issue_type == "missing_iferror":
                fixed_formula = self._fix_missing_iferror(fixed_formula)
            
            elif issue.issue_type == "if_direct_empty_comparison":
                fixed_formula = self._fix_if_empty_comparison(fixed_formula)
            
            elif issue.issue_type == "concatenation_no_trim":
                fixed_formula = self._fix_concatenation_trim(fixed_formula)
            
            elif issue.issue_type == "vlookup_no_iferror":
                fixed_formula = self._fix_vlookup_iferror(fixed_formula)

            elif issue.issue_type == "not_localized":
                fixed_formula = self._fix_localization(fixed_formula)

            elif issue.issue_type == "wrong_quote_escaping":
                fixed_formula = self._fix_quote_escaping(fixed_formula)

            elif issue.issue_type == "missing_equals":
                fixed_formula = self._fix_missing_equals(fixed_formula)

        return fixed_formula
    
    # =============================================================================
    # FIX #1: ARRAYFORMULA open range
    # =============================================================================
    
    def _fix_arrayformula_open_range(
        self, 
        formula: str, 
        context: Dict
    ) -> str:
        """
        A2:A → A2:A100
        B5:B → B5:B100
        """
        end_row = context.get('row_count', 100)
        
        # Паттерн: буква + число + : + буква БЕЗ числа
        pattern = r'([A-Z]+)(\d+):([A-Z]+)(?![0-9])'
        
        def replacer(match):
            col1, row1, col2 = match.groups()
            return f"{col1}{row1}:{col2}{end_row}"
        
        fixed = re.sub(pattern, replacer, formula)
        return fixed
    
    # =============================================================================
    # FIX #2: VLOOKUP missing FALSE
    # =============================================================================
    
    def _fix_vlookup_missing_false(self, formula: str) -> str:
        """
        VLOOKUP(A2,B:C,2) → VLOOKUP(A2,B:C,2,FALSE)
        """
        # Находим все VLOOKUP
        pattern = r'(VLOOKUP\s*\([^)]+)\)'
        
        def replacer(match):
            vlookup_content = match.group(1)
            
            # Проверяем есть ли уже FALSE
            if 'FALSE' in vlookup_content.upper() or re.search(r',\s*0\s*$', vlookup_content):
                return match.group(0)  # уже есть, не трогаем
            
            # Добавляем FALSE
            return vlookup_content + ',FALSE)'
        
        fixed = re.sub(pattern, replacer, formula, flags=re.IGNORECASE)
        return fixed
    
    # =============================================================================
    # FIX #3: Concatenation empty check
    # =============================================================================
    
    def _fix_concatenation_empty_check(self, formula: str) -> str:
        """
        A2&" "&B2 → IF(LEN(A2)=0,"",A2&" "&B2)
        
        Это сложный fix, делаем упрощенную версию
        """
        # Если формула начинается с = и сразу идет конкатенация
        if formula.startswith('=') and '&' in formula and 'IF' not in formula.upper():
            # Простой wrap: оборачиваем всю формулу
            inner = formula[1:]  # убираем =
            
            # Находим первую ячейку
            first_cell_match = re.search(r'([A-Z]+\d+)', inner)
            if first_cell_match:
                first_cell = first_cell_match.group(1)
                fixed = f'=IF(LEN({first_cell})=0,"",{inner})'
                return fixed
        
        return formula
    
    # =============================================================================
    # FIX #4: Date operation DATEVALUE
    # =============================================================================
    
    def _fix_date_operation_datevalue(self, formula: str) -> str:
        """
        TODAY()-A2 → TODAY()-DATEVALUE(A2)
        """
        # Паттерн: TODAY() или NOW() минус/плюс ячейка
        pattern = r'(TODAY|NOW)\(\)\s*([-+])\s*([A-Z]+\d+)'
        
        def replacer(match):
            func, operator, cell = match.groups()
            return f'{func}(){operator}DATEVALUE({cell})'
        
        fixed = re.sub(pattern, replacer, formula, flags=re.IGNORECASE)
        return fixed
    
    # =============================================================================
    # FIX #5: Missing IFERROR
    # =============================================================================
    
    def _fix_missing_iferror(self, formula: str) -> str:
        """
        VLOOKUP(...) → IFERROR(VLOOKUP(...),"")
        """
        if 'IFERROR' in formula.upper():
            return formula  # уже есть
        
        # Оборачиваем всю формулу
        inner = formula[1:] if formula.startswith('=') else formula
        fixed = f'=IFERROR({inner},"")'
        return fixed
    
    # =============================================================================
    # FIX #6: IF empty comparison
    # =============================================================================
    
    def _fix_if_empty_comparison(self, formula: str) -> str:
        """
        IF(A2="",...) → IF(LEN(A2)=0,...)
        """
        # Паттерн: ячейка = пустая строка
        pattern = r'([A-Z]+\d+)\s*=\s*["\']["\']'
        
        def replacer(match):
            cell = match.group(1)
            return f'LEN({cell})=0'
        
        fixed = re.sub(pattern, replacer, formula)
        return fixed
    
    # =============================================================================
    # FIX #7: Concatenation TRIM
    # =============================================================================
    
    def _fix_concatenation_trim(self, formula: str) -> str:
        """
        =A2&" "&B2 → =TRIM(A2&" "&B2)
        """
        if 'TRIM' in formula.upper():
            return formula  # уже есть
        
        if '&' in formula:
            inner = formula[1:] if formula.startswith('=') else formula
            fixed = f'=TRIM({inner})'
            return fixed
        
        return formula
    
    # =============================================================================
    # FIX #8: VLOOKUP IFERROR
    # =============================================================================
    
    def _fix_vlookup_iferror(self, formula: str) -> str:
        """
        VLOOKUP(...) → IFERROR(VLOOKUP(...),"Не найдено")
        """
        if 'IFERROR' in formula.upper():
            return formula

        # Находим VLOOKUP и оборачиваем
        pattern = r'(VLOOKUP\s*\([^)]+\))'

        def replacer(match):
            vlookup = match.group(1)
            return f'IFERROR({vlookup},"Не найдено")'

        fixed = re.sub(pattern, replacer, formula, flags=re.IGNORECASE)
        return fixed

    # =============================================================================
    # FIX #9: Локализация функций для русской версии Google Sheets
    # =============================================================================

    def _fix_localization(self, formula: str) -> str:
        """
        DEPRECATED: Локализация отключена.

        Google Sheets автоматически переводит английские формулы на язык интерфейса,
        поэтому мы используем только АНГЛИЙСКИЕ названия функций (SUM, AVERAGE, IF, etc.)
        """
        # Локализация отключена - Google Sheets сам переводит формулы
        return formula

    # =============================================================================
    # FIX #10: Quote Escaping (PHASE 1.1 - критичный фикс)
    # =============================================================================

    def _fix_quote_escaping(self, formula: str) -> str:
        """
        Заменяет backslash-кавычки на двойные кавычки.
        Google Sheets использует двойные кавычки для экранирования.
        """
        # Заменяем \" на ""
        # Сначала убираем backslash
        fixed = formula.replace('\\"', '""')
        fixed = fixed.replace(r'\"', '""')

        return fixed

    # =============================================================================
    # FIX #11: Missing Equals (PHASE 1.2 - критичный фикс)
    # =============================================================================

    def _fix_missing_equals(self, formula: str) -> str:
        """
        Добавляет = в начало формулы если его нет.
        """
        formula = formula.strip()
        if not formula.startswith('='):
            return '=' + formula
        return formula