# SheetGPT - AI Assistant for Google Sheets

AI-powered assistant that helps users work with Google Sheets using natural language.

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL (or use SQLite for development)
- Gemini API key (get from https://makersuite.google.com/app/apikey)

### Installation

1. **Clone repository**
   ```bash
   cd backend
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env and add your Gemini API key
   ```

4. **Run the server**
   ```bash
   # From backend directory
   python -m uvicorn app.main:app --reload
   ```

5. **Check it's working**
   - API: http://localhost:8000
   - Docs: http://localhost:8000/docs
   - Health: http://localhost:8000/health

## 📋 Project Structure

```
sheetgpt/
├── backend/
│   ├── app/
│   │   ├── api/              # API endpoints
│   │   │   └── formula.py    # Formula generation
│   │   ├── models/           # Database models
│   │   │   ├── user.py
│   │   │   └── subscription.py
│   │   ├── schemas/          # Pydantic schemas
│   │   │   ├── requests.py
│   │   │   └── responses.py
│   │   ├── services/         # Business logic
│   │   │   └── ai_service.py # Gemini integration
│   │   ├── core/             # Core functionality
│   │   │   ├── config.py     # Settings
│   │   │   └── database.py   # DB connection
│   │   └── main.py           # FastAPI app
│   ├── requirements.txt
│   └── .env
├── frontend/                 # Google Apps Script (TODO)
└── docs/                     # Documentation
```

## 🧪 Testing API

### Test Formula Generation

```bash
curl -X POST http://localhost:8000/api/v1/formula \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Сумма продаж где сумма больше 500000",
    "column_names": ["Дата", "Продажи", "Менеджер"],
    "sheet_data": [
      ["2024-01-01", 600000, "Иванов"],
      ["2024-01-02", 400000, "Петров"]
    ]
  }'
```

**Expected response:**
```json
{
  "formula": "=SUMIF(B:B, \">500000\", B:B)",
  "explanation": "Суммирует все значения в столбце B которые больше 500,000",
  "target_cell": "D1",
  "confidence": 0.98
}
```

## 🔧 Configuration

### Environment Variables (.env)

```bash
# AI API Keys
GEMINI_API_KEY=your-key-here          # Required
OPENAI_API_KEY=your-key-here          # Optional (fallback)

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/sheetgpt

# JWT
JWT_SECRET_KEY=your-secret-key
```

### Get API Keys

1. **Gemini API Key**
   - Go to https://makersuite.google.com/app/apikey
   - Click "Create API Key"
   - Copy and paste to .env

2. **OpenAI API Key** (optional)
   - Go to https://platform.openai.com/api-keys
   - Create new key

## 📊 Database Setup

### Option 1: PostgreSQL (Production)

```bash
# Install PostgreSQL
# Ubuntu: sudo apt-get install postgresql
# Mac: brew install postgresql

# Create database
createdb sheetgpt

# Run migrations
alembic upgrade head
```

### Option 2: SQLite (Development)

```bash
# Just change DATABASE_URL in .env:
DATABASE_URL=sqlite+aiosqlite:///./sheetgpt.db
```

## 🚀 Deployment

### Deploy to Render.com (Free)

1. Push to GitHub
2. Go to render.com
3. New → Web Service
4. Connect GitHub repo
5. Set environment variables
6. Deploy!

## 🛠️ Development

### Add new endpoint

1. Create router in `app/api/`
2. Add to `app/main.py`:
   ```python
   from app.api import your_router
   app.include_router(your_router.router)
   ```

### Run with auto-reload

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 📖 API Documentation

Once server is running:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🐛 Troubleshooting

**"Module not found" error:**
```bash
# Make sure you're in backend directory
cd backend
python -m uvicorn app.main:app --reload
```

**"Gemini API key invalid":**
- Check your .env file
- Make sure GEMINI_API_KEY is set correctly
- Restart the server after changing .env

**Database connection error:**
- Check DATABASE_URL in .env
- Make sure PostgreSQL is running
- Or switch to SQLite for quick start

## 📝 TODO

- [ ] Implement /analyze endpoint (data analysis)
- [ ] Implement /report endpoint (report generation)
- [ ] Add authentication (JWT + Google OAuth)
- [ ] Add rate limiting
- [ ] Create Google Apps Script frontend
- [ ] Deploy to production

## 🤝 Contributing

See [docs/MVP_ROADMAP.md](docs/MVP_ROADMAP.md) for development plan.
