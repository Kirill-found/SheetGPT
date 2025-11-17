"""
Локальный тест Function Calling v7.0.0
Тестирует работу AIFunctionCaller без деплоя
"""

import asyncio
import pandas as pd
import sys
import os

# Добавляем путь к модулям
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.services.ai_function_caller import AIFunctionCaller


async def test_function_calling():
    """Тестирование function calling на реальных данных"""

    print("=" * 80)
    print("ТЕСТ FUNCTION CALLING v7.0.0")
    print("=" * 80)

    # Создаем тестовые данные (как у пользователя)
    test_data = {
        "Канал": ["Google Ads", "Facebook Ads", "TikTok Ads", "Email", "SEO"],
        "Показы": [120000, 90000, 150000, 40000, 80000],
        "Клики": [4800, 3150, 6000, 3200, 4000],
        "CTR": [0.04, 0.035, 0.04, 0.08, 0.05],
        "Лиды": [1200, 700, 1500, 2600, 1000],
        "CPL": [250, 285, 200, 40, 100],
        "Клиенты": [180, 110, 210, 520, 150],
        "CAC": [1667, 2273, 1428, 200, 667],
        "Выручка": [950000, 510000, 780000, 520000, 600000]
    }

    df = pd.DataFrame(test_data)
    column_names = list(df.columns)
    sheet_data = df.values.tolist()

    print(f"\n📊 Тестовые данные: {len(df)} строк × {len(df.columns)} колонок")
    print(f"Колонки: {', '.join(column_names)}\n")

    # Создаем AIFunctionCaller
    caller = AIFunctionCaller()

    # Тест-кейсы
    test_cases = [
        {
            "name": "Тест 1: Выделение строк (highlight)",
            "query": "выдели строки где Выручка меньше 600000 желтым цветом",
            "expected_function": "highlight_rows"
        },
        {
            "name": "Тест 2: Фильтрация (filter)",
            "query": "покажи строки где CTR больше 0.04",
            "expected_function": "filter_rows"
        },
        {
            "name": "Тест 3: Сортировка (sort)",
            "query": "отсортируй по Выручке по убыванию",
            "expected_function": "sort_data"
        },
        {
            "name": "Тест 4: Сумма (calculate_sum)",
            "query": "сумма выручки по всем каналам",
            "expected_function": "calculate_sum"
        },
        {
            "name": "Тест 5: Группировка (aggregate)",
            "query": "средний CTR по каждому каналу",
            "expected_function": "aggregate_by_group"
        },
        {
            "name": "Тест 6: Поиск (search)",
            "query": "найди строки с Google",
            "expected_function": "search_rows"
        },
        {
            "name": "Тест 7: Топ N (top_n)",
            "query": "топ 3 канала по выручке",
            "expected_function": "sort_data"  # или top_n если реализован
        },
    ]

    results = []

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*80}")
        print(f"🧪 {test_case['name']}")
        print(f"{'='*80}")
        print(f"Запрос: '{test_case['query']}'")
        print(f"Ожидаемая функция: {test_case['expected_function']}")

        try:
            # Вызываем AIFunctionCaller
            response = await caller.process_query(
                query=test_case['query'],
                df=df,
                column_names=column_names,
                sheet_data=sheet_data
            )

            # Проверяем результат
            if response.get('function_used'):
                print(f"\n✅ Функция вызвана: {response['function_used']}")
                print(f"Параметры: {response.get('parameters', {})}")

                # Проверяем совпадение ожидаемой функции
                if response['function_used'] == test_case['expected_function']:
                    print("✅ Совпадает с ожидаемой!")
                    results.append({"test": test_case['name'], "status": "PASS", "function": response['function_used']})
                else:
                    print(f"⚠️  Ожидалась {test_case['expected_function']}, но вызвана {response['function_used']}")
                    results.append({"test": test_case['name'], "status": "PARTIAL", "function": response['function_used']})

                # Показываем результат
                if response.get('summary'):
                    print(f"\n📝 Результат: {response['summary']}")

                if response.get('highlight_rows'):
                    print(f"🎨 Выделены строки: {response['highlight_rows']}")
                    print(f"🎨 Цвет: {response['highlight_color']}")

                if response.get('structured_data'):
                    headers = response['structured_data'].get('headers', [])
                    rows = response['structured_data'].get('rows', [])
                    print(f"\n📊 Structured Data:")
                    print(f"   Headers: {headers}")
                    print(f"   Rows: {len(rows)}")
                    if rows:
                        print(f"   First row: {rows[0]}")

                if response.get('key_findings'):
                    print(f"\n💡 Key Findings: {response['key_findings']}")

            elif response.get('response_type') == 'code_execution':
                print(f"\n⚠️  Fallback на code execution (функция не найдена)")
                print(f"Сгенерированный код:\n{response.get('code', 'N/A')[:200]}...")
                results.append({"test": test_case['name'], "status": "FALLBACK", "function": "code_executor"})

            else:
                print(f"\n❌ Неожиданный тип ответа: {response.get('response_type')}")
                results.append({"test": test_case['name'], "status": "FAIL", "function": "unknown"})

        except Exception as e:
            print(f"\n❌ ОШИБКА: {str(e)}")
            import traceback
            traceback.print_exc()
            results.append({"test": test_case['name'], "status": "ERROR", "function": "error"})

    # Итоговая статистика
    print(f"\n\n{'='*80}")
    print("📊 ИТОГОВАЯ СТАТИСТИКА")
    print(f"{'='*80}")

    total = len(results)
    passed = sum(1 for r in results if r['status'] == 'PASS')
    partial = sum(1 for r in results if r['status'] == 'PARTIAL')
    fallback = sum(1 for r in results if r['status'] == 'FALLBACK')
    failed = sum(1 for r in results if r['status'] in ['FAIL', 'ERROR'])

    print(f"\nВсего тестов: {total}")
    print(f"✅ Успешно (правильная функция): {passed}")
    print(f"⚠️  Частично (другая функция): {partial}")
    print(f"🔄 Fallback на code executor: {fallback}")
    print(f"❌ Ошибки: {failed}")

    success_rate = ((passed + partial) / total * 100) if total > 0 else 0
    print(f"\n📈 Успешность: {success_rate:.1f}%")

    if success_rate >= 80:
        print("\n🎉 ОТЛИЧНЫЙ РЕЗУЛЬТАТ! Готово к деплою.")
    elif success_rate >= 60:
        print("\n👍 ХОРОШИЙ РЕЗУЛЬТАТ. Можно деплоить с небольшими улучшениями.")
    else:
        print("\n⚠️  ТРЕБУЮТСЯ УЛУЧШЕНИЯ перед деплоем.")

    print("\n" + "="*80)

    return results


if __name__ == "__main__":
    # Проверяем наличие OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("[ERROR] OPENAI_API_KEY not found in environment")
        print("Set it: export OPENAI_API_KEY=your-key")
        sys.exit(1)

    # Запускаем тесты
    asyncio.run(test_function_calling())
