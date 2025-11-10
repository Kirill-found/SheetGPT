# Claude Code Rules for SheetGPT

## Project Context
You are helping build SheetGPT - a Google Sheets Add-on with AI capabilities.

## Documentation
Always refer to:
- /docs/PRD.md - Product requirements
- /docs/TECH_SPEC.md - Technical architecture  
- /docs/MVP_ROADMAP.md - Development priorities
- /docs/AI_PROMPTS.md - GPT prompts (critical!)
- /agents/LEAD_AGENT.md - Your role as tech lead

## Code Standards

### Python (Backend)
```python
# Always use type hints
async def analyze_data(query: str, sheet_data: list[list]) -> dict:
    """Analyzes sheet data based on user query."""
    pass

# Use Pydantic for validation
from pydantic import BaseModel

class AnalyzeRequest(BaseModel):
    query: str
    sheet_data: list[list[str | int | float]]
    
# Error handling always
try:
    result = await openai_call()
except OpenAIError as e:
    logger.error(f"OpenAI failed: {e}")
    raise HTTPException(status_code=500, detail="AI service unavailable")
```

### JavaScript (Apps Script)
```javascript
// Always handle errors
function callBackend(endpoint, payload) {
  try {
    const response = UrlFetchApp.fetch(API_URL + endpoint, {
      method: 'post',
      payload: JSON.stringify(payload)
    });
    return JSON.parse(response.getContentText());
  } catch (error) {
    Logger.log('Error calling backend: ' + error);
    showError('Произошла ошибка. Попробуйте еще раз.');
  }
}

// Always show loading state
function showLoading() {
  document.getElementById('loading').style.display = 'block';
}
```

## MVP Principles
1. **Simple > Complex** - Always choose simpler solution
2. **Working > Perfect** - Ship working code, optimize later
3. **Core features only** - If not in MVP_ROADMAP.md, don't build it

## Before Writing Code
Ask yourself:
1. Is this in MVP scope? (check MVP_ROADMAP.md)
2. Is there a simpler way?
3. What can break? (add error handling)
4. How will I test this?

## Git Commits
Format: `[component] description`
Examples:
- `[backend] Add /analyze endpoint`
- `[frontend] Implement sidebar UI`
- `[docs] Update API documentation`

## When Stuck
1. Check documentation first
2. Refer to LEAD_AGENT.md (tech lead guidance)
3. Ask specific questions

## Testing
Every feature needs:
- [ ] Happy path test (basic usage works)
- [ ] Error handling test (graceful failures)
- [ ] Edge case test (empty data, Cyrillic, etc)

## Security Checklist
- [ ] No API keys in code (use environment variables)
- [ ] Input validation (Pydantic schemas)
- [ ] Rate limiting implemented
- [ ] SQL injection protected (use ORM)

## Performance
- Target: API responds <3s
- OpenAI calls: use GPT-4o-mini (cheap + fast)
- Database: indexes on frequently queried fields
- Cache: not needed in MVP

## Deployment
- Backend: Railway.app (auto-deploy from main branch)
- Database: Supabase PostgreSQL
- Frontend: Google Apps Script (manual publish)

Remember: Focus on MVP. Ship fast. Iterate based on user feedback.