"""
Fuzzy column name matching для повышения success rate
"""

from difflib import SequenceMatcher
from typing import List, Optional, Dict
import re


def find_best_column_match(
    requested_column: str,
    available_columns: List[str],
    threshold: float = 0.6
) -> Optional[str]:
    """
    Находит лучшее совпадение для requested_column среди available_columns

    Стратегия (по приоритету):
    1. Точное совпадение (case-insensitive)
    2. Fuzzy match (SequenceMatcher) с порогом 0.6
    3. Substring match (содержит или содержится)
    4. Synonym match (продажи/сумма/заказы)
    5. None (не найдено)

    Args:
        requested_column: Название колонки которую ищем
        available_columns: Список доступных колонок
        threshold: Минимальный порог для fuzzy match (0.0-1.0)

    Returns:
        Лучшее совпадение или None
    """
    if not requested_column or not available_columns:
        return None

    requested_lower = requested_column.lower().strip()
    available_lower = {col: col.lower().strip() for col in available_columns}

    # 1️⃣ Точное совпадение (case-insensitive)
    for col, col_lower in available_lower.items():
        if requested_lower == col_lower:
            return col

    # 2️⃣ Fuzzy match (SequenceMatcher)
    best_match = None
    best_score = 0.0

    for col, col_lower in available_lower.items():
        score = SequenceMatcher(None, requested_lower, col_lower).ratio()
        if score > best_score:
            best_score = score
            best_match = col

    if best_score >= threshold:
        return best_match

    # 3️⃣ Substring match (содержит или содержится)
    for col, col_lower in available_lower.items():
        if requested_lower in col_lower or col_lower in requested_lower:
            return col

    # 3.5️⃣ Partial word match (для русских падежей: "сумма" vs "сумму")
    # Проверяем первые 4 символа каждого слова
    requested_words = requested_lower.split()
    for col, col_lower in available_lower.items():
        col_words = col_lower.split()
        for req_word in requested_words:
            if len(req_word) >= 4:  # Минимум 4 символа для надежности
                req_stem = req_word[:4]
                for col_word in col_words:
                    if col_word.startswith(req_stem):
                        return col

    # 4️⃣ Synonym match (русские синонимы для общих столбцов)
    synonyms = get_column_synonyms()
    requested_synonyms = synonyms.get(requested_lower, [requested_lower])

    for col, col_lower in available_lower.items():
        # Проверяем каждый синоним на вхождение в название колонки
        for req_syn in requested_synonyms:
            # Проверка вхождения синонима как подстроки
            if req_syn in col_lower:
                return col
            # Проверка вхождения синонима как отдельного слова
            col_words = col_lower.split()
            for col_word in col_words:
                # Проверка на первые 4 символа (для падежей)
                if len(col_word) >= 4 and len(req_syn) >= 4:
                    if col_word.startswith(req_syn[:4]):
                        return col

    # 5️⃣ Не найдено
    return None


def get_column_synonyms() -> Dict[str, List[str]]:
    """
    Возвращает словарь синонимов для общих столбцов
    """
    return {
        # Продажи
        "продажи": ["продажи", "сумма", "выручка", "заказ", "заказы", "продажа", "revenue", "sales"],
        "сумма": ["сумма", "продажи", "выручка", "заказ", "total", "amount"],
        "выручка": ["выручка", "продажи", "сумма", "revenue"],
        "заказ": ["заказ", "заказы", "продажи", "сумма", "order", "orders"],

        # Даты
        "дата": ["дата", "день", "date", "время", "time"],
        "день": ["день", "дата", "date"],

        # Персоны
        "менеджер": ["менеджер", "продавец", "сотрудник", "manager", "employee"],
        "клиент": ["клиент", "покупатель", "заказчик", "customer", "client"],
        "сотрудник": ["сотрудник", "работник", "менеджер", "employee"],

        # Продукты
        "продукт": ["продукт", "товар", "item", "product"],
        "товар": ["товар", "продукт", "item", "product"],

        # Метрики
        "количество": ["количество", "кол-во", "кол", "count", "qty", "quantity"],
        "цена": ["цена", "стоимость", "price", "cost"],
        "скидка": ["скидка", "discount"],

        # Статусы
        "статус": ["статус", "состояние", "status", "state"],
        "категория": ["категория", "тип", "вид", "category", "type"],
    }


def get_similar_columns(
    requested_column: str,
    available_columns: List[str],
    top_n: int = 3
) -> List[Dict[str, float]]:
    """
    Возвращает топ N наиболее похожих колонок с их score

    Используется для подсказок пользователю когда колонка не найдена

    Returns:
        [{"column": "Продажи", "score": 0.85}, ...]
    """
    if not requested_column or not available_columns:
        return []

    requested_lower = requested_column.lower().strip()

    scores = []
    for col in available_columns:
        col_lower = col.lower().strip()
        score = SequenceMatcher(None, requested_lower, col_lower).ratio()
        scores.append({"column": col, "score": score})

    # Сортируем по убыванию score
    scores.sort(key=lambda x: x["score"], reverse=True)

    return scores[:top_n]


def normalize_column_name(column_name: str) -> str:
    """
    Нормализует название колонки для сравнения
    - Убирает лишние пробелы
    - Приводит к lowercase
    - Убирает спецсимволы
    """
    if not column_name:
        return ""

    # Убираем спецсимволы (оставляем буквы, цифры, пробелы, дефисы)
    normalized = re.sub(r'[^\w\s\-]', '', column_name, flags=re.UNICODE)

    # Убираем множественные пробелы
    normalized = ' '.join(normalized.split())

    # Lowercase
    normalized = normalized.lower().strip()

    return normalized


# Примеры использования для тестов
if __name__ == "__main__":
    # Тест 1: Точное совпадение
    available = ["Менеджер", "Продажи", "Дата"]
    assert find_best_column_match("продажи", available) == "Продажи"
    print("✅ Test 1 passed: Exact match")

    # Тест 2: Fuzzy match
    assert find_best_column_match("Продаж", available) == "Продажи"
    print("✅ Test 2 passed: Fuzzy match")

    # Тест 3: Substring match
    available2 = ["Менеджер по продажам", "Сумма заказов", "Дата создания"]
    assert find_best_column_match("Сумма", available2) == "Сумма заказов"
    print("✅ Test 3 passed: Substring match")

    # Тест 4: Synonym match
    assert find_best_column_match("Выручка", available) == "Продажи"
    print("✅ Test 4 passed: Synonym match")

    # Тест 5: Not found
    assert find_best_column_match("Несуществующая колонка", available) is None
    print("✅ Test 5 passed: Not found")

    # Тест 6: Similar columns
    similar = get_similar_columns("Продаж", available, top_n=2)
    print(f"✅ Test 6 passed: Similar columns: {similar}")

    print("\n🎉 All tests passed!")
