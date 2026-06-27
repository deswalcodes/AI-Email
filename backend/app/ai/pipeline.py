"""End-to-end processing of a single email: analyze -> escalate -> draft reply.

This is the heart of the system, called both by the Gmail poller and by manual
re-processing endpoints. It mutates and persists the Email row.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Email, Reply, Escalation
from app.ai.analyze import analyze_email
from app.ai.reply import generate_reply
from app.ai.escalation import evaluate_escalation


def process_email(db: Session, email: Email) -> Email:
    """Run the full AI pipeline on `email` and persist all results."""
    # 1. Analyze (category, sentiment, intent, VIP).
    analysis = analyze_email(email.subject or "", email.body, email.sender)
    email.category = analysis["category"]
    email.sentiment = analysis["sentiment"]
    email.intent = analysis["intent"]
    email.is_vip = analysis["is_vip"]
    email.analysis = analysis

    # 2. Generate a RAG-grounded draft reply (skip drafting for pure spam).
    reply_data = None
    if analysis["category"] != "Spam / Irrelevant":
        reply_data = generate_reply(
            db,
            subject=email.subject or "",
            body=email.body,
            category=analysis["category"],
            sentiment=analysis["sentiment"],
            summary=analysis.get("summary", ""),
        )

    confidence = reply_data["confidence"] if reply_data else None

    # 3. Escalation decision.
    reasons = evaluate_escalation(db, email, analysis=analysis, confidence=confidence)

    # Persist reply draft.
    if reply_data:
        reply = Reply(
            email_id=email.id,
            body=reply_data["reply"],
            tone=reply_data["tone"],
            confidence=reply_data["confidence"],
            kb_sources=reply_data["kb_sources"],
            is_ai=True,
        )
        db.add(reply)

    # Persist escalation + set status.
    if reasons:
        email.status = "escalated"
        db.add(Escalation(email_id=email.id, reasons=reasons))
    elif reply_data and settings.reply_mode == "auto_send":
        # Auto-send mode: mark the draft as sent immediately.
        email.status = "replied"
    elif reply_data:
        email.status = "drafted"
    else:
        email.status = "open"  # spam left as-is

    # Auto-send: flip the reply to sent (actual Gmail send handled by caller for real mail).
    if email.status == "replied" and reply_data:
        db.flush()
        sent_reply = email.replies[-1] if email.replies else None
        if sent_reply:
            sent_reply.sent = True
            sent_reply.sent_at = datetime.now(timezone.utc)
            sent_reply.approved_by = "auto"

    email.processed = True
    db.commit()
    db.refresh(email)
    return email
