"""Test professional insights generation directly"""
import sys
sys.path.insert(0, 'C:/SheetGPT/backend')

from app.services.ai_code_executor import get_ai_executor

executor = get_ai_executor()

# Test data
query = "топ 5 товаров по продажам"
result_data = {
    "Товар 4": 3000,
    "Товар 5": 2500,
    "Товар 2": 2000
}
summary = "Топ 3 товара: Товар 4 (3000), Товар 5 (2500), Товар 2 (2000)"
custom_context = "Ты финансовый директор SaaS компании с 10-летним опытом. Анализируй данные с точки зрения рентабельности, маржинальности и unit economics. Давай конкретные рекомендации по оптимизации."

print("Testing _generate_professional_insights directly...")
print(f"Custom context length: {len(custom_context)}")
print("")

try:
    insights = executor._generate_professional_insights(
        query=query,
        result_data=result_data,
        summary=summary,
        custom_context=custom_context
    )

    print("SUCCESS!")
    print(f"\nProfessional insights: {insights.get('professional_insights')}")
    print(f"\nRecommendations: {insights.get('recommendations')}")
    print(f"\nWarnings: {insights.get('warnings')}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
