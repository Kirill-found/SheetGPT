"""Тест Gemini API"""
import google.generativeai as genai
import os
from dotenv import load_dotenv

# Загружаем .env
load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
print(f"API Key загружен: {API_KEY[:20]}...")

try:
    # Настраиваем Gemini
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')

    # Простой тест
    print("\nОтправляю тестовый запрос...")
    response = model.generate_content("Скажи привет на русском")

    print("\n✅ Успех! Ответ от Gemini:")
    print(response.text)

except Exception as e:
    print(f"\n❌ Ошибка: {e}")
    print("\nВозможные причины:")
    print("1. API key неактивен - проверь на https://makersuite.google.com/app/apikey")
    print("2. Нужно включить Generative Language API в Google Cloud Console")
    print("3. API key скопирован неправильно")
