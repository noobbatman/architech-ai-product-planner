# ArchiTECH — AI Product Planner

> Turn a one-sentence product idea into a fully-populated Trello board in under 60 seconds.

ArchiTECH is an AI-powered product planning tool built at a hackathon.
You describe your idea in plain English; a crew of AI agents simulates
1,000 customers, analyses their feedback, writes developer-ready user
stories, and pushes them directly to your Trello board — automatically.

## Demo


---

## How it works

```
Your idea (1 sentence)
        │
        ▼
  Customer Crew ──► 1,000 simulated users give feedback
        │
        ▼
  Analyst Agent ──► Finds top themes & pain points
        │
        ▼
    PM Agent ──► Writes user stories + acceptance criteria
        │
        ▼
  Trello Bot ──► Pushes cards to your project board
```

**Example input:** "An app that helps people find local dog walkers."

**Example output:** A fully-formed Trello board with cards like:
- *"As a user, I want to see reviews for a dog walker so that I can
  trust them with my pet."*
- *"As a user, I want to pay securely in-app so I don't need cash."*

---

## My role — Backend Developer & Project Lead

This was a 4-person hackathon team. I was responsible for the entire
Python backend and overall system architecture.

**What I built:**
- Designed the FastAPI backend and RESTful API contract consumed by
  the Next.js frontend
- Architected and implemented the multi-agent pipeline using CrewAI —
  Customer Crew, Analyst Agent, PM Agent, and Trello Bot
- Set up the SQLAlchemy ORM models and PostgreSQL schema (via Supabase)
  for storing users, projects, and generated backlogs
- Integrated the Trello REST API for automatic card creation using
  OAuth 2.0 authentication
- Configured pgvector extension for future vector embedding storage
  (planned "Listen Mode" feature)
- Led technical decisions: stack selection, agent orchestration
  strategy, API design

**My teammates:**
- Frontend: Next.js / React / TypeScript UI
- AI/ML: LLM prompt engineering, Gemini API integration
- UX/Design: User flows and product strategy

---

## What I learnt

- **Multi-agent AI orchestration** with CrewAI — how to design agents
  with defined roles, tools, and handoff logic
- **Prompt engineering at scale** — structuring prompts so that LLMs
  (Gemini/GPT-4o) produce consistent, structured output (user stories
  with proper acceptance criteria)
- **FastAPI async patterns** for AI-heavy endpoints that involve
  multiple sequential LLM calls
- **OAuth 2.0 integration** with a third-party API (Trello)
- **Rapid prototyping under time pressure** — making scope decisions
  and shipping a working demo in a hackathon window

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI (Python) |
| AI Agents | CrewAI + Google Gemini / GPT-4o |
| Frontend | Next.js + TypeScript (team member) |
| Database | PostgreSQL via Supabase |
| Vector store | pgvector (for future Listen Mode) |
| Integration | Trello REST API + OAuth 2.0 |

---

## Run locally

```bash
# Clone the repo
git clone https://github.com/noobbatman/architech-ai-product-planner
cd architech-ai-product-planner/architech_backend

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Add: GEMINI_API_KEY, TRELLO_API_KEY, DATABASE_URL

# Start the backend
uvicorn main:app --reload
```

API docs: http://localhost:8000/docs

---

## Roadmap
- [ ] "Listen Mode" — connect to real user feedback sources
  (Zendesk, App Store reviews) and auto-suggest backlog items
- [ ] Jira integration alongside Trello
- [ ] Analytics dashboard showing why features were prioritised
- [ ] SaaS pricing tiers (Free / Pro / Enterprise)
