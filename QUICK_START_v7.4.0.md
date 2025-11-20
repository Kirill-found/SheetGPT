# SheetGPT v7.4.0 - Quick Start Guide

**Get started with SheetGPT in 5 minutes**

---

## 🎯 What is SheetGPT?

AI assistant for Google Sheets with **100 functions** that understands natural language.

**Examples:**
- "Покажи топ 5 продаж" → Automatically filters and sorts data
- "Сумма продаж Иванова" → Calculates sum with condition
- "Группировка по менеджерам" → Creates pivot table

---

## ⚡ Choose Your Method

### Method 1: Chrome Extension (Recommended) ⭐

**Best for:** Interactive analysis, one-off queries

**Setup (2 minutes):**
1. Open Chrome: `chrome://extensions/`
2. Enable "Developer mode" (top right)
3. Click "Load unpacked"
4. Select folder: `C:\SheetGPT\chrome-extension`

**Usage:**
1. Open any Google Sheets
2. Sidebar appears automatically
3. Type: "Покажи мне топ 5"
4. Click "Анализировать"
5. ✅ Results in 3-8 seconds

**Demo:** [Screenshot](https://github.com/your-org/sheetgpt/docs/demo.gif)

---

### Method 2: Custom Functions (In-Cell) 📊

**Best for:** Recurring calculations, formulas in cells

**Setup (3 minutes):**
1. Open Google Sheets
2. **Extensions** → **Apps Script**
3. Create new file `CustomFunctions.gs`
4. Copy code from `C:\SheetGPT\CustomFunctions.gs`
5. Save (Ctrl+S)

**Usage:**
```
=GPT("Кто лучший менеджер?", A1:C10)
```
Result appears in cell like any formula!

**4 Functions Available:**
- `=GPT(query, [data])` - Text answer
- `=GPT_VALUE(query, [data])` - Number (e.g., sum, average)
- `=GPT_LIST(query, [data])` - List (e.g., top 5 names)
- `=GPT_TABLE(query, [data])` - Table (e.g., grouped data)

**Examples:**
```
=GPT("Кто продал больше всех?", A1:C100)
=GPT_VALUE("Общая сумма продаж", B2:B100)
=GPT_LIST("Топ 3 менеджера", A1:C100)
=GPT_TABLE("Группировка по городам с суммой", A1:D100)
```

---

### Method 3: API (Advanced) 🚀

**Best for:** Custom integrations, automation

**Production URL:**
```
https://sheetgpt-production.up.railway.app
```

**Test API:**
```bash
curl -X POST https://sheetgpt-production.up.railway.app/api/v1/formula \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Сумма продаж где сумма больше 500000",
    "column_names": ["Менеджер", "Продажи"],
    "sheet_data": [["Иванов", 600000], ["Петров", 400000]]
  }'
```

**Response:**
```json
{
  "response_type": "function_call",
  "function_used": "filter_rows",
  "summary": "Найдено 1 строк: Иванов - 600,000₽",
  "confidence": 0.98
}
```

**API Docs:** https://sheetgpt-production.up.railway.app/docs

---

## 📋 Real-World Examples

### Example 1: Sales Analysis 💰

**Data:**
```
| Менеджер | Продукт  | Сумма   | Дата       |
|----------|----------|---------|------------|
| Иванов   | Ноутбук  | 150000  | 2024-01-15 |
| Петров   | Телефон  | 80000   | 2024-01-16 |
| Иванов   | Мышка    | 2000    | 2024-01-17 |
```

**Queries:**
```
Chrome Extension:
→ "Кто лучший менеджер?"
→ "Покажи все продажи больше 50000"
→ "Группировка по менеджерам с суммой"

Custom Functions:
=GPT("Кто лучший менеджер?", A1:D4)
=GPT_VALUE("Сумма продаж Иванова", A1:D4)
=GPT_TABLE("Группировка по менеджерам", A1:D4)
```

**Results:**
- Best manager identified: Иванов (152,000₽)
- Filtered rows highlighted in yellow
- Summary table created

---

### Example 2: Date Analysis 📅

**Data:**
```
| Дата       | Продажи |
|------------|---------|
| 2024-01-15 | 150000  |
| 2024-02-10 | 200000  |
| 2024-01-20 | 180000  |
```

**Queries:**
```
→ "Продажи за январь"
→ "Топ 3 дня по продажам"
→ "Группировка по месяцам"
```

**Results:**
- January sales: 330,000₽
- Top days identified and highlighted
- Monthly summary table created

---

### Example 3: Text Search 🔍

**Data:**
```
| Клиент    | Комментарий            |
|-----------|------------------------|
| Иванов    | Срочный заказ!        |
| Петров    | Все ок                |
| Сидоров   | Нужно срочно доставить|
```

**Queries:**
```
→ "Найди все срочные заказы"
→ "Список клиентов со словом 'срочно'"
```

**Results:**
- 2 rows highlighted (Иванов, Сидоров)
- List of urgent customers returned

---

## 🧪 Test Your Setup

### Test 1: Chrome Extension
1. Open Google Sheets with any data
2. Open sidebar (appears automatically)
3. Type: "Покажи мне все"
4. ✅ Should see results in 3-8 seconds

### Test 2: Custom Functions
1. In any cell, type: `=GPT("Hello from SheetGPT!")`
2. Press Enter
3. ✅ Should see AI response in 3-5 seconds

### Test 3: API
```bash
curl https://sheetgpt-production.up.railway.app/health
```
✅ Should return: `{"status":"healthy"}`

---

## 🐛 Troubleshooting

### Chrome Extension: "Request timeout"
**Fix:** Check OAuth setup in [manifest.json](chrome-extension/manifest.json):17-22

### Custom Functions: "Error: Request failed"
**Fix:** Verify API_URL in [CustomFunctions.gs](CustomFunctions.gs):11
```javascript
const API_URL_FUNCTIONS = 'https://sheetgpt-production.up.railway.app';
```

### API: 429 Error (Rate Limit)
**Fix:** Wait 60 seconds (OpenAI limit: 30,000 tokens/minute)

### Empty Results
**Fix:** Make sure your data has:
- ✅ Header row with column names
- ✅ At least 1 data row
- ✅ Clear column structure

---

## 📚 Learn More

**Documentation:**
- [README.md](README.md) - Full overview
- [CUSTOM_FUNCTIONS_GUIDE.md](CUSTOM_FUNCTIONS_GUIDE.md) - User guide
- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Deployment
- [DEVELOPER_NOTES.md](DEVELOPER_NOTES.md) - Technical details

**API Docs:**
- Swagger: https://sheetgpt-production.up.railway.app/docs
- ReDoc: https://sheetgpt-production.up.railway.app/redoc

**Support:**
- Issues: https://github.com/your-org/sheetgpt/issues
- Docs: https://code.claude.com/docs

---

## 🎉 What's Next?

### After Basic Setup:

1. **Try Complex Queries:**
   ```
   → "Создай сводную таблицу по менеджерам и продуктам"
   → "Покажи тренд продаж за последние 3 месяца"
   → "Найди аномалии в данных"
   ```

2. **Combine with Google Sheets Features:**
   ```
   =IF(GPT_VALUE("Средняя зарплата", A1:B100) > 100000, "Высокая", "Низкая")
   ```

3. **Automate Workflows:**
   - Use Apps Script triggers for scheduled analysis
   - Integrate with Google Apps Script automation

### Advanced Features (Phase 4 - Coming Soon):

- 🔮 Multi-step operations ("Фильтруй → Группируй → Создай график")
- 📊 Bulk processing (apply to multiple sheets)
- 🧠 AI memory (contextual follow-up queries)

---

## ⚡ Pro Tips

1. **Be Specific:**
   - ✅ "Сумма продаж Иванова в январе"
   - ❌ "Покажи данные"

2. **Use Data Ranges:**
   - ✅ `=GPT("Анализ", A1:C100)` - Fast (only 100 rows)
   - ❌ `=GPT("Анализ")` - Slow (entire sheet)

3. **Cache Results:**
   - Copy result → Paste Special → Values
   - Prevents recalculation on every sheet open

4. **Check Function Used:**
   - API returns `function_used` field
   - Helps understand which of 100 functions was selected

---

## 📊 What Can You Do?

**100 Functions Across 8 Categories:**

✅ **Math** - Sum, average, median, percentile, correlation, variance
✅ **Filtering** - By value, date, top N, bottom N, contains, unique
✅ **Grouping** - Group by, pivot tables, aggregations, running totals
✅ **Sorting** - Sort, rank, percentile rank, dense rank
✅ **Text** - Find, regex, concatenate, split, extract
✅ **Dates** - Format, extract, calculate difference, filter by range
✅ **Actions** - Highlight rows, create tables/charts, modify columns
✅ **Insights** - Analyze trends, find anomalies, suggest actions

**See full list:** [README.md](README.md)#-100-functions-categories

---

**Version:** 7.4.0
**Status:** ✅ Production Ready
**Updated:** 2024-11-19

**Ready to start? Pick your method above and try it now!** 🚀
