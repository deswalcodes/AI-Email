"""Lightweight analytics for the dashboard (brief section 4: Analytics Dashboard)."""
from __future__ import annotations

from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import Email, Escalation

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/overview")
def overview(db: Session = Depends(get_db)):
    emails = db.query(Email).all()
    total = len(emails)
    replied = sum(1 for e in emails if e.status == "replied")
    escalated = sum(1 for e in emails if e.status == "escalated")
    drafted = sum(1 for e in emails if e.status == "drafted")

    category_counts = Counter(e.category for e in emails if e.category)
    sentiment_counts = Counter(e.sentiment for e in emails if e.sentiment)

    escalation_reasons: Counter = Counter()
    for esc in db.query(Escalation).all():
        for r in esc.reasons or []:
            # bucket by leading phrase before any dash/number for cleaner grouping
            escalation_reasons[r.split(" — ")[0].split(" (")[0]] += 1

    return {
        "total_emails": total,
        "replied": replied,
        "drafted": drafted,
        "escalated": escalated,
        "auto_handled_pct": round((replied + drafted) / total * 100, 1) if total else 0,
        "by_category": dict(category_counts),
        "by_sentiment": dict(sentiment_counts),
        "top_escalation_reasons": dict(escalation_reasons.most_common(5)),
    }
