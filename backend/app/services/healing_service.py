"""
Healing Service - регенерирует формулы когда они не работают
"""

import logging
from typing import Dict, Optional, Any
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class HealingService:
    """
    Сервис для "лечения" сломанных формул
    
    Когда формула не работает (даже после validator + fixer),
    этот сервис пытается её переделать с учетом ошибки.
    """
    
    def __init__(self, openai_client: AsyncOpenAI):
        self.openai_client = openai_client
    
    async def heal_formula(
        self,
        original_formula: str,
        error_info: Dict[str, Any],
        context: Dict[str, Any],
        attempt: int = 1
    ) -> Optional[str]:
        """
        Пытается "вылечить" формулу которая не работает
        
        Args:
            original_formula: Оригинальная формула которая не сработала
            error_info: Информация об ошибке:
                {
                    "error_type": "#N/A" | "#VALUE!" | etc,
                    "error_message": "...",
                    "result_preview": [...]
                }
            context: Контекст запроса (query, columns, etc)
            attempt: Номер попытки (1, 2, 3...)
            
        Returns:
            Новая формула или None если не удалось
        """
        
        logger.info(f"🔧 Healing attempt #{attempt} for formula: {original_formula}")
        logger.info(f"   Error: {error_info.get('error_type')} - {error_info.get('error_message')}")
        
        # ===== Определяем стратегию healing =====
        
        error_type = error_info.get("error_type", "")
        
        if error_type == "#N/A":
            # VLOOKUP не нашел значение
            strategy = "vlookup_not_found"
        elif error_type == "#VALUE!":
            # Неправильный тип данных
            strategy = "wrong_data_type"
        elif error_type == "#NAME?":
            # Неизвестная функция или имя
            strategy = "unknown_name"
        elif error_type == "#REF!":
            # Неправильная ссылка
            strategy = "invalid_reference"
        elif error_type == "#DIV/0!":
            # Деление на ноль
            strategy = "division_by_zero"
        else:
            # Общая стратегия
            strategy = "general"
        
        # ===== Применяем стратегию =====
        
        healed_formula = await self._apply_healing_strategy(
            original_formula,
            error_info,
            context,
            strategy
        )
        
        return healed_formula
    
    async def _apply_healing_strategy(
        self,
        formula: str,
        error_info: Dict,
        context: Dict,
        strategy: str
    ) -> Optional[str]:
        """
        Применяет конкретную стратегию healing
        """
        
        if strategy == "vlookup_not_found":
            return await self._heal_vlookup(formula, error_info, context)
        
        elif strategy == "wrong_data_type":
            return await self._heal_data_type(formula, error_info, context)
        
        elif strategy == "unknown_name":
            return await self._heal_unknown_name(formula, error_info, context)
        
        elif strategy == "invalid_reference":
            return await self._heal_invalid_ref(formula, error_info, context)
        
        else:
            # Общая стратегия - просим GPT придумать альтернативу
            return await self._heal_with_gpt(formula, error_info, context)
    
    # =========================================================================
    # СПЕЦИФИЧНЫЕ СТРАТЕГИИ
    # =========================================================================
    
    async def _heal_vlookup(
        self,
        formula: str,
        error_info: Dict,
        context: Dict
    ) -> Optional[str]:
        """
        Healing для VLOOKUP #N/A ошибки
        
        Возможные проблемы:
        1. Lookup value не существует в таблице
        2. Неправильный диапазон поиска
        3. Неправильный номер столбца
        """
        
        # Простое решение - уже должен быть IFERROR
        # Но если его нет - добавляем
        if "IFERROR" not in formula:
            healed = f'IFERROR({formula}, "")'
            logger.info(f"✅ Healed VLOOKUP by adding IFERROR")
            return healed
        
        # Если IFERROR уже есть - просим GPT найти другое решение
        return await self._heal_with_gpt(formula, error_info, context)
    
    async def _heal_data_type(
        self,
        formula: str,
        error_info: Dict,
        context: Dict
    ) -> Optional[str]:
        """
        Healing для #VALUE! ошибки (неправильный тип данных)
        
        Обычно это:
        1. Даты как текст
        2. Числа как текст
        3. Пустые ячейки в математических операциях
        """
        
        # Если работаем с датами - добавляем DATEVALUE
        if "TODAY" in formula or "NOW" in formula:
            # Находим ячейку с датой и оборачиваем в DATEVALUE
            import re
            
            # Паттерн: операция с ячейкой
            pattern = r'(TODAY\(\)|NOW\(\))\s*([-+])\s*([A-Z]+\d+)'
            match = re.search(pattern, formula)
            
            if match:
                func, operator, cell = match.groups()
                
                # Проверяем нет ли уже DATEVALUE
                if f"DATEVALUE({cell})" not in formula:
                    healed = formula.replace(
                        f"{func}{operator}{cell}",
                        f"{func}{operator}DATEVALUE({cell})"
                    )
                    logger.info(f"✅ Healed by adding DATEVALUE")
                    return healed
        
        # Если это не даты - просим GPT
        return await self._heal_with_gpt(formula, error_info, context)
    
    async def _heal_unknown_name(
        self,
        formula: str,
        error_info: Dict,
        context: Dict
    ) -> Optional[str]:
        """
        Healing для #NAME? ошибки (неизвестная функция)
        
        Обычно это:
        1. Опечатка в имени функции
        2. Кириллица в имени диапазона
        """
        
        # Проверяем на кириллицу
        import re
        if re.search(r'[А-Яа-я]', formula):
            logger.warning("⚠️ Formula contains Cyrillic - cannot auto-heal")
            # Это требует column mapping - возвращаем None
            return None
        
        # Иначе - просим GPT исправить опечатку
        return await self._heal_with_gpt(formula, error_info, context)
    
    async def _heal_invalid_ref(
        self,
        formula: str,
        error_info: Dict,
        context: Dict
    ) -> Optional[str]:
        """
        Healing для #REF! ошибки (неправильная ссылка на ячейку)
        """
        
        # Это сложная ошибка - обычно неправильный column reference
        # Просим GPT переделать
        return await self._heal_with_gpt(formula, error_info, context)
    
    # =========================================================================
    # ОБЩАЯ GPT СТРАТЕГИЯ
    # =========================================================================
    
    async def _heal_with_gpt(
        self,
        formula: str,
        error_info: Dict,
        context: Dict
    ) -> Optional[str]:
        """
        Универсальная стратегия - просим GPT создать альтернативу
        """
        
        prompt = self._build_healing_prompt(formula, error_info, context)
        
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a Google Sheets formula expert. Fix broken formulas."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # чуть выше чем обычно для creativity
                max_tokens=500
            )
            
            content = response.choices[0].message.content.strip()
            
            # Извлекаем формулу из ответа
            healed_formula = self._extract_formula_from_response(content)
            
            if healed_formula and healed_formula != formula:
                logger.info(f"✅ GPT healed formula: {healed_formula}")
                return healed_formula
            else:
                logger.warning("⚠️ GPT didn't provide a different formula")
                return None
            
        except Exception as e:
            logger.error(f"❌ Error in GPT healing: {e}")
            return None
    
    def _build_healing_prompt(
        self,
        formula: str,
        error_info: Dict,
        context: Dict
    ) -> str:
        """
        Строит промпт для GPT healing
        """
        
        error_type = error_info.get("error_type", "unknown")
        error_message = error_info.get("error_message", "")
        
        columns = context.get("columns", [])
        query = context.get("query", "")
        
        prompt = f"""A Google Sheets formula is not working. Help fix it.

ORIGINAL QUERY: "{query}"

FAILED FORMULA: {formula}

ERROR: {error_type}
ERROR MESSAGE: {error_message}

AVAILABLE COLUMNS: {", ".join(columns)}

Please provide an ALTERNATIVE formula that will work.
Consider:
1. Different approach to solve the same problem
2. Simpler formula if possible
3. Handle edge cases (empty cells, wrong data types)

Output ONLY the new formula, starting with =
Do NOT explain, just the formula."""
        
        return prompt
    
    def _extract_formula_from_response(self, response: str) -> Optional[str]:
        """
        Извлекает формулу из ответа GPT
        """
        lines = response.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith('='):
                return line
        
        # Если не нашли строку с = - может быть в markdown
        if '`' in response:
            import re
            match = re.search(r'`(=.+?)`', response)
            if match:
                return match.group(1)
        
        return None