# SheetGPT - MVP Development Roadmap

## 🎯 MVP Goal
Launch functional Add-on that can:
1. Generate formulas from natural language
2. Analyze data and answer questions
3. Create basic reports
4. Accept payments

**Target: 4 weeks to launch**

---

## 📅 Week-by-Week Plan

### WEEK 1: Backend Foundation
**Goal:** Backend API working locally

#### Day 1-2: Project Setup
- [ ] Initialize FastAPI project
- [ ] Set up PostgreSQL locally (Docker)
- [ ] Create database schema (users, query_history, subscriptions)
- [ ] Set up SQLAlchemy models
- [ ] Test DB connection

#### Day 3-4: Core API Endpoints
- [ ] POST /api/v1/formula
  - Accept query + sheet data
  - Call OpenAI GPT-4o-mini
  - Return formula
- [ ] POST /api/v1/analyze
  - Accept query + sheet data
  - Call OpenAI
  - Return analysis

#### Day 5-7: Authentication & Rate Limiting
- [ ] Implement JWT auth
- [ ] Google OAuth integration (verify tokens)
- [ ] User registration flow
- [ ] Rate limiting (queries per month)
- [ ] Test all endpoints with Postman

**Deliverable:** Working backend API (local)

---

### WEEK 2: Frontend (Google Apps Script)
**Goal:** Working Add-on that calls backend

#### Day 1-2: Apps Script Setup
- [ ] Create new Apps Script project
- [ ] Set up basic sidebar UI (HTML/CSS)
- [ ] Test sidebar opens in Google Sheets

#### Day 3-4: Backend Integration
- [ ] Implement API calls from Apps Script
- [ ] Send sheet data to backend
- [ ] Display results in sidebar
- [ ] Handle loading states

#### Day 5: Formula Insertion
- [ ] Get formula from backend
- [ ] Insert into active cell
- [ ] Test with various formulas

#### Day 6-7: Polish UI
- [ ] Add example queries
- [ ] Show query count remaining
- [ ] Error handling
- [ ] Loading animations

**Deliverable:** Working Add-on (can generate formulas)

---

### WEEK 3: Core Features + Payments
**Goal:** Full feature set + monetization

#### Day 1-2: Analysis Feature
- [ ] Implement data analysis flow
- [ ] Format analysis results nicely
- [ ] Add charts/visualizations (basic)

#### Day 3-4: Report Generation
- [ ] Create new sheet with report
- [ ] Format cells (bold headers, colors)
- [ ] Insert charts automatically

#### Day 5-7: Payments
- [ ] Integrate ЮKassa (or Stripe)
- [ ] Subscription management
- [ ] Upgrade flow in sidebar
- [ ] Webhook handlers (payment success/fail)

**Deliverable:** Feature-complete MVP

---

### WEEK 4: Testing + Deployment
**Goal:** Live in production

#### Day 1-2: Testing
- [ ] Manual testing all flows
- [ ] Test with 10+ real queries
- [ ] Fix critical bugs
- [ ] Test payment flow end-to-end

#### Day 3-4: Deployment
- [ ] Deploy backend to Railway
- [ ] Set up production database (Supabase)
- [ ] Configure environment variables
- [ ] Test production API

#### Day 5-6: Publish Add-on
- [ ] Prepare Google Workspace Marketplace listing
  - Screenshots
  - Video demo
  - Description
- [ ] Submit for review
- [ ] Create landing page (simple)

#### Day 7: Launch
- [ ] Announce on social media
- [ ] Email beta testers
- [ ] Monitor errors/bugs
- [ ] Quick fixes if needed

**Deliverable:** SheetGPT live in Google Workspace Marketplace

---

## 🎯 Success Criteria

By end of Week 4:
- ✅ Add-on is published and installable
- ✅ Core features work (formulas, analysis, reports)
- ✅ Payments work
- ✅ At least 10 beta testers have used it successfully
- ✅ API uptime >95%
- ✅ Response time <5s

---

## 🚨 Risk Mitigation

### Risk 1: OpenAI API errors
**Solution:** Implement retry logic + fallback to simpler model

### Risk 2: Apps Script limitations
**Solution:** Keep UI simple, move complex logic to backend

### Risk 3: Marketplace approval delays
**Solution:** Submit early (Day 25), continue fixing bugs during review

### Risk 4: Payment integration issues
**Solution:** Start with simple one-time payments, add subscriptions later if needed

---

## 📦 Post-MVP (Week 5+)

Once MVP is live, prioritize based on user feedback:

**High Priority:**
- Error checking (proactive warnings)
- Multi-sheet support
- Better visualizations

**Medium Priority:**
- Automatic scheduled reports
- Templates library
- Team features

**Low Priority:**
- Voice input
- Excel support
- Mobile optimization