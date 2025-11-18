"""
Тест воспроизведения ошибки с запросом "выдели города с населением больше 1,7 млн"
"""

import sys
sys.path.insert(0, '.')

from app.services.ai_service import AIService

# Тестовые данные: города с населением
test_data = [
    ["Москва", "1500"],
    ["Санкт-Петербург", "540"],
    ["Новосибирск", "158"],
    ["Екатеринбург", "147"],
    ["Казань", "125"],
    ["Нижний Новгород", "126"],
    ["Челябинск", "119"],
    ["Самара", "114"],
    ["Уфа", "111"],
    ["Ростов-на-Дону", "113"]
]

# Названия колонок
column_names = ["Город", "Население (тыс.)"]

# Запрос
query = "выдели города с населением больше 1,7 млн"

print(f"\n{'='*80}")
print(f"TEST: {query}")
print(f"{'='*80}\n")

print(f"[DATA]:")
print(f"   Columns: {column_names}")
print(f"   Rows: {len(test_data)}")
print(f"\n   First 3 rows:")
for row in test_data[:3]:
    print(f"   {row}")

print(f"\n{'='*80}")
print(f"[PROCESSING] Query...")
print(f"{'='*80}\n")

try:
    # Создаём AI Service
    ai_service = AIService()

    # Обрабатываем запрос
    result = ai_service.process_formula_request(
        query=query,
        column_names=column_names,
        sheet_data=test_data,
        history=[]
    )

    print(f"\n{'='*80}")
    print(f"[RESULT]:")
    print(f"{'='*80}\n")

    print(f"ALL RESULT KEYS: {list(result.keys())}")
    print(f"\nResponse Type: {result.get('response_type')}")
    print(f"Confidence: {result.get('confidence')}")

    if 'error' in result:
        print(f"\n[ERROR IN RESULT]: {result['error']}")

    if 'answer' in result:
        print(f"\nAnswer: {result['answer']}")

    if 'explanation' in result:
        print(f"\nExplanation: {result['explanation']}")

    if 'summary' in result:
        print(f"\nSummary:\n{result['summary']}")

    if 'methodology' in result:
        print(f"\nMethodology:\n{result['methodology']}")

    if 'key_findings' in result:
        print(f"\nKey Findings:")
        for finding in result['key_findings']:
            print(f"  - {finding}")

    if 'code_generated' in result:
        print(f"\nGenerated Code:\n{result['code_generated']}")

    if 'execution_output' in result:
        print(f"\nExecution Output:\n{result['execution_output']}")

    print(f"\n{'='*80}")
    print(f"[SUCCESS] Тест завершён успешно!")
    print(f"{'='*80}\n")

except Exception as e:
    print(f"\n{'='*80}")
    print(f"[ERROR]:")
    print(f"{'='*80}\n")
    print(f"{type(e).__name__}: {str(e)}")

    import traceback
    print(f"\n{'='*80}")
    print(f"Stack Trace:")
    print(f"{'='*80}\n")
    traceback.print_exc()

    print(f"\n{'='*80}")
    print(f"[FAILED] Тест провален!")
    print(f"{'='*80}\n")
