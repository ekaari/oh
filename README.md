# AI Web Tester

Autonomous web application testing platform based on the Product Requirements Document (PRD) v1.0.

**Stack:** FastAPI + Playwright + React (TypeScript, Tailwind)

## Features (MVP)

- Project & environment management (SAFE / WARNING / DANGEROUS)
- Encrypted credentials (never sent to LLM prompts or reports in plaintext)
- Natural-language AI test missions
- Heuristic / optional LLM test planner
- Playwright browser agent: navigate, explore, forms, UI smoke, screenshots
- Console & network anomaly monitoring
- Bug pipeline: Detect → Analyze → Reproduce → Verify → Confirm
- HTML reports, test history, re-test / regression
- Natural-language query over run results
- Live dashboard

## Quick start

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env   # optional OPENAI_API_key for LLM planner
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

API docs: http://localhost:8000/docs

## User flow

1. Create a project with a base URL  
2. Configure environment & optional login credentials  
3. Create an AI mission in natural language  
4. Start test → planner → browser exploration → analysis → report  
5. Review bugs/evidence, ask NL questions, or re-test  

## Safety

Destructive actions (delete, payment submit, etc.) are blocked unless the environment explicitly allows them. Production should use `DANGEROUS` only with caution.
