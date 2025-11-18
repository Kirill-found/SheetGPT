"""
Тестирование веб-поиска через DuckDuckGo
"""

import sys
sys.path.insert(0, '.')

from app.services.web_search import get_web_search_service
from app.services.ai_code_executor import get_ai_executor

def test_basic_search():
    """Тест базового поиска"""
    print("\n" + "="*80)
    print("TEST 1: Базовый поиск через DuckDuckGo")
    print("="*80)

    web_search = get_web_search_service()
    results = web_search.search("LLM модели OpenAI GPT", max_results=5)

    print(f"\n[OK] Найдено результатов: {len(results)}")
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result['title']}")
        print(f"   {result['body'][:150]}...")
        print(f"   {result['href']}")


def test_table_generation_with_search():
    """Тест генерации таблицы с веб-поиском"""
    print("\n" + "="*80)
    print("TEST 2: Генерация таблицы с веб-поиском")
    print("="*80)

    ai_executor = get_ai_executor()

    # Тестовый запрос с веб-поиском
    query = "найди в интернете информацию о последних LLM моделях и создай таблицу"

    print(f"\n[QUERY] Запрос: {query}")
    print(f"[SEARCH] Выполняется веб-поиск и генерация таблицы...\n")

    result = ai_executor._generate_table_from_knowledge(query)

    print(f"\n[OK] Результат:")
    print(f"   Summary: {result.get('summary', 'N/A')}")
    print(f"   Methodology: {result.get('methodology', 'N/A')}")
    print(f"   Confidence: {result.get('confidence', 0)}")
    print(f"   Web search used: {result.get('web_search_used', False)}")

    if 'structured_data' in result:
        data = result['structured_data']
        print(f"\n[TABLE] Таблица:")
        print(f"   Заголовки: {data.get('headers', [])}")
        print(f"   Количество строк: {len(data.get('rows', []))}")

        # Показываем первые 3 строки
        for i, row in enumerate(data.get('rows', [])[:3], 1):
            print(f"   Row {i}: {row}")


def test_table_without_search():
    """Тест генерации таблицы БЕЗ веб-поиска (только AI знания)"""
    print("\n" + "="*80)
    print("TEST 3: Генерация таблицы БЕЗ веб-поиска")
    print("="*80)

    ai_executor = get_ai_executor()

    query = "создай таблицу со странами Европы"

    print(f"\n[QUERY] Запрос: {query}")
    print(f"[AI] Генерация таблицы из знаний AI...\n")

    result = ai_executor._generate_table_from_knowledge(query)

    print(f"\n[OK] Результат:")
    print(f"   Summary: {result.get('summary', 'N/A')}")
    print(f"   Methodology: {result.get('methodology', 'N/A')}")
    print(f"   Web search used: {result.get('web_search_used', False)}")

    if 'structured_data' in result:
        data = result['structured_data']
        print(f"\n[TABLE] Таблица:")
        print(f"   Заголовки: {data.get('headers', [])}")
        print(f"   Количество строк: {len(data.get('rows', []))}")


if __name__ == "__main__":
    try:
        # Тест 1: Базовый поиск
        test_basic_search()

        # Тест 2: Таблица С веб-поиском
        test_table_generation_with_search()

        # Тест 3: Таблица БЕЗ веб-поиска
        test_table_without_search()

        print("\n" + "="*80)
        print("[SUCCESS] ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
        print("="*80)

    except Exception as e:
        print(f"\n[ERROR] ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
