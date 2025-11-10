"""
Мастер запросов к шаблонам формул.
Анализирует запрос пользователя и находит подходящий template.
"""

from typing import Optional, List, Dict, Tuple
import re
from .formula_templates import get_all_templates, FormulaTemplate


class TemplateMatcher:
    """Находит подходящий шаблон для запроса"""
    
    def __init__(self):
        self.templates = get_all_templates()
    
    def find_template(self, query: str, columns: List[str]) -> Optional[Tuple[FormulaTemplate, Dict]]:
        """
        Находит подходящий шаблон и извлекает параметры
        
        Args:
            query: Запрос пользователя
            columns: Список названий столбцов
            
        Returns:
            (template, params) или None если не найдено
        """
        query_lower = query.lower()
        
        # Проходим по всем шаблонам и считаем score
        best_match = None
        best_score = 0
        
        for template in self.templates.values():
            score = self._calculate_match_score(query_lower, template)
            
            if score > best_score and score >= 2:  # минимум 2 совпадения
                best_score = score
                best_match = template
        
        if not best_match:
            return None
        
        # Извлекаем параметры из запроса и данных
        params = self._extract_parameters(query, best_match, columns)
        
        if not params:
            return None
        
        return (best_match, params)
    
    def _calculate_match_score(self, query: str, template: FormulaTemplate) -> int:
        """Считает насколько запрос соответствует шаблону"""
        score = 0

        # Проверяем каждое ключевое слово
        for keyword in template.keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in query:
                # Даем больше баллов за точное совпадение фразы
                if ' ' in keyword_lower:
                    score += 2  # Фраза из нескольких слов
                else:
                    score += 1  # Одно слово

        return score
    
    def _extract_parameters(
        self, 
        query: str, 
        template: FormulaTemplate,
        columns: List[str]
    ) -> Optional[Dict]:
        """Извлекает параметры для шаблона"""
        
        params = {}
        
        # Определяем какой столбец упоминается в запросе
        mentioned_column = self._find_mentioned_column(query, columns)
        
        # В зависимости от требуемых параметров
        if "column" in template.requires_params:
            if mentioned_column:
                params["column"] = mentioned_column
            else:
                # Если не упомянут - берем первый числовой столбец (для math операций)
                params["column"] = self._guess_numeric_column(columns)
        
        if "col1" in template.requires_params:
            # Для ФИО - ищем "Фамилия", "Имя", "Отчество"
            params["col1"] = self._find_column_by_pattern(columns, ["фамилия", "surname", "lastname"])
            params["col2"] = self._find_column_by_pattern(columns, ["имя", "name", "firstname"])
            params["col3"] = self._find_column_by_pattern(columns, ["отчество", "middlename", "patronymic"])
            
            if not all([params["col1"], params["col2"], params["col3"]]):
                return None
        
        if "separator" in template.requires_params:
            # Ищем разделитель в запросе
            if "запятой" in query.lower() or "запятую" in query.lower():
                params["separator"] = ", "
            elif "дефис" in query.lower() or "через дефис" in query.lower():
                params["separator"] = " - "
            else:
                params["separator"] = " "  # по умолчанию пробел
        
        # Для VLOOKUP
        if "lookup_cell" in template.requires_params:
            # Упрощенно - берем первую ячейку первого столбца
            params["lookup_cell"] = "A2"
            params["table_range"] = "Sheet2!A:B"  # TODO: нужно улучшить
            params["column_index"] = 2
        
        # Для IF
        if "operator" in template.requires_params:
            params["operator"] = self._extract_operator(query)
            params["value"] = self._extract_value(query)
            params["true_text"] = self._extract_true_text(query)
            params["false_text"] = self._extract_false_text(query)
            params["cell"] = mentioned_column + "2" if mentioned_column else "A2"
        
        # Для SUMIF/COUNTIF
        if "criteria" in template.requires_params:
            params["criteria"] = self._extract_criteria(query, columns)
            params["criteria_range"] = self._find_criteria_column(query, columns) + ":" + self._find_criteria_column(query, columns)
            if "sum_range" in template.requires_params:
                params["sum_range"] = (mentioned_column or self._guess_numeric_column(columns)) + ":" + (mentioned_column or self._guess_numeric_column(columns))
            else:
                params["range"] = (mentioned_column or columns[0]) + ":" + (mentioned_column or columns[0])
        
        # Для дат
        if "date1" in template.requires_params:
            date_cols = self._find_date_columns(columns)
            if len(date_cols) >= 2:
                params["date1"] = date_cols[0] + "2"
                params["date2"] = date_cols[1] + "2"
            else:
                return None
        
        # Для финансовых
        if "revenue_col" in template.requires_params:
            params["revenue_col"] = self._find_column_by_pattern(columns, ["доход", "выручка", "продажи", "revenue", "sales"]) + "2"
            params["expense_col"] = self._find_column_by_pattern(columns, ["расход", "затраты", "expense", "cost"]) + "2"
            
            if not params["revenue_col"] or not params["expense_col"]:
                return None
        
        # Для процентов
        if "part_col" in template.requires_params:
            params["part_col"] = mentioned_column + "2" if mentioned_column else "A2"
            params["total_col"] = self._find_column_by_pattern(columns, ["итого", "всего", "total", "план"]) + "2"
        
        if "new_value" in template.requires_params:
            params["new_value"] = mentioned_column + "3" if mentioned_column else "B3"  # текущая строка
            params["old_value"] = mentioned_column + "2" if mentioned_column else "B2"  # предыдущая строка
        
        # Для округления
        if "decimals" in template.requires_params:
            if "целого" in query.lower() or "без копеек" in query.lower():
                params["decimals"] = 0
            else:
                params["decimals"] = 2  # по умолчанию
            params["cell"] = mentioned_column + "2" if mentioned_column else "A2"
        
        # Для UNIQUE и SORT
        if "range" in template.requires_params and template.id in ["unique_values", "sort_data"]:
            col = mentioned_column or columns[0]
            params["range"] = f"{col}:{col}"
            
            if template.id == "sort_data":
                params["column"] = 1
                params["ascending"] = "возрастанию" in query.lower() or "меньшего" in query.lower()
        
        return params if params else None
    
    def _find_mentioned_column(self, query: str, columns: List[str]) -> Optional[str]:
        """Находит упомянутый в запросе столбец"""
        query_lower = query.lower()
        
        # Сначала ищем прямое упоминание буквы столбца
        column_match = re.search(r'\b([A-Z])\b', query)
        if column_match:
            return column_match.group(1)
        
        # Ищем упоминание названия столбца
        for i, col_name in enumerate(columns):
            if col_name.lower() in query_lower:
                return chr(65 + i)  # A=65, B=66, etc
        
        return None
    
    def _find_column_by_pattern(self, columns: List[str], patterns: List[str]) -> Optional[str]:
        """Находит столбец по паттернам в названии"""
        for i, col_name in enumerate(columns):
            col_lower = col_name.lower()
            for pattern in patterns:
                if pattern in col_lower:
                    return chr(65 + i)
        return None
    
    def _guess_numeric_column(self, columns: List[str]) -> str:
        """Угадывает числовой столбец (для math операций)"""
        # Ищем столбцы с типичными названиями для чисел
        numeric_keywords = ["цена", "сумма", "количество", "продажи", "price", "amount", "sales", "cost"]
        
        for i, col_name in enumerate(columns):
            col_lower = col_name.lower()
            if any(kw in col_lower for kw in numeric_keywords):
                return chr(65 + i)
        
        # Если не нашли - берем второй столбец (обычно первый - это названия)
        return "B" if len(columns) > 1 else "A"
    
    def _find_date_columns(self, columns: List[str]) -> List[str]:
        """Находит столбцы с датами"""
        date_keywords = ["дата", "date", "срок", "период", "месяц", "год"]
        date_cols = []
        
        for i, col_name in enumerate(columns):
            col_lower = col_name.lower()
            if any(kw in col_lower for kw in date_keywords):
                date_cols.append(chr(65 + i))
        
        return date_cols
    
    def _find_criteria_column(self, query: str, columns: List[str]) -> str:
        """Находит столбец для условия"""
        # Ищем "по [столбцу]", "где [столбец]", etc
        for i, col_name in enumerate(columns):
            if col_name.lower() in query.lower():
                return chr(65 + i)
        
        # По умолчанию - последний столбец (часто там категории)
        return chr(65 + len(columns) - 1)
    
    def _extract_criteria(self, query: str, columns: List[str]) -> str:
        """Извлекает критерий из запроса"""
        # Ищем значение после "где", "если", "только", "по"
        patterns = [
            r'где\s+([^\s,]+)',
            r'если\s+([^\s,]+)',
            r'только\s+([^\s,]+)',
            r'по\s+([^\s,]+)',
            r'категории\s+([^\s,]+)',
            r'статусом\s+["\']([^"\']+)["\']'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query.lower())
            if match:
                return match.group(1)
        
        return "критерий"  # placeholder
    
    def _extract_operator(self, query: str) -> str:
        """Извлекает оператор сравнения"""
        if any(kw in query.lower() for kw in ["больше", "выше", ">"]):
            return ">"
        elif any(kw in query.lower() for kw in ["меньше", "ниже", "<"]):
            return "<"
        elif any(kw in query.lower() for kw in ["равно", "равен", "="]):
            return "="
        elif any(kw in query.lower() for kw in ["не равно", "не равен", "!="]):
            return "<>"
        else:
            return ">"
    
    def _extract_value(self, query: str) -> str:
        """Извлекает значение для сравнения"""
        # Ищем число в запросе
        match = re.search(r'\d+', query)
        if match:
            return match.group(0)
        return "1000"  # default
    
    def _extract_true_text(self, query: str) -> str:
        """Извлекает текст для true условия"""
        patterns = [
            r'то\s+["\']([^"\']+)["\']',
            r'то\s+(\w+)',
            r'пиши\s+["\']([^"\']+)["\']'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query.lower())
            if match:
                return match.group(1)
        
        return "Да"
    
    def _extract_false_text(self, query: str) -> str:
        """Извлекает текст для false условия"""
        patterns = [
            r'иначе\s+["\']([^"\']+)["\']',
            r'иначе\s+(\w+)',
            r'else\s+["\']([^"\']+)["\']'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query.lower())
            if match:
                return match.group(1)
        
        return "Нет"