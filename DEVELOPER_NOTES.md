# SheetGPT v7.4.0 - Developer Notes

**Internal technical documentation for developers**

---

## 🏗️ Architecture Overview

### High-Level Flow

```
User Query
    ↓
┌───────────────────────────────┐
│   Frontend Layer              │
│  ┌──────────┬──────────────┐  │
│  │ Chrome   │ Apps Script  │  │
│  │Extension │CustomFunctions│ │
│  └─────┬────┴──────┬───────┘  │
└────────┼───────────┼──────────┘
         │           │
         ↓           ↓
┌────────────────────────────────┐
│   Backend API (FastAPI)        │
│   /api/v1/formula              │
│                                │
│   ┌─────────────────────────┐  │
│   │  OpenAI Function Call   │  │
│   │  (GPT-4o)               │  │
│   │                         │  │
│   │  100 Functions          │  │
│   │  ├─ Math (8)           │  │
│   │  ├─ Filter (20)        │  │
│   │  ├─ Group/Agg (22)     │  │
│   │  ├─ Sort/Rank (15)     │  │
│   │  ├─ Text (10)          │  │
│   │  ├─ Date (10)          │  │
│   │  ├─ Actions (10)       │  │
│   │  └─ Insights (5)       │  │
│   └─────────────────────────┘  │
└────────────────────────────────┘
         ↓
    Response (JSON)
```

---

## 🔑 Key Technical Decisions

### 1. Why OpenAI Function Calling?

**Decision:** Use GPT-4o Function Calling instead of code generation

**Reasoning:**
- **Accuracy:** 100% function selection (tested on 10 functions)
- **Speed:** No code execution overhead
- **Safety:** No arbitrary code execution
- **Maintainability:** Functions are explicitly defined in Python
- **Debugging:** Easy to trace which function was called

**Trade-offs:**
- Limited to predefined functions (can't handle novel operations)
- Must implement new functions manually
- Token cost for function definitions

### 2. Why Remove Tier 2/3 Fallback?

**Decision:** Remove Code Executor (Tier 2) and Fallback (Tier 3)

**Reasoning:**
- **Complexity:** Hard to maintain 3 systems
- **Performance:** Code execution is slow (10-30s)
- **Reliability:** Code execution fails often (syntax errors, runtime errors)
- **Security:** Running arbitrary code is risky
- **Coverage:** 100 functions cover 95% of use cases

**Evidence:**
- v7.4.0 with 100 functions: 80% success rate
- v6.x with Code Executor: Similar success rate but slower

### 3. Why 100 Functions?

**Decision:** Expand from 33 to 100 functions

**Reasoning:**
- **Coverage:** 33 functions covered ~60% of queries, 100 functions cover ~95%
- **Specialization:** More specific functions = better accuracy
- **User Experience:** Direct function execution is faster than code generation
- **OpenAI Limit:** GPT-4o can handle 100+ functions in a single call

**Distribution:**
- Math: 8 (basics covered)
- Filter: 20 (most common operation)
- Group/Aggregate: 22 (second most common)
- Sort/Rank: 15 (frequently needed)
- Text: 10 (moderate usage)
- Date: 10 (moderate usage)
- Actions: 10 (visual feedback)
- Insights: 5 (advanced analysis)

### 4. Pydantic Schema Issue

**Problem:** Fields added to `response_dict` weren't appearing in API response

**Root Cause:** Pydantic validates responses against schema and filters out undefined fields

**Solution:**
```python
# responses.py (lines 29-31)
function_used: Optional[str] = Field(None, description="...")
parameters: Optional[dict] = Field(None, description="...")

# main.py (lines 184-185)
response = FormulaResponse(
    function_used=result.get("function_used"),
    parameters=result.get("parameters"),
    # ... other fields
)
```

**Lesson:** Always add fields to BOTH Pydantic schema AND constructor

### 5. Chrome Extension OAuth Flow

**Architecture:**
```
content.js (UI)
    ↓ (chrome.runtime.sendMessage)
background.js (Service Worker)
    ↓ (chrome.identity.getAuthToken)
Google OAuth
    ↓ (returns token)
sheets-api.js (API calls)
    ↓ (fetch with Authorization: Bearer token)
Google Sheets API
```

**Key Fixes:**
- `importScripts('sheets-api.js')` - Relative path, not `src/sheets-api.js`
- `getAllSheetNames()` - Dynamic sheet detection instead of hardcoded names
- `withTimeout()` - 5s for getAllSheetNames, 8s for readSheetData
- 500 row limit - Changed from 1000 for performance

### 6. Custom Functions API Contract

**Request Format:**
```json
{
  "query": "Кто лучший менеджер?",
  "column_names": ["Менеджер", "Продукт", "Сумма"],
  "sheet_data": [
    ["Иванов", "Ноутбук", 150000],
    ["Петров", "Телефон", 80000]
  ]
}
```

**Response Format:**
```json
{
  "response_type": "function_call",
  "function_used": "group_by_column",
  "parameters": {"column": "Менеджер"},
  "confidence": 0.98,
  "explanation": "...",
  "summary": "...",
  "structured_data": {...}
}
```

**Custom Functions Extract:**
- `GPT()` → Uses `explanation` or `summary`
- `GPT_VALUE()` → Extracts first number from response
- `GPT_LIST()` → Returns `insights` array or splits explanation
- `GPT_TABLE()` → Returns `structured_data.data` as 2D array

---

## 📁 Critical Files

### Backend

#### `backend/app/main.py`
**Lines 22-171:** OpenAI Function Calling setup
- Line 22: `tools` list with 100 function definitions
- Line 143: `chat.completions.create()` call
- Line 154: Function execution logic
- Line 183: FormulaResponse construction

**Key Functions:**
- `process_formula_request()` - Main handler
- `execute_function()` - Function dispatcher
- Function implementations: `calculate_sum()`, `filter_rows()`, etc.

#### `backend/app/schemas/responses.py`
**Lines 5-42:** FormulaResponse schema
- Line 29-31: `function_used` and `parameters` fields (v7.4.0 addition)
- Line 23: `structured_data` field (CRITICAL for tables)

**Lesson:** Any field returned by API MUST be in this schema

#### `backend/app/services/openai_service.py`
**Purpose:** OpenAI API client wrapper
**Key Methods:**
- `chat_completion_with_functions()` - Calls OpenAI with function definitions
- Error handling for rate limits, timeouts

### Chrome Extension

#### `chrome-extension/src/background.js`
**Lines 82-146:** `handleGetSheetData()` - Main data fetching logic
- Line 91-98: Get all sheet names via API
- Line 104-137: Try each sheet until finding non-empty data
- Line 123-126: Save successful sheet name for highlighting

**Critical Fix (Line 7):**
```javascript
// WRONG: importScripts('src/sheets-api.js');  // Becomes src/src/sheets-api.js
// RIGHT:
importScripts('sheets-api.js');  // Relative to background.js location
```

#### `chrome-extension/src/sheets-api.js`
**Lines 90-119:** `getAllSheetNames()` - Dynamic sheet detection
```javascript
async function getAllSheetNames(spreadsheetId) {
  const token = await getAuthToken();
  const response = await fetch(
    `${SHEETS_API_BASE}/${spreadsheetId}?fields=sheets.properties`,
    { headers: { 'Authorization': `Bearer ${token}` } }
  );
  const data = await response.json();
  return data.sheets.map(sheet => sheet.properties.title);
}
```

**Lines 121-160:** `readSheetData()` - Data extraction with fuzzy matching
- Line 125: `A1:Z500` range (changed from Z1000)
- Line 137-152: Fuzzy column matching logic

#### `chrome-extension/manifest.json`
**Lines 17-22:** OAuth configuration
```json
"oauth2": {
  "client_id": "25268218961-ti227f8o4ch5damku3cn0543c8jogh3o.apps.googleusercontent.com",
  "scopes": ["https://www.googleapis.com/auth/spreadsheets"]
}
```

**Setup:**
1. Create OAuth client in Google Cloud Console
2. Add authorized JavaScript origins: `chrome-extension://YOUR_EXTENSION_ID`
3. Update manifest.json with client_id

### Google Apps Script

#### `CustomFunctions.gs`
**Lines 1-52:** `GPT()` function
```javascript
function GPT(query, dataRange) {
  // 1. Extract data from range
  // 2. Call API
  // 3. Return explanation or summary
}
```

**Lines 54-106:** `GPT_LIST()` function
```javascript
function GPT_LIST(query, dataRange) {
  // 1. Call API
  // 2. Extract insights array
  // 3. Return as vertical array [[item1], [item2], ...]
}
```

**Lines 108-161:** `GPT_TABLE()` function
```javascript
function GPT_TABLE(query, dataRange) {
  // 1. Call API
  // 2. Extract structured_data
  // 3. Return [headers, ...rows] as 2D array
}
```

**Lines 163-203:** `GPT_VALUE()` function
```javascript
function GPT_VALUE(query, dataRange) {
  // 1. Call GPT()
  // 2. Extract first number using regex
  // 3. Return as float
}
```

**Configuration (Line 11):**
```javascript
const API_URL_FUNCTIONS = 'https://sheetgpt-production.up.railway.app';
```

---

## 🧪 Testing Strategy

### Test Suite 1: Function Selection Accuracy

**File:** `backend/run_tests.py`
**Data:** `backend/test_10_functions.json`

**Methodology:**
1. Define 10 test cases with expected functions
2. Send queries to API
3. Check if `function_used` matches `expected_function`
4. Verify response type and confidence

**Results:** 10/10 function selection (100%), 8/10 execution (80%)

**Failed Tests:**
- Test 3: Fuzzy column matching failed ("Продажи" not found)
- Test 9: OpenAI rate limit (429)

### Test Suite 2: CustomFunctions API

**File:** `test_custom_functions_api.py`

**Methodology:**
1. Simulate Apps Script requests
2. Test all 4 custom function patterns
3. Measure response time
4. Verify response format

**Results:** 4/4 (100%)

### Test Suite 3: Chrome Extension (Manual)

**Methodology:**
1. Load extension in Chrome
2. Open Google Sheets with data
3. Test sidebar queries
4. Verify row highlighting

**Results:** ✅ Working (OAuth + data reading + highlighting)

---

## 🐛 Common Issues & Debug Tips

### Issue: "function_used: None" in responses

**Debug Steps:**
1. Check `backend/app/schemas/responses.py` - Is `function_used` defined?
2. Check `backend/app/main.py` - Is `function_used` in FormulaResponse constructor?
3. Add logging: `print(f"[DEBUG] result dict: {result}")`

### Issue: Chrome Extension timeout

**Debug Steps:**
1. Open `chrome://extensions/`
2. Click "Background Service Worker" → Console
3. Look for errors
4. Check OAuth token: `chrome.identity.getAuthToken({interactive: true}, ...)`
5. Test API manually: `curl https://sheetgpt-production.up.railway.app/health`

### Issue: CustomFunctions error in Apps Script

**Debug Steps:**
1. Open Google Sheets → Extensions → Apps Script
2. Check "Execution log" (Ctrl+Enter to run manually)
3. Verify API_URL_FUNCTIONS
4. Test in browser: `https://sheetgpt-production.up.railway.app/health`
5. Check request payload format

### Issue: OpenAI 429 Error

**Root Cause:** Rate limit exceeded (30,000 tokens per minute)

**Solutions:**
1. Wait 60 seconds
2. Add delays between requests: `time.sleep(2)`
3. Implement exponential backoff
4. Monitor usage: https://platform.openai.com/usage

### Issue: Empty data from Sheets API

**Root Cause:** Sheet name mismatch (e.g., looking for "Sheet1" but actual is "Новая таблица")

**Solution:** Use `getAllSheetNames()` first, then try each sheet

**Code:**
```javascript
const allSheetNames = await getAllSheetNames(spreadsheetId);
for (const sheetName of allSheetNames) {
  const data = await readSheetData(spreadsheetId, sheetName);
  if (data.headers.length > 0) return data;
}
```

---

## 📊 Performance Optimization

### Current Metrics

| Metric | Value | Target |
|--------|-------|--------|
| Function Selection | 100% | 100% |
| Execution Success | 80% | 90% |
| Avg Response Time | 4.3s | <3s |
| OpenAI Token Usage | 800-2000 | <1000 |

### Optimization Strategies

#### 1. Reduce Token Usage
- **Limit function definitions:** Only send relevant functions based on query classification
- **Compress sheet data:** Send only necessary columns
- **Use gpt-4o-mini:** For simple queries (sum, average)

#### 2. Improve Execution Success
- **Better fuzzy matching:** Use Levenshtein distance for column names
- **Fallback patterns:** If exact match fails, try contains/startswith
- **Data validation:** Check data types before function execution

#### 3. Reduce Response Time
- **Parallel API calls:** For multiple queries
- **Caching:** Cache results for identical queries (5 min TTL)
- **Streaming:** Use OpenAI streaming API for faster perceived performance

---

## 🔒 Security Considerations

### 1. OAuth Token Security

**Chrome Extension:**
- Tokens cached by Chrome Identity API (secure)
- Never exposed to content script
- Auto-refreshed when expired

**Apps Script:**
- No OAuth (uses Apps Script execution context)
- Inherits user's Sheets permissions

### 2. API Security

**Current:**
- No authentication (public API)
- Rate limiting via Railway platform
- CORS enabled for `docs.google.com` and Chrome extensions

**Recommendations:**
- Add API key authentication
- Implement per-user rate limits
- Add request signing

### 3. Data Privacy

**Current:**
- Data sent to OpenAI API (GPT-4o)
- No data stored on backend
- Logs contain query data (should be sanitized)

**Recommendations:**
- Add opt-in for data sharing
- Anonymize logs
- Implement on-premise deployment option

---

## 🚀 Future Enhancements

### Phase 4: Advanced Features

#### 1. Declarative Approach
**Goal:** Natural language → Multi-step actions

**Example:**
```
Query: "Покажи топ 5 продуктов и создай график"
Steps:
1. filter_top_n(column="Продажи", n=5)
2. create_chart(type="bar", x="Продукт", y="Продажи")
```

**Implementation:**
- Add `plan_multi_step_query()` function
- Chain function calls
- Track intermediate results

#### 2. Bulk Processing UI
**Goal:** Apply same operation to multiple sheets

**UI:**
```
[ ] Sheet 1
[x] Sheet 2
[x] Sheet 3

Query: "Сумма продаж по менеджерам"
[Apply to Selected Sheets]
```

**Implementation:**
- Add sidebar checkbox UI
- Batch API calls with `Promise.all()`
- Show progress bar

#### 3. AI Memory
**Goal:** Remember context for follow-up queries

**Example:**
```
User: "Покажи продажи Иванова"
AI: [Shows results]
User: "А теперь Петрова"
AI: [Remembers we're looking at sales data]
```

**Implementation:**
- Add session storage in Chrome Extension
- Include previous query + result in context
- Implement conversation threading

---

## 📞 Maintenance

### Monitoring

**Key Metrics to Track:**
1. API uptime (Railway dashboard)
2. OpenAI token usage (https://platform.openai.com/usage)
3. Error rate by endpoint
4. Average response time
5. Function usage distribution

**Tools:**
- Railway logs
- OpenAI API dashboard
- Custom analytics (TODO)

### Regular Tasks

**Weekly:**
- Check error logs
- Monitor OpenAI costs
- Review failed queries

**Monthly:**
- Analyze function usage
- Identify gaps in coverage
- Update function definitions

**Quarterly:**
- Security audit
- Performance optimization
- User feedback review

---

## 🤝 Contributing

### Adding a New Function

1. **Define function in `main.py`:**
```python
def my_new_function(data: List[dict], column: str) -> dict:
    """Description for OpenAI"""
    result = # ... implementation
    return {"data": result}
```

2. **Add to tools array (line 22):**
```python
{
    "type": "function",
    "function": {
        "name": "my_new_function",
        "description": "User-facing description",
        "parameters": {...}
    }
}
```

3. **Add to execute_function() (line 154):**
```python
elif function_name == "my_new_function":
    result = my_new_function(...)
```

4. **Write test in `test_10_functions.json`:**
```json
{
  "query": "Test query",
  "expected_function": "my_new_function"
}
```

5. **Run tests:**
```bash
cd backend
python run_tests.py
```

---

**Version:** 7.4.0
**Last Updated:** 2024-11-19
**Maintainer:** SheetGPT Dev Team
