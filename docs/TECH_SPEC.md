# SheetGPT - Technical Specification

## 🏗️ Architecture Overview
```
┌─────────────────────────────────────────┐
│         Google Sheets (Client)          │
│  ┌───────────────────────────────────┐  │
│  │   Apps Script (Frontend)          │  │
│  │   - Sidebar UI (HTML/CSS/JS)      │  │
│  │   - Read/Write to Sheet           │  │
│  └────────────┬──────────────────────┘  │
└───────────────┼─────────────────────────┘
                │ HTTPS
                ▼
┌───────────────────────────────────────────┐
│      Backend API (FastAPI/Python)         │
│  ┌─────────────────────────────────────┐  │
│  │  /analyze - AI Analysis             │  │
│  │  /formula - Formula Generation      │  │
│  │  /report  - Report Creation         │  │
│  └─────────────┬───────────────────────┘  │
└────────────────┼─────────────────────────┘
                 │
        ┌────────┴────────┐
        ▼                 ▼
┌──────────────┐   ┌──────────────┐
│   GPT-4 API  │   │  PostgreSQL  │
│   (OpenAI)   │   │  (User data) │
└──────────────┘   └──────────────┘
```

---

## 🎨 Frontend: Google Apps Script

### Technology Stack
- **Google Apps Script** (JavaScript-based)
- **HTML/CSS** for sidebar UI
- **Google Sheets API** (native access)

### File Structure
```
/frontend
├── Code.gs              # Main Apps Script entry point
├── Sidebar.html         # Sidebar UI
├── Styles.html          # CSS (inline in HTML)
└── API.gs               # API calls to backend
```

### Key Functions

#### Code.gs
```javascript
/**
 * Entry point: runs when user opens Add-on
 */
function onOpen(e) {
  SpreadsheetApp.getUi()
    .createAddonMenu()
    .addItem('Open SheetGPT', 'showSidebar')
    .addToUi();
}

/**
 * Shows sidebar when user clicks menu item
 */
function showSidebar() {
  const html = HtmlService.createHtmlOutputFromFile('Sidebar')
    .setTitle('SheetGPT')
    .setWidth(350);
  SpreadsheetApp.getUi().showSidebar(html);
}

/**
 * Reads data from active sheet
 * @returns {Array} 2D array of sheet data
 */
function getSheetData() {
  const sheet = SpreadsheetApp.getActiveSheet();
  const data = sheet.getDataRange().getValues();
  return data;
}

/**
 * Inserts formula into cell
 */
function insertFormula(cell, formula) {
  const sheet = SpreadsheetApp.getActiveSheet();
  sheet.getRange(cell).setFormula(formula);
}
```

#### API.gs
```javascript
/**
 * Sends user query to backend API
 */
function callBackendAPI(endpoint, payload) {
  const API_URL = 'https://api.sheetgpt.ru';
  const userToken = getUserToken(); // Get from PropertiesService
  
  const options = {
    method: 'post',
    contentType: 'application/json',
    headers: {
      'Authorization': `Bearer ${userToken}`
    },
    payload: JSON.stringify(payload)
  };
  
  const response = UrlFetchApp.fetch(`${API_URL}${endpoint}`, options);
  return JSON.parse(response.getContentText());
}
```

### Sidebar UI (Sidebar.html)
```html



  
  
    body {
      font-family: 'Google Sans', Arial, sans-serif;
      margin: 0;
      padding: 16px;
      background: #f8f9fa;
    }
    .header {
      font-size: 20px;
      font-weight: 500;
      margin-bottom: 8px;
    }
    .subheader {
      font-size: 14px;
      color: #5f6368;
      margin-bottom: 24px;
    }
    .input-container {
      margin-bottom: 16px;
    }
    textarea {
      width: 100%;
      min-height: 100px;
      padding: 12px;
      border: 1px solid #dadce0;
      border-radius: 8px;
      font-size: 14px;
      resize: vertical;
    }
    button {
      background: #1a73e8;
      color: white;
      border: none;
      padding: 10px 24px;
      border-radius: 4px;
      cursor: pointer;
      font-size: 14px;
      font-weight: 500;
    }
    button:hover {
      background: #1765cc;
    }
    .loading {
      display: none;
      text-align: center;
      margin: 16px 0;
    }
    .result {
      margin-top: 16px;
      padding: 16px;
      background: white;
      border-radius: 8px;
      border: 1px solid #e8eaed;
    }
  


  👋 Привет!
  
    Опиши что нужно сделать, я помогу
  
  
  
    
  
  
  Отправить
  
  
    🤔 Думаю...
  
  
  

  
    async function sendQuery() {
      const query = document.getElementById('queryInput').value;
      if (!query) return;
      
      // Show loading
      document.getElementById('loading').style.display = 'block';
      document.getElementById('result').style.display = 'none';
      
      // Call backend via Apps Script
      google.script.run
        .withSuccessHandler(displayResult)
        .withFailureHandler(displayError)
        .processQuery(query);
    }
    
    function displayResult(result) {
      document.getElementById('loading').style.display = 'none';
      const resultDiv = document.getElementById('result');
      resultDiv.innerHTML = result.answer;
      resultDiv.style.display = 'block';
    }
    
    function displayError(error) {
      document.getElementById('loading').style.display = 'none';
      alert('Ошибка: ' + error.message);
    }
  


```

---

## ⚙️ Backend: FastAPI (Python)

### Technology Stack
- **FastAPI** (Python web framework)
- **Python 3.11+**
- **PostgreSQL** (database)
- **SQLAlchemy** (ORM)
- **OpenAI API** (GPT-4o-mini)
- **Pydantic** (data validation)

### File Structure
```
/backend
├── main.py                 # FastAPI app entry point
├── routers/
│   ├── analyze.py         # /analyze endpoint
│   ├── formula.py         # /formula endpoint
│   └── report.py          # /report endpoint
├── services/
│   ├── ai_service.py      # GPT-4 integration
│   └── sheet_service.py   # Sheet data processing
├── models/
│   └── user.py            # SQLAlchemy models
├── schemas/
│   └── requests.py        # Pydantic schemas
└── utils/
    ├── auth.py            # JWT authentication
    └── config.py          # Configuration
```

### Key Endpoints

#### POST /api/v1/analyze
Analyzes sheet data and answers analytical questions

**Request:**
```json
{
  "query": "Why did sales drop in October?",
  "sheet_data": [
    ["Date", "Sales", "Manager"],
    ["2024-09-15", 150000, "Ivanov"],
    ["2024-10-15", 100000, "Ivanov"],
    ...
  ],
  "sheet_metadata": {
    "name": "Sales Data",
    "total_rows": 200,
    "total_cols": 5
  }
}
```

**Response:**
```json
{
  "answer": "📉 Found 3 main reasons:\n1. Manager Ivanov: -33%\n...",
  "insights": [
    {
      "type": "decrease",
      "factor": "Manager Ivanov",
      "impact": -50000,
      "percentage": -33
    }
  ],
  "processing_time": 2.3
}
```

---

#### POST /api/v1/formula
Generates Google Sheets formula based on natural language

**Request:**
```json
{
  "query": "Sum of sales where amount > 500000",
  "sheet_data": [
    ["Customer", "Sales"],
    ["Company A", 600000],
    ["Company B", 400000]
  ],
  "column_names": ["Customer", "Sales"]
}
```

**Response:**
```json
{
  "formula": "=SUMIF(B:B, \">500000\", B:B)",
  "explanation": "Эта формула суммирует все значения в столбце Sales (B) которые больше 500000",
  "cell_to_insert": "D2",
  "estimated_result": 600000
}
```

---

#### POST /api/v1/report
Creates formatted report in new sheet

**Request:**
```json
{
  "query": "Create weekly sales report",
  "sheet_data": [...],
  "report_type": "weekly"
}
```

**Response:**
```json
{
  "report_title": "Weekly Sales Report - Nov 4-10",
  "report_data": [
    ["Metric", "Value"],
    ["Total Sales", "1,240,000₽"],
    ["Change", "+12%"],
    ...
  ],
  "chart_config": {
    "type": "column",
    "data_range": "A2:B10"
  }
}
```

---

### AI Service (services/ai_service.py)
```python
from openai import AsyncOpenAI
import json

class AIService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4o-mini"  # Cheap and fast
    
    async def analyze_data(self, query: str, sheet_data: list) -> dict:
        """
        Analyzes sheet data based on user query
        """
        # Convert sheet data to structured format
        df_text = self._format_sheet_data(sheet_data)
        
        prompt = f"""
You are a data analyst. Analyze this Google Sheets data and answer the question.

SHEET DATA:
{df_text}

USER QUESTION: {query}

Provide:
1. Direct answer to the question
2. Top 3 contributing factors (if applicable)
3. Specific numbers/percentages
4. Actionable insights

Format response in Russian, use emojis for clarity.
Be concise but specific.
"""
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a helpful data analyst."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,  # Lower = more factual
            max_tokens=500
        )
        
        return {
            "answer": response.choices[0].message.content,
            "tokens_used": response.usage.total_tokens
        }
    
    async def generate_formula(self, query: str, column_names: list) -> dict:
        """
        Generates Google Sheets formula
        """
        prompt = f"""
You are a Google Sheets expert. Generate a formula based on user request.

AVAILABLE COLUMNS: {', '.join(column_names)}

USER REQUEST: {query}

Respond with JSON:
{{
  "formula": "=SUMIF(...)",
  "explanation": "Brief explanation in Russian",
  "confidence": 0.95
}}

Use Google Sheets functions (SUMIF, COUNTIF, VLOOKUP, etc).
Formula must be ready to paste into cell.
"""
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a Google Sheets formula expert."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1  # Very low = precise formulas
        )
        
        return json.loads(response.choices[0].message.content)
```

---

## 💾 Database Schema

### Users Table
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    google_id VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    subscription_tier VARCHAR(20) DEFAULT 'free',
    queries_used_this_month INTEGER DEFAULT 0,
    queries_limit INTEGER DEFAULT 20,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Query History Table
```sql
CREATE TABLE query_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    query_text TEXT NOT NULL,
    query_type VARCHAR(50), -- 'analyze', 'formula', 'report'
    response_time FLOAT, -- seconds
    tokens_used INTEGER,
    success BOOLEAN DEFAULT true,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Subscriptions Table
```sql
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    tier VARCHAR(20) NOT NULL, -- 'starter', 'pro', 'team'
    status VARCHAR(20) DEFAULT 'active', -- 'active', 'cancelled', 'expired'
    price INTEGER NOT NULL, -- in kopecks (490₽ = 49000)
    billing_cycle VARCHAR(20) DEFAULT 'monthly',
    next_billing_date DATE,
    created_at TIMESTAMP DEFAULT NOW(),
    cancelled_at TIMESTAMP
);
```

---

## 🔐 Authentication Flow
```
1. User installs Add-on from Marketplace
2. Apps Script requests OAuth consent (Google account)
3. Backend receives Google OAuth token
4. Backend verifies with Google API
5. Backend creates/updates user record
6. Backend issues JWT token
7. Apps Script stores JWT in PropertiesService
8. All API calls include JWT in Authorization header
```

### JWT Token Structure
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "subscription_tier": "pro",
  "exp": 1234567890
}
```

---

## 📊 Rate Limiting

### Free Tier
- 20 queries/month
- If exceeded → show upgrade prompt

### Paid Tiers
- Track queries_used_this_month in DB
- Reset on 1st of each month
- If exceeded → soft limit (warn user, still works)

### API Rate Limiting
- 10 requests/minute per user
- 1000 requests/hour globally
- Prevents abuse

---

## 🚀 Deployment

### Backend Deployment (Railway.app)
```
1. Connect GitHub repo
2. Railway auto-detects FastAPI
3. Set environment variables:
   - DATABASE_URL
   - OPENAI_API_KEY
   - JWT_SECRET
4. Deploy → get public URL
```

### Frontend Deployment (Google Apps Script)
```
1. Open script.google.com
2. Create new project
3. Paste Code.gs, Sidebar.html
4. Publish → Deploy as Add-on
5. Submit to Google Workspace Marketplace
```

### Database (Supabase or Railway PostgreSQL)
```
1. Create PostgreSQL instance
2. Run migration scripts
3. Set DATABASE_URL in backend env
```

---

## 📈 Monitoring

### Key Metrics to Track
- API response time (target: <3s)
- Error rate (target: <5%)
- GPT-4 token usage (cost control)
- User query success rate (target: >90%)

### Tools
- **Sentry** for error tracking
- **PostHog** for product analytics
- **Railway logs** for debugging

---

## 🧪 Testing Strategy

### Unit Tests
- Backend API endpoints (pytest)
- AI service (mock OpenAI responses)

### Integration Tests
- Full flow: Apps Script → Backend → DB
- Test with sample sheet data

### Manual Testing
- Install Add-on in test Google Sheet
- Run through all user scenarios
- Check edge cases (empty sheet, Cyrillic names)

---

## 💰 Cost Estimates (Monthly)

### MVP Costs
```
OpenAI API (GPT-4o-mini):
- 1000 queries × 2K tokens avg = 2M tokens
- $0.15 per 1M input tokens = $0.30
- $0.60 per 1M output tokens = $1.20
Total: ~$1.50/month for 1000 queries

Backend Hosting (Railway):
- Free tier: $0
- Paid tier (if needed): $5/month

Database (Supabase):
- Free tier: $0 (up to 500MB)

Domain:
- sheetgpt.ru = ~500₽/year = 42₽/month

TOTAL: ~$7/month = 700₽/month
```

### At Scale (300 paying users)
```
OpenAI: ~$150/month (100K queries)
Railway: $20/month (Pro plan)
Database: $25/month (Supabase Pro)

TOTAL: ~$200/month

Revenue: 300 × 600₽ avg = 180,000₽
Costs: $200 = 20,000₽
Profit: 160,000₽/month (89% margin)
```

---

## 🔧 Configuration Files

### .env (Backend)
```bash
DATABASE_URL=postgresql://user:pass@host:5432/sheetgpt
OPENAI_API_KEY=sk-...
JWT_SECRET=random-secret-key-here
ENVIRONMENT=production
CORS_ORIGINS=["https://script.google.com"]
```

### appsscript.json (Frontend)
```json
{
  "timeZone": "Europe/Moscow",
  "dependencies": {
    "enabledAdvancedServices": []
  },
  "exceptionLogging": "STACKDRIVER",
  "runtimeVersion": "V8",
  "oauthScopes": [
    "https://www.googleapis.com/auth/spreadsheets.currentonly",
    "https://www.googleapis.com/auth/script.external_request"
  ],
  "webapp": {
    "access": "ANYONE",
    "executeAs": "USER_DEPLOYING"
  }
}
```
