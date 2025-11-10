# SheetGPT - Product Requirements Document

## 🎯 Product Vision
AI assistant that works inside Google Sheets, helping users analyze data and create formulas using natural language instead of complex syntax.

## 👤 Target User
Sales managers, marketers, small business owners who:
- Work with Google Sheets daily
- Spend 3-10 hours/week on reports and analysis
- Don't know advanced formulas
- Want results fast without learning Excel/Sheets syntax

## 🎭 Core User Story
**Dmitry, Sales Manager:**
"I need to analyze why sales dropped last month. Usually takes me 3 hours with pivot tables. With SheetGPT, I just ask 'Why did sales drop in October?' and get answer in 30 seconds."

---

## ✨ Core Features (MVP)

### Feature 1: AI Sidebar
**What:** Persistent sidebar in Google Sheets where user types requests in natural language

**User Flow:**
1. User opens Google Sheets
2. Extensions → SheetGPT → Open (sidebar appears on right)
3. User types: "Find customers who bought >500K"
4. AI analyzes sheet, creates formula/filter
5. Result inserted into sheet

**Success Criteria:**
- Sidebar loads <2 seconds
- AI responds <15 seconds
- 90%+ queries work correctly

---

### Feature 2: Formula Generation
**What:** User describes what they want, AI creates the correct Google Sheets formula

**Examples:**
```
User: "Sum of sales where amount > 500000"
AI creates: =SUMIF(B:B, ">500000", B:B)

User: "Average order value per customer"
AI creates: =AVERAGEIF(A:A, "Customer X", B:B)

User: "Count unique customers"
AI creates: =COUNTA(UNIQUE(A:A))
```

**Edge Cases:**
- Sheet has 10,000+ rows (AI should use ranges, not full columns)
- Multiple sheets (AI needs to know which sheet)
- Cyrillic column names (must work)
- Date formats (DD.MM.YYYY vs MM/DD/YYYY)

**Success Criteria:**
- 90% formulas work without errors
- User doesn't need to edit formula
- Works with Russian column names

---

### Feature 3: Data Analysis
**What:** User asks analytical question, AI examines data and provides insights

**Examples:**
```
User: "Why did sales drop in October?"
AI Response:
"📉 Found 3 main reasons:
1. Product 'Coffee Machine Deluxe': -40% (-340K₽)
2. Manager Ivanov: -35% (-217K₽)  
3. Region St. Petersburg: -25%

Main cause: Coffee machines stopped selling in SPb.
September: 12 units, October: 2 units"
```

**What AI Should Do:**
1. Read all data from sheet
2. Compare time periods (if question about change)
3. Identify biggest contributors to change
4. Explain in simple language
5. Offer to create visualizations

**Success Criteria:**
- Analysis is factually correct
- Highlights top 3 causes
- Response in <30 seconds
- Clear actionable insights

---

### Feature 4: Automatic Reports
**What:** AI creates formatted report in new sheet based on user request

**Example:**
```
User: "Create weekly sales report"

AI Creates New Sheet:
┌─────────────────────────────────┐
│ WEEKLY SALES REPORT            │
│ Nov 4-10, 2024                 │
│                                 │
│ Total Sales: 1,240,000₽        │
│ Change: +12% vs last week      │
│                                 │
│ TOP PERFORMERS:                │
│ 1. Petrov: 420,000₽           │
│ 2. Ivanov: 380,000₽           │
│                                 │
│ [Chart automatically inserted] │
└─────────────────────────────────┘
```

**Success Criteria:**
- Report is formatted nicely
- Includes relevant metrics
- Chart/graph auto-generated
- Takes <20 seconds

---

## 🚫 NOT in MVP

These are good ideas but NOT for first version:
- ❌ Error checking (proactive warnings about formula errors)
- ❌ Voice input
- ❌ Scheduled reports (automatic weekly emails)
- ❌ Multi-sheet analysis
- ❌ Excel support (only Google Sheets)
- ❌ Templates library
- ❌ Team collaboration features

**Why not?** Focus on core value first. Add later if users want.

---

## 💰 Monetization

### Free Tier
- 20 queries/month
- All features available
- Goal: let users try and get hooked

### Paid Tier: STARTER (490₽/month = $5)
- 200 queries/month
- All features
- Priority processing (faster)

### Paid Tier: PRO (1,490₽/month = $15)
- 1000 queries/month
- All features
- Automatic reports (up to 5)
- Priority support

### Paid Tier: TEAM (4,990₽/month = $50)
- Unlimited queries
- Up to 10 users
- Shared templates
- Admin dashboard

---

## 📊 Success Metrics

### Activation
- User installs → opens sidebar → makes first query
- Target: 50%+ activation rate

### Retention
- User makes query week 1 → returns week 2
- Target: 40%+ week 1 retention

### Conversion
- Free user → paid user
- Target: 20% conversion (industry standard: 15-25%)

### Churn
- Paid user cancels subscription
- Target: <25% monthly churn

---

## 🎨 UX Principles

1. **Zero Learning Curve**
   User should understand what to do in 3 seconds

2. **Instant Gratification**
   First query should WOW the user (magic moment)

3. **Forgiving**
   If query unclear, ask clarifying question (don't fail)

4. **Transparent**
   Show what AI is doing ("Analyzing 200 rows...")

5. **Fast**
   <15 seconds response time (users won't wait more)

---

## 🔐 Security & Privacy

### Data Access
- Add-on only accesses sheets where user installed it
- NO access to other user's sheets
- Data sent to backend for AI processing
- Data NOT stored permanently (only during query)

### API Security
- HTTPS only
- API keys encrypted
- Rate limiting (prevent abuse)

### User Privacy
- No PII stored without consent
- GDPR compliant (user can delete all data)
- Transparent privacy policy

---

## 🌍 Localization

### MVP: Russian First
- All UI in Russian
- AI understands Russian queries
- Works with Cyrillic column names

### Later: English
- After MVP proven in Russian market

---

## 📱 Platform Support

### MVP: Desktop Only
- Google Sheets on desktop browser
- Chrome, Firefox, Safari, Edge

### Later: Mobile
- Google Sheets mobile app
- After desktop is stable