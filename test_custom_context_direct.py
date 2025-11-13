"""
Прямой тест custom_context функциональности
"""
import sys
sys.path.insert(0, 'C:/SheetGPT/backend')

from app.services.ai_code_executor import AICodeExecutor

# Создаем executor
executor = AICodeExecutor()

# Тестовые данные
query = "сумма продаж"
column_names = ["Товар", "Продажи"]
sheet_data = [
    ["Товар 1", 1000],
    ["Товар 2", 2000],
    ["Товар 3", 1500]
]
custom_context = "Ты финансовый директор. Давай краткие рекомендации."

print("\n========== ТЕСТ CUSTOM_CONTEXT ==========\n")
print(f"Query: {query}")
print(f"Custom Context: {custom_context}")
print("\nВызываем process_with_code...\n")

# Вызываем
result = executor.process_with_code(
    query=query,
    column_names=column_names,
    sheet_data=sheet_data,
    history=[],
    custom_context=custom_context
)

print("\n========== РЕЗУЛЬТАТ ==========\n")
print(f"Summary: {result.get('summary')}")
print(f"Professional Insights: {result.get('professional_insights')}")
print(f"Recommendations: {result.get('recommendations')}")
print(f"Warnings: {result.get('warnings')}")
