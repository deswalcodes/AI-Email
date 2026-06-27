"""FastAPI application entrypoint: wiring, startup, and background Gmail polling."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.db import init_db, SessionLocal
from app.rag.store import seed_kb_from_file
from app.gmail import auth
from app.gmail.poller import poll_once
from app.routers import emails, replies, escalations, kb, gmail_routes, analytics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app")

POLL_INTERVAL_SECONDS = 60  # brief 3.1: poll every 60s


async def _poll_loop():
    """Background task: poll Gmail every 60s while connected."""
    while True:
        try:
            if auth.is_connected():
                summary = await asyncio.to_thread(poll_once)
                if summary.get("ingested"):
                    logger.info("Poll: %s", summary)
        except Exception:
            logger.exception("Background poll failed")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # Seed the mock KB on first run. A bad/missing OpenAI key must NOT crash startup —
    # embeddings will fail, so we warn and leave the KB unseeded; POST /api/kb/seed
    # re-runs it once a valid key is in place.
    db = SessionLocal()
    try:
        n = seed_kb_from_file(db)
        if n:
            logger.info("Seeded %d KB articles", n)
    except Exception as exc:
        logger.warning("KB seeding skipped (embeddings failed): %s. "
                       "Fix OPENAI_API_KEY then POST /api/kb/seed.", exc)
    finally:
        db.close()
    if not settings.has_llm:
        logger.warning("No LLM API key set (provider=%s) — AI endpoints will error.",
                       settings.llm_provider)

    task = asyncio.create_task(_poll_loop())
    yield
    task.cancel()


app = FastAPI(title="AI Email Automation", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (emails, replies, escalations, kb, gmail_routes, analytics):
    app.include_router(r.router)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "llm_provider": settings.llm_provider,
        "llm_configured": settings.has_llm,
        "chat_model": settings.chat_model,
        "gmail_connected": auth.is_connected(),
        "reply_mode": settings.reply_mode,
    }


# Serve the built React frontend (production). In a Docker/Render build the Vite output
# is copied to backend/static. Mounted last so /api/* routes always take precedence.
# html=True makes "/" serve index.html. Registered after all API routes above.
from pathlib import Path  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

_STATIC_DIR = Path(__file__).resolve().parents[1] / "static"
if _STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(_STATIC_DIR), html=True), name="frontend")
    logger.info("Serving frontend from %s", _STATIC_DIR)
