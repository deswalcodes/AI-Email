"""Rule engine deciding whether an email needs a human, per the brief's section 3.5."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Email


def evaluate_escalation(
    db: Session,
    email: Email,
    *,
    analysis: dict,
    confidence: float | None,
) -> list[str]:
    """Return a list of human-readable escalation reasons (empty == no escalation)."""
    reasons: list[str] = []

    category = analysis.get("category")
    sentiment = analysis.get("sentiment")
    intent = analysis.get("intent", [])
    is_vip = analysis.get("is_vip", False)

    # 1. Legal category — any legal/regulatory mention.
    if category == "Legal":
        reasons.append("Legal category — routed to the legal team")

    # 2. Angry AND third contact or more in the same thread.
    if sentiment == "Angry":
        contact_count = _thread_contact_count(db, email)
        if contact_count >= settings.angry_contact_threshold:
            reasons.append(
                f"Angry customer on contact #{contact_count} in this thread"
            )

    # 3. VIP / high-value customer.
    if is_vip or "high_value_customer" in intent:
        reasons.append("VIP / high-value customer")

    # 4. AI confidence below threshold.
    if confidence is not None and confidence < settings.confidence_threshold:
        reasons.append(
            f"AI confidence {confidence:.2f} below threshold {settings.confidence_threshold:.2f}"
        )

    # 5. Attachments needing human review.
    if email.has_attachments:
        reasons.append("Email contains attachments needing human review")

    # Bonus: explicit threat of escalation (legal / social media).
    if "threatening_escalation" in intent and category != "Legal":
        reasons.append("Customer threatening escalation (legal / social media)")

    return reasons


def _thread_contact_count(db: Session, email: Email) -> int:
    """Number of inbound emails from this sender in the same thread (incl. this one)."""
    if email.thread_id:
        return (
            db.query(Email)
            .filter(Email.thread_id == email.thread_id, Email.sender == email.sender)
            .count()
        )
    return (
        db.query(Email)
        .filter(Email.sender == email.sender)
        .count()
    )
