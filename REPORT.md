# AI-Powered Customer Email Automation — Project Report

*A plain-language, end-to-end explanation of how the system works.*

**Live app:** https://ai-email-s67p.onrender.com
**Stack:** FastAPI (Python) · React · Groq LLM · Gmail API · PostgreSQL (Neon) · Docker · Render

---

## 1. What this project does (in one paragraph)

This is an assistant that watches a customer-support Gmail inbox and handles incoming
emails automatically. The moment an email arrives, the system reads it, figures out what
it's about (e.g. a refund request or a delivery complaint), senses the customer's mood
(angry, happy, neutral…), writes a ready-to-send reply using the company's own help
documents, and decides whether a human needs to step in (for example, anything involving
lawyers or VIP customers). A web dashboard shows everything at a glance and lets an agent
approve replies with one click. The goal: emails that used to take hours of manual sorting
get triaged and answered in seconds.

---

## 2. The big picture (how the pieces fit together)

```
        ┌──────────────┐
        │  Gmail inbox │   (real customer emails)
        └──────┬───────┘
               │  every 60 seconds, "is there new mail?"
               ▼
        ┌──────────────────────────────────────────────┐
        │              BACKEND (FastAPI)                 │
        │                                                │
        │   1. Poller fetches new emails                 │
        │   2. AI analyses each email   ──► Groq LLM     │
        │   3. RAG finds relevant help docs ─► Knowledge │
        │   4. AI writes a reply        ──► Groq LLM     │
        │   5. Rules decide: auto-handle or escalate?    │
        │   6. Everything saved          ──► PostgreSQL  │
        └──────┬─────────────────────────────────────────┘
               │  REST API (JSON over HTTP)
               ▼
        ┌──────────────┐
        │  DASHBOARD   │   (React web app: inbox, replies,
        │  (browser)   │    escalations, analytics, KB)
        └──────────────┘
```

Think of the backend as the "brain" that does the thinking, the database as its "memory,"
Gmail as the "mailbox" it watches, the Groq LLM as the "language expert" it consults, and
the dashboard as the "control panel" a human uses.

---

## 3. The tools used, and why

| Tool | What it is | Why we chose it |
|------|-----------|-----------------|
| **FastAPI** (Python) | Web framework for the backend/API | Fast, modern, great for AI work, auto-generates API docs |
| **React + Vite** | Frontend dashboard | Standard for interactive single-page apps; Vite builds it instantly |
| **Groq** (`llama-3.3-70b-versatile`) | The Large Language Model (the "AI brain") | Free tier with no credit card, very fast, OpenAI-compatible |
| **Gmail API + OAuth 2.0** | Reads/sends the actual emails | The real inbox source; OAuth lets us connect securely without passwords |
| **PostgreSQL (Neon)** | The database (memory) | Free hosted Postgres; data survives restarts |
| **SQLAlchemy** | Talks to the database from Python | Lets us use Python objects instead of raw SQL |
| **Docker** | Packages the whole app into one box | "Works on my machine" → works everywhere, including the cloud |
| **Render** | Cloud host | Free tier, auto-deploys from GitHub |

**Important design choice — provider-agnostic AI:** The code is written so the AI provider
can be swapped between **Groq, Google Gemini, or OpenAI** by changing one setting
(`LLM_PROVIDER`). They all share the same "OpenAI-compatible" interface, so switching is a
config change, not a code rewrite. We landed on Groq because it was the only one that gave
a working free key without billing setup.

---

## 4. The pipeline, step by step (following one email)

Let's follow a real example email through the entire system:

> **From:** priya@example.com
> **Subject:** How do I return a jacket?
> **Body:** "Hi, I bought a jacket last week but it's too small. How do I return it and how long does the refund take? Do I need an RMA number?"

### Step 1 — The email is fetched (Gmail polling)
Every 60 seconds a background task asks Gmail: *"Any inbox emails I haven't handled yet?"*
It identifies new mail using a Gmail label called **`AI-Processed`** — any email *without*
that label is considered new. It downloads the new email and pulls out the sender, subject,
body, and any attachments.
*(Files: `app/gmail/poller.py`, `app/gmail/client.py`)*

### Step 2 — The email is understood (analysis)
The email text is sent to the Groq LLM with a carefully written instruction ("system
prompt") that says, in effect: *"You are an email triage engine. Read this and reply in
strict JSON with the category, sentiment, intent, and whether this looks like a VIP."*

The AI returns structured data like:
```json
{
  "category": "Return / Refund",
  "sentiment": "Neutral",
  "intent": ["seeking_information"],
  "is_vip": false,
  "summary": "Customer wants to return a jacket and asks about refund timing and RMA",
  "reasoning": "Asks how to return and refund timeframe"
}
```

- **Category** — one of 8 buckets: Legal, Product Issue, Delivery Issue, Return/Refund,
  Billing, General Enquiry, Feedback/Praise, Spam/Irrelevant.
- **Sentiment** — the customer's mood: Angry, Frustrated, Sad/Distressed, Neutral,
  Happy/Positive.
- **Intent** — what they want: immediate resolution, information, threatening escalation,
  repeat contact, high-value customer.
- **VIP flag** — does this sound like an important/enterprise customer?

*(File: `app/ai/analyze.py`)*

### Step 3 — Relevant help docs are found (RAG)
Before writing a reply, the system looks up the **company knowledge base** to ground the
answer in real policy (so the AI doesn't make things up). This is called **RAG —
Retrieval-Augmented Generation**. Here's how it works in plain terms:

1. The knowledge base is a document of help articles (return policy, refund times, RMA
   rules, shipping, billing, etc.) — see `data/knowledge_base.md`.
2. Each article was turned into a list of numbers called an **embedding** — a "meaning
   fingerprint." Articles about similar topics have similar fingerprints.
3. The customer's question is also turned into an embedding.
4. We compare the question's fingerprint to every article's fingerprint using **cosine
   similarity** (a math measure of "how alike are these two fingerprints?") and pick the
   **top 3 closest articles**.

For Priya's email, RAG pulls up *"RMA Numbers & Return Tracking"* and *"Return & Exchange
Policy"* — exactly the right docs.
*(Files: `app/rag/store.py`, `data/knowledge_base.md`)*

> **Note on embeddings:** When using Gemini/OpenAI, real AI embeddings are used. Groq has
> no embedding service, so the system falls back to a simple built-in method (a
> word-based fingerprint). It's less precise but keeps everything working for free and
> still retrieves the right articles in practice.

### Step 4 — A reply is written (grounded generation)
Now the system asks the Groq LLM again, this time giving it three things: the customer's
email, the retrieved help articles, and a **tone instruction** based on the sentiment
(e.g. *"empathetic and solution-first"* for an angry customer, *"professional and concise"*
for a neutral one; for Legal emails the tone is *"brief, formal, escalate"*).

The AI is told to **only use facts from the provided help articles** and to never admit
legal liability. It returns the reply text plus a **confidence score** (0 to 1) — how sure
it is that the help docs actually covered the question.

For Priya, it wrote a complete reply explaining the RMA process, the $6 return fee, and the
5-day refund timing — all pulled from the knowledge base — with confidence `1.0`.
*(File: `app/ai/reply.py`)*

### Step 5 — Decide: handle automatically or call a human? (escalation)
A rule engine checks whether a human must review the email. It escalates if **any** of
these are true:

1. **Legal** — anything mentioning lawsuits, GDPR, regulators, solicitors/attorneys.
2. **Angry + persistent** — sentiment is Angry *and* it's the 3rd-or-more email in the
   same conversation thread.
3. **VIP** — the customer looks high-value/enterprise.
4. **Low confidence** — the AI's confidence in its reply is below 70%.
5. **Attachments** — the email has files that may need human eyes (e.g. legal docs).
6. *(Bonus)* **Threatening escalation** — customer threatens to go to social media/legal.

Priya's email triggers none of these, so it's safely handled automatically (status:
*drafted*, waiting for one-click approval). A legal threat, by contrast, would be flagged
and routed to a human immediately.
*(File: `app/ai/escalation.py`)*

### Step 6 — Everything is saved and shown
All of the above — the email, its analysis, the draft reply, the KB sources used, and any
escalation reasons — is saved to the database. The email gets the `AI-Processed` label in
Gmail so it's never handled twice. The dashboard then displays it instantly.
*(Files: `app/ai/pipeline.py` orchestrates all steps; `app/models.py` defines the data)*

### Step 7 — A human approves (or it auto-sends)
The system has two modes:
- **Approve mode** (default): the AI writes a draft, a human reviews/edits it in the
  dashboard, and clicks **Approve & Send** — which sends it through Gmail.
- **Auto-send mode**: confident, non-escalated replies are sent automatically.

*(File: `app/routers/replies.py`)*

---

## 5. The dashboard (what the human sees)

A single-page React app with four tabs:

- **Inbox** — every email with colour-coded badges (category, mood, status, VIP,
  attachments). Click one to read the full message, the AI's analysis, the draft reply
  (with the KB sources it used and a confidence bar), and to edit/approve/send it.
- **Escalations** — the queue of emails flagged for a human, each showing *why* it was
  flagged.
- **Analytics** — totals, a category breakdown, a sentiment breakdown, the % auto-handled,
  and the top reasons emails get escalated.
- **Knowledge Base** — browse the help articles and a **RAG preview** tool: type any
  customer question and see exactly which articles the AI would retrieve (and their
  similarity scores).

There's also a **"Simulate email"** button to inject a fake customer email and watch it go
through the whole pipeline — handy for demos without waiting for real mail.

---

## 6. How the data is stored (the database)

Five tables in PostgreSQL:

| Table | Holds |
|-------|-------|
| `emails` | each email + its AI analysis (category, sentiment, intent, VIP, status) |
| `replies` | AI/human draft replies (text, tone, confidence, KB sources, sent status) |
| `escalations` | which emails were escalated and the reasons |
| `kb_articles` | the knowledge base articles + their embedding fingerprints |
| `app_settings` | app state that must persist — notably the **Gmail login token** |

*(File: `app/models.py`)*

**Why the Gmail token is in the database:** Originally the login token was saved to a file.
On the free cloud host that file disappears when the server restarts, which made Gmail
"disconnect" itself. Moving the token into the database fixed this — it now survives
restarts and is shared between the local and deployed versions.

---

## 7. Connecting to Gmail securely (OAuth 2.0)

We never ask for or store a Gmail password. Instead we use **OAuth 2.0**, the standard
"Sign in with Google" flow:

1. The user clicks **Connect Gmail**.
2. They're sent to Google's official consent screen and approve the permissions (read
   email, send email, modify labels).
3. Google sends back a **token** — a temporary key that lets our app act on the inbox.
4. We store that token (in the database) and use it for all Gmail operations. It
   auto-refreshes when it expires.

During development the app is in Google's "Testing" mode, so only **approved test users**
(specific Gmail addresses we list) can connect — this is why a new account must be added
as a test user first.
*(Files: `app/gmail/auth.py`, `app/routers/gmail_routes.py`)*

---

## 8. How it's deployed (getting it online)

1. **One container, one service.** A multi-stage **Dockerfile** first builds the React
   dashboard, then packages it together with the Python backend. The backend serves the
   dashboard directly, so the whole app runs as a single web service on one URL (no CORS
   headaches, and the Gmail login redirect stays on one domain). *(File: `Dockerfile`)*
2. **Hosted on Render** (free tier), which rebuilds and redeploys automatically every time
   we push to GitHub.
3. **Database on Neon** (free hosted PostgreSQL) so data persists.
4. **Secrets** (the Groq key, Gmail credentials, database URL) are provided as environment
   variables / secret files on Render — never committed to the code.

**Free-tier trade-offs (acceptable for a prototype):**
- The server **sleeps after ~15 minutes** of no traffic; the first request afterward takes
  ~30–60 seconds to wake it (and the 60-second auto-poller pauses while asleep).
- Persistence is handled by Neon, so even when the server recycles, all data and the Gmail
  connection remain intact.

---

## 9. End-to-end example outcomes (real results from the system)

| Test email | Category | Sentiment | Outcome |
|-----------|----------|-----------|---------|
| "How do I return a jacket?" | Return / Refund | Neutral | Auto-drafted reply, confidence 1.0, no escalation |
| "GDPR request + I'll contact my solicitor" | Legal | Angry | **Escalated** (legal + low confidence) |
| "Where is my order?! 5 days late" (+ attachment) | Delivery Issue | Angry | **Escalated** (attachment + escalation threat) |
| "Love it — we're a big enterprise client" | Feedback / Praise | Happy | **Escalated** (VIP detected) |

---

## 10. Limitations & possible next steps

- **Embedding quality on Groq:** Groq has no embeddings, so RAG uses a basic local method.
  Switching `LLM_PROVIDER` to Gemini/OpenAI (with a working key) gives much sharper
  retrieval.
- **Single inbox:** one Gmail account at a time; multi-account is a straightforward
  extension.
- **Free-tier limits:** Groq has per-minute rate limits, so large bursts of email are
  processed gradually (the code retries automatically on rate limits).
- **No authentication on the dashboard yet:** anyone with the URL can view it — fine for a
  prototype, but a login would be added for production.
- **Future ideas:** push-based Gmail notifications (instead of 60s polling), Slack/Teams
  alerts on escalation, knowledge-base file uploads (PDF/DOCX) from the UI, and analytics
  over time.

---

## 11. Project file map (where everything lives)

```
ai-email-automation/
├── Dockerfile                 # builds frontend + backend into one image
├── render.yaml                # Render deploy config
├── README.md                  # setup instructions
├── REPORT.md                  # this document
├── backend/
│   ├── requirements.txt
│   ├── migrate_to_postgres.py # one-off SQLite → Postgres data migration
│   └── app/
│       ├── main.py            # app startup, 60s poller, serves frontend
│       ├── models.py          # database tables
│       ├── schemas.py         # API request/response shapes
│       ├── core/              # config + database connection
│       ├── ai/                # analyze, reply (RAG), escalation, pipeline, LLM client
│       ├── rag/               # knowledge-base loading + similarity search
│       ├── gmail/             # OAuth, Gmail API client, 60s poller
│       └── routers/           # API endpoints (emails, replies, escalations, kb, gmail, analytics)
└── frontend/
    └── src/
        ├── App.jsx            # dashboard shell + tabs
        ├── api.js             # talks to the backend
        └── components/        # Inbox, EmailDetail, Analytics, KnowledgeBase, SimulateModal, Badges
```

---

*Built as a working prototype: real Gmail integration, real LLM, real database, deployed to
the cloud — demonstrating the complete auto-triage → AI reply → human-escalation workflow.*
