"""
Formula Executor - вставляет формулы в Google Sheets и проверяет результат
"""

import asyncio
import logging
from typing import Dict, Optional, List, Any

# Google API импорты (опциональные для тестовых сред)
try:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False
    Credentials = None

logger = logging.getLogger(__name__)


class FormulaExecutionResult:
    """Результат выполнения формулы"""
    
    def __init__(
        self,
        success: bool,
        formula: str,
        cell: str,
        error: Optional[str] = None,
        result_preview: Optional[List] = None,
        error_type: Optional[str] = None
    ):
        self.success = success
        self.formula = formula
        self.cell = cell
        self.error = error
        self.result_preview = result_preview
        self.error_type = error_type


class FormulaExecutor:
    """
    Выполняет формулы в Google Sheets и проверяет результат
    """
    
    def __init__(self, credentials: Credentials):
        """
        Args:
            credentials: Google OAuth2 credentials
        """
        self.credentials = credentials
        self.sheets_service = None
    
    def _get_sheets_service(self):
        """Ленивая инициализация Sheets API"""
        if not self.sheets_service:
            self.sheets_service = build('sheets', 'v4', credentials=self.credentials)
        return self.sheets_service
    
    async def execute_and_verify(
        self,
        spreadsheet_id: str,
        cell: str,
        formula: str,
        verify_rows: int = 5
    ) -> FormulaExecutionResult:
        """
        Вставляет формулу и проверяет результат
        
        Args:
            spreadsheet_id: ID таблицы
            cell: Целевая ячейка (например "D1")
            formula: Формула для вставки
            verify_rows: Сколько строк проверить на ошибки
            
        Returns:
            FormulaExecutionResult
        """
        
        try:
            # ===== ШАГ 1: Вставляем формулу =====
            
            logger.info(f"📝 Inserting formula into {cell}: {formula}")
            
            await self._insert_formula(spreadsheet_id, cell, formula)
            
            # ===== ШАГ 2: Ждем пока Sheet вычислит =====
            
            # Google Sheets вычисляет формулы асинхронно
            # Даем время на вычисление (обычно < 1 секунды)
            await asyncio.sleep(1)
            
            # ===== ШАГ 3: Читаем результат =====
            
            result_values = await self._read_result(
                spreadsheet_id,
                cell,
                verify_rows
            )
            
            logger.info(f"📊 Result preview: {result_values[:3]}")
            
            # ===== ШАГ 4: Проверяем на ошибки =====
            
            error_check = self._check_for_errors(result_values)
            
            if error_check["has_error"]:
                logger.warning(f"⚠️ Formula error detected: {error_check['error_type']}")
                
                return FormulaExecutionResult(
                    success=False,
                    formula=formula,
                    cell=cell,
                    error=error_check["error_message"],
                    error_type=error_check["error_type"],
                    result_preview=result_values
                )
            
            # ===== ШАГ 5: Все ОК! =====
            
            logger.info(f"✅ Formula executed successfully")
            
            return FormulaExecutionResult(
                success=True,
                formula=formula,
                cell=cell,
                result_preview=result_values
            )
            
        except Exception as e:
            logger.error(f"❌ Error executing formula: {e}", exc_info=True)
            
            return FormulaExecutionResult(
                success=False,
                formula=formula,
                cell=cell,
                error=str(e),
                error_type="EXECUTION_ERROR"
            )
    
    async def _insert_formula(
        self,
        spreadsheet_id: str,
        cell: str,
        formula: str
    ):
        """
        Вставляет формулу в ячейку
        """
        service = self._get_sheets_service()
        
        # Формируем тело запроса
        body = {
            'values': [[formula]]
        }
        
        # Вставляем формулу
        # valueInputOption='USER_ENTERED' - чтобы формула вычислилась
        result = service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=cell,
            valueInputOption='USER_ENTERED',
            body=body
        ).execute()
        
        logger.debug(f"Insert result: {result}")
    
    async def _read_result(
        self,
        spreadsheet_id: str,
        cell: str,
        num_rows: int
    ) -> List[Any]:
        """
        Читает результат формулы
        
        Args:
            cell: Начальная ячейка (например "D1")
            num_rows: Сколько строк прочитать
        """
        service = self._get_sheets_service()
        
        # Определяем диапазон для чтения
        # Если cell = "D1", читаем D1:D{num_rows}
        column = ''.join(filter(str.isalpha, cell))
        start_row = int(''.join(filter(str.isdigit, cell)))
        end_row = start_row + num_rows - 1
        
        range_to_read = f"{column}{start_row}:{column}{end_row}"
        
        logger.debug(f"Reading range: {range_to_read}")
        
        # Читаем значения
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_to_read,
            valueRenderOption='FORMATTED_VALUE'  # Получаем форматированные значения
        ).execute()
        
        values = result.get('values', [])
        
        # Flatten list of lists
        flattened = []
        for row in values:
            if row:
                flattened.append(row[0] if len(row) > 0 else "")
            else:
                flattened.append("")
        
        return flattened
    
    def _check_for_errors(self, values: List[Any]) -> Dict[str, Any]:
        """
        Проверяет результаты на наличие ошибок Google Sheets
        
        Типы ошибок:
        - #ERROR! - общая ошибка
        - #N/A - значение не найдено (VLOOKUP)
        - #VALUE! - неправильный тип данных
        - #REF! - неправильная ссылка
        - #NAME? - неизвестная функция/имя
        - #DIV/0! - деление на ноль
        - #NUM! - неправильное числовое значение
        """
        
        error_types = [
            "#ERROR!", "#N/A", "#VALUE!", "#REF!", 
            "#NAME?", "#DIV/0!", "#NUM!", "#NULL!"
        ]
        
        for value in values:
            value_str = str(value).upper()
            
            for error_type in error_types:
                if error_type in value_str:
                    return {
                        "has_error": True,
                        "error_type": error_type,
                        "error_message": f"Formula produced {error_type} error",
                        "error_value": value
                    }
        
        # Проверка на пустые результаты (может быть проблемой)
        non_empty = [v for v in values if v and str(v).strip()]
        
        if len(non_empty) == 0:
            # Все пустое - возможно формула не сработала
            logger.warning("⚠️ All results are empty")
            # Но это не всегда ошибка, так что не фейлим
        
        return {
            "has_error": False,
            "error_type": None,
            "error_message": None
        }


# =============================================================================
# MOCK EXECUTOR (для разработки без Google API)
# =============================================================================

class MockFormulaExecutor(FormulaExecutor):
    """
    Mock версия для тестирования без реального Google Sheets
    """
    
    def __init__(self):
        # Не вызываем super().__init__() чтобы не требовать credentials
        self.mock_errors = {}  # dict для задания тестовых ошибок
    
    def set_mock_error(self, formula_pattern: str, error_type: str):
        """
        Задает mock ошибку для тестирования
        
        Example:
            executor.set_mock_error("VLOOKUP", "#N/A")
        """
        self.mock_errors[formula_pattern] = error_type
    
    async def _insert_formula(self, spreadsheet_id: str, cell: str, formula: str):
        """Mock вставка"""
        logger.info(f"[MOCK] Inserting formula: {formula}")
        await asyncio.sleep(0.1)  # симулируем задержку
    
    async def _read_result(
        self,
        spreadsheet_id: str,
        cell: str,
        num_rows: int
    ) -> List[Any]:
        """Mock чтение результата"""
        
        # Проверяем есть ли mock ошибка для этой формулы
        formula = getattr(self, '_last_formula', '')
        
        for pattern, error_type in self.mock_errors.items():
            if pattern in formula:
                return [error_type] * num_rows
        
        # Генерируем fake успешные результаты
        if "SUM" in formula:
            return ["1500", "0", "0", "0", "0"]
        elif "&" in formula:  # concatenation
            return ["Иванов Иван Иванович", "Петров Петр Петрович", "", "", ""]
        else:
            return ["Result 1", "Result 2", "Result 3", "", ""]
    
    async def execute_and_verify(
        self,
        spreadsheet_id: str,
        cell: str,
        formula: str,
        verify_rows: int = 5
    ) -> FormulaExecutionResult:
        """Переопределяем чтобы сохранить formula"""
        self._last_formula = formula
        return await super().execute_and_verify(spreadsheet_id, cell, formula, verify_rows)