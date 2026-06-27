"""RAG-grounded reply generation with tone adaptation and a confidence score."""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.ai.client import chat_json
from app.rag.store import retrieve

# Tone guidance keyed by sentiment, with category overrides applied separately.
_TONE_BY_SENTIMENT = {
    "Angry": "firm but empathetic, solution-first, acknowledge the frustration directly",
    "Frustrated": "patient and reassuring, acknowledge the delay and offer a concrete resolution",
    "Sad / Distressed": "warm, human, and caring; prioritise reassurance",
    "Neutral": "professional, clear, and concise",
    "Happy / Positive": "friendly, warm, and brand-forward",
}

_SYSTEM = """You are a customer support agent for Northwind Gear, an outdoor & fitness
e-commerce retailer. Write a reply to the customer's email.

HARD RULES:
- Ground every factual claim ONLY in the provided Knowledge Base context. If the KB does
  not contain the answer, do not invent policy — say a human teammate will follow up.
- Never admit legal liability. For legal/regulatory matters, keep it brief and say the
  matter has been escalated to the appropriate team.
- Match the requested tone. Keep replies tight and skimmable.
- Include relevant specifics from the KB (timeframes, steps, RMA format) where helpful.

Return STRICT JSON:
{
  "reply": "<the full email reply body, ready to send, with a greeting and sign-off as 'The Northwind Gear Team'>",
  "confidence": <float 0..1 — how well the KB context covers this question; low if KB lacks the answer>,
  "used_kb": [<titles of KB articles you actually relied on>]
}"""


def generate_reply(
    db: Session,
    *,
    subject: str,
    body: str,
    category: str,
    sentiment: str,
    summary: str = "",
    top_k: int = 3,
) -> dict[str, Any]:
    # Retrieve KB context using the email content + AI summary as the query.
    query = f"{subject}\n{summary}\n{body}"
    sources = retrieve(db, query, top_k=top_k)
    kb_context = "\n\n".join(
        f"### {s['title']} ({s['category'] or 'General'})\n{s['content']}" for s in sources
    ) or "(no relevant KB articles found)"

    tone = _TONE_BY_SENTIMENT.get(sentiment, "professional and concise")
    if category == "Legal":
        tone = "brief, formal, non-committal; confirm escalation to the legal team"

    user = (
        f"Category: {category}\nSentiment: {sentiment}\nDesired tone: {tone}\n\n"
        f"--- KNOWLEDGE BASE CONTEXT ---\n{kb_context}\n\n"
        f"--- CUSTOMER EMAIL ---\nSubject: {subject}\n\n{body}"
    )

    result = chat_json(_SYSTEM, user, temperature=0.4)

    confidence = result.get("confidence", 0.5)
    try:
        confidence = max(0.0, min(1.0, float(confidence)))
    except (TypeError, ValueError):
        confidence = 0.5

    return {
        "reply": result.get("reply", "").strip(),
        "tone": tone,
        "confidence": confidence,
        "kb_sources": result.get("used_kb", []) or [s["title"] for s in sources],
        "retrieved": sources,
    }
