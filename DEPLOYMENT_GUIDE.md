# SheetGPT v7.4.0 - Deployment Guide

## 📦 Структура проекта

```
SheetGPT/
├── backend/                          # FastAPI backend с 100 функциями
│   ├── app/
│   │   ├── main.py                   # Основной API (100 функций)
│   │   ├── schemas/responses.py      # Pydantic схемы
│   │   └── services/openai_service.py
│   └── requirements.txt
├── chrome-extension/                 # Chrome расширение
│   ├── src/
│   │   ├── background.js             # OAuth + Sheets API
│   │   ├── content.js                # Sidebar injection
│   │   ├── sheets-api.js             # Google Sheets API
│   │   └── sidebar.js                # UI логика
│   └── manifest.json
├── CustomFunctions.gs                # Google Apps Script функции
└── CUSTOM_FUNCTIONS_GUIDE.md         # Пользовательская документация
```

---

## 🚀 Деплой Backend (Railway)

### Статус: ✅ DEPLOYED

**Production URL:** https://sheetgpt-production.up.railway.app

**Последняя версия:** v7.4.0 (100 функций, function calling)

### Проверка работоспособности:

```bash
# Health check
curl https://sheetgpt-production.up.railway.app/health

# Тест API
cd C:\SheetGPT
python test_custom_functions_api.py
```

**Результат теста:** 4/4 (100%) ✅

---

## 🔌 Chrome Extension

### Статус: ✅ READY

**Текущая версия:** 1.0.0

### Установка для тестирования:

1. Откройте Chrome: `chrome://extensions/`
2. Включите "Режим разработчика"
3. Нажмите "Загрузить распакованное расширение"
4. Выберите папку `C:\SheetGPT\chrome-extension`

### OAuth Setup:

**Client ID:** `25268218961-ti227f8o4ch5damku3cn0543c8jogh3o.apps.googleusercontent.com`

**Scopes:**
- `https://www.googleapis.com/auth/spreadsheets`

**Redirect URI:**
- `https://bmajcbeobecfdglpfngnkhakdohmpcoe.chromiumapp.org/`

### Тестирование:

1. Откройте любой Google Sheets
2. Sidebar должен появиться справа
3. Введите запрос: "Покажи мне все данные"
4. Нажмите "Анализировать"
5. Результат должен появиться через 3-8 секунд

**Результат последнего теста:** ✅ Работает (подсветка строк успешна)

---

## 📊 Google Apps Script Custom Functions

### Статус: ✅ CODE READY, ⏳ WAITING DEPLOYMENT

### Шаги деплоя:

#### Шаг 1: Создать Apps Script проект

1. Откройте любой Google Sheets
2. **Расширения** → **Apps Script**
3. Создайте новый файл `CustomFunctions.gs`
4. Скопируйте код из `C:\SheetGPT\CustomFunctions.gs`
5. Нажмите **Сохранить** (Ctrl+S)

#### Шаг 2: Настроить API URL

По умолчанию используется Railway production:
```javascript
const API_URL_FUNCTIONS = 'https://sheetgpt-production.up.railway.app';
```

Для локального тестирования:
```javascript
const API_URL_FUNCTIONS = 'http://localhost:8000';
```

#### Шаг 3: Протестировать функции

В Google Sheets введите:

```
=GPT("Привет от SheetGPT!")
```

**Ожидаемый результат:** Текстовый ответ от AI через 3-5 секунд

**Дополнительные тесты:**
```
=GPT_VALUE("Сколько будет 2+2?")  → 4
=GPT_LIST("Список фруктов")        → ["Яблоко", "Банан", "Апельсин"]
=GPT_TABLE("Таблица умножения 2")  → Двумерная таблица
```

---

## 🧪 Тестирование функций

### Test Suite 1: API Endpoint

**Файл:** `test_custom_functions_api.py`

**Запуск:**
```bash
cd C:\SheetGPT
python test_custom_functions_api.py
```

**Последний результат:** 4/4 (100%) ✅

### Test Suite 2: 100 Functions

**Файл:** `run_tests.py` + `test_10_functions.json`

**Запуск:**
```bash
cd C:\SheetGPT\backend
python run_tests.py
```

**Последний результат:** 8/10 (80%) - 2 провала из-за fuzzy matching

### Test Suite 3: Chrome Extension

**Ручное тестирование:**
1. Открыть Google Sheets с данными
2. Использовать sidebar для анализа
3. Проверить подсветку строк

**Последний результат:** ✅ Работает

---

## 📋 Roadmap Progress

### Phase 1: 100 Functions ✅ DONE
- ✅ 100 функций реализовано
- ✅ Function calling настроен
- ✅ Тесты пройдены (80-100%)
- ✅ Fallback Tier 2/3 удалены

### Phase 2: Optimization ✅ DONE
- ✅ `selected_range` поддержка
- ✅ Лимит 500 строк (было 1000)
- ✅ OAuth token caching (built-in)

### Phase 3: Custom Functions ✅ CODE READY
- ✅ CustomFunctions.gs создан
- ✅ Документация CUSTOM_FUNCTIONS_GUIDE.md
- ⏳ Деплой в Apps Script (ручной шаг)
- ❌ Публикация в Marketplace (будущее)

### Phase 4: Future (Optional)
- ❌ Declarative approach
- ❌ Bulk processing UI
- ❌ AI memory

---

## 🔧 Troubleshooting

### Проблема: "function_used: None" в ответах

**Причина:** Pydantic schema фильтрует поля

**Статус:** Исправлено в responses.py (lines 29-31) и main.py (lines 184-185)

**Проверка:**
```bash
python run_tests.py | grep "function_used"
```

### Проблема: Chrome Extension timeout

**Причина:** OAuth не настроен или backend недоступен

**Решение:**
1. Проверить `chrome://extensions/` → Background Service Worker → Console
2. Проверить `manifest.json` client_id
3. Убедиться что Railway backend работает

### Проблема: Apps Script "Request failed"

**Причина:** API недоступен или CORS

**Решение:**
1. Проверить API_URL_FUNCTIONS в CustomFunctions.gs
2. Попробовать в браузере: https://sheetgpt-production.up.railway.app/health
3. Проверить лимиты Railway

### Проблема: OpenAI Rate Limit (429)

**Причина:** Превышен лимит 30,000 TPM

**Решение:**
1. Подождать 1 минуту
2. Уменьшить частоту запросов
3. Использовать кэширование результатов

---

## 🎯 Next Steps

### Immediate (Manual by User):

1. **Deploy CustomFunctions.gs** ⏳
   - Открыть Google Sheets
   - Создать Apps Script проект
   - Скопировать код
   - Протестировать =GPT() функцию

2. **Test in Real Sheets** ⏳
   - Использовать реальные данные (продажи, финансы)
   - Проверить все 4 функции
   - Собрать feedback

### Future (If Needed):

3. **Publish to Chrome Web Store**
   - Подготовить скриншоты
   - Написать описание
   - Пройти review

4. **Publish to Workspace Marketplace**
   - Создать листинг
   - Добавить видео демо
   - Сделать landing page

---

## 📊 Performance Metrics

### Backend Response Times:
- **GPT (text):** 5.59s
- **GPT_VALUE (number):** 2.50s
- **GPT_LIST (array):** 6.72s
- **GPT_TABLE (table):** 2.34s

### Accuracy:
- **Function Selection:** 100% (10/10 tests)
- **Execution Success:** 80% (8/10 tests)
- **API Availability:** 100% (Railway uptime)

### Token Usage:
- **Average per request:** 800-2000 tokens
- **OpenAI Limit:** 30,000 TPM (GPT-4o)

---

## 📞 Support

### Logs Location:
- **Backend:** Railway dashboard
- **Extension:** Chrome → Extensions → Background Service Worker
- **Apps Script:** Google Sheets → Extensions → Apps Script → Execution Log

### Debug Commands:
```bash
# Backend test
curl -X POST https://sheetgpt-production.up.railway.app/api/v1/formula \
  -H "Content-Type: application/json" \
  -d '{"query":"Test", "column_names":[], "sheet_data":[]}'

# Extension reload
chrome://extensions/ → Reload icon

# Clear OAuth cache
chrome.identity.clearAllCachedAuthTokens()
```

---

**Version:** 7.4.0
**Last Updated:** 2024-11-19
**Status:** ✅ Production Ready (Backend + Extension), ⏳ Apps Script Pending Manual Deploy
