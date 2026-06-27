# AI-Powered Customer Email Automation

A working prototype that connects to Gmail, auto-triages incoming customer emails,
drafts RAG-grounded replies from a company knowledge base, detects sentiment & intent,
flags legally-sensitive / high-risk threads for human review, and surfaces everything in
a React dashboard.

- **Backend:** Python · FastAPI · SQLAlchemy (SQLite) · OpenAI · Gmail API
- **Frontend:** React + Vite
- **RAG:** mock company KB (`backend/data/knowledge_base.md`) embedded into a lightweight
  SQLite-backed vector store with cosine similarity retrieval.

---

## Architecture

```
Gmail inbox ──poll(60s)──► Poller ──► [ AI Pipeline ] ──► SQLite ──► REST API ──► React dashboard
                                          │
                 analyze (category + sentiment + intent + VIP)
                                          │
                 RAG retrieve KB ─► draft reply (tone-adapted) + confidence
                                          │
                 escalation rules ─► human queue (legal / angry / VIP / low-conf / attachment)
```

Pipeline lives in [`backend/app/ai/pipeline.py`](backend/app/ai/pipeline.py):
`analyze → RAG reply → escalation decision → persist`.

---

## Prerequisites

- Python 3.11+
- Node 18+
- An **OpenAI API key**
- A **Google Cloud project** with the Gmail API enabled + an OAuth client (for real Gmail)

---

## 1. Backend setup

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then edit .env
```

Edit `backend/.env`:

```ini
OPENAI_API_KEY=sk-...your key...
OPENAI_CHAT_MODEL=gpt-4o-mini
REPLY_MODE=approve            # or auto_send
CONFIDENCE_THRESHOLD=0.7
ANGRY_CONTACT_THRESHOLD=3
```

Run it:

```bash
uvicorn app.main:app --reload --port 8000
```

On first boot it creates the SQLite DB and seeds the mock KB (14 articles). API docs at
http://localhost:8000/docs.

## 2. Gmail OAuth setup (for real inbox)

1. https://console.cloud.google.com → create a project.
2. **APIs & Services → Library → Gmail API → Enable**.
3. **OAuth consent screen**: User type *External*; add your Google account as a **Test user**.
4. **Credentials → Create OAuth client ID → Web application**. Add redirect URI:
   `http://localhost:8000/api/gmail/oauth/callback`
5. Download the JSON and save it as **`backend/credentials.json`**.
6. Start the app, open the dashboard, click **Connect Gmail**, approve.

Tokens are saved to `backend/token.json`. The poller then checks the inbox every 60s,
processes new mail, and applies an `AI-Processed` label to avoid double-handling.

> `credentials.json`, `token.json`, `.env`, and the DB are all gitignored.

## 3. Frontend setup

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173 (proxies /api to :8000)
```

---

## Using the prototype

- **Connect Gmail** (header) — real OAuth; or **+ Simulate email** to inject a test email
  through the full pipeline without waiting for real traffic.
- **Inbox** — all emails with category / sentiment / status badges; click to view the
  thread, AI analysis, and the RAG-grounded draft. Edit the draft, then **Approve & Send**
  (sends via Gmail for real emails). `auto_send` mode sends without approval.
- **Escalations** — the human-review queue with the reason each email was flagged.
- **Analytics** — volume, category & sentiment breakdowns, top escalation reasons.
- **Knowledge Base** — browse KB articles and preview which chunks RAG retrieves for any
  query.

## Escalation rules (brief §3.5)

An email is auto-escalated when any of these hold:
- Category = **Legal** (lawsuit, GDPR, regulator, solicitor/attorney)
- Sentiment = **Angry** AND it's the 3rd+ contact in the thread
- Customer flagged **VIP / high-value**
- AI reply **confidence < threshold** (default 0.70)
- Email has **attachments** needing human review

## Categories

Legal · Product Issue · Delivery Issue · Return / Refund · Billing · General Enquiry ·
Feedback / Praise · Spam / Irrelevant

## Project layout

```
backend/
  app/
    core/      config + DB
    ai/        analyze, reply (RAG), escalation, pipeline, OpenAI client
    rag/       vector store + KB seeding
    gmail/     OAuth, API client, poller
    routers/   emails, replies, escalations, kb, gmail, analytics
    models.py  schemas.py  main.py
  data/        knowledge_base.md  (mock KB)  +  app.db
frontend/
  src/components/  Inbox, EmailDetail, Analytics, KnowledgeBase, SimulateModal, Badges
```

## Notes / prototype scope

- Knowledge base is mock data for a fictional retailer ("Northwind Gear"). Replace
  `backend/data/knowledge_base.md` (or POST to `/api/kb`) with real content.
- Single-inbox OAuth; multi-account is a straightforward extension.
- Vector store is in-DB cosine similarity — fine for a prototype KB; swap for a dedicated
  vector DB (pgvector, Chroma) at scale.
```
