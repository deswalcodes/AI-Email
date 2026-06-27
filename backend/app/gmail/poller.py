"""Poll Gmail for new messages, persist them, run the AI pipeline, auto-label."""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models import Email
from app.ai.pipeline import process_email
from app.gmail import client as gmail

logger = logging.getLogger("gmail.poller")


def poll_once(max_results: int = 20) -> dict:
    """Fetch unprocessed Gmail messages, ingest + process them. Returns a summary."""
    db: Session = SessionLocal()
    ingested, processed, errors = 0, 0, []
    try:
        message_ids = gmail.list_unprocessed_message_ids(max_results=max_results)
        for mid in message_ids:
            try:
                existing = db.query(Email).filter(Email.gmail_id == mid).first()
                if existing:
                    # Already ingested. If a prior run failed before processing it
                    # (e.g. hit a rate limit), retry the AI step now instead of
                    # silently labelling it as done.
                    if not existing.processed:
                        process_email(db, existing)
                        processed += 1
                    gmail.mark_processed(mid)
                    continue
                parsed = gmail.fetch_message(mid)
                email = Email(
                    gmail_id=parsed["gmail_id"],
                    thread_id=parsed["thread_id"],
                    sender=parsed["sender"],
                    sender_name=parsed["sender_name"],
                    subject=parsed["subject"],
                    body=parsed["body"] or "(no body)",
                    has_attachments=parsed["has_attachments"],
                    attachment_names=parsed["attachment_names"],
                    analysis={"message_id_header": parsed.get("message_id_header")},
                )
                db.add(email)
                db.commit()
                db.refresh(email)
                ingested += 1

                process_email(db, email)
                processed += 1

                # Auto-send happens here for real Gmail when in auto_send mode.
                _maybe_auto_send(db, email, parsed.get("message_id_header"))

                gmail.mark_processed(mid)
            except Exception as exc:  # one bad message shouldn't stop the batch
                logger.exception("Failed processing message %s", mid)
                errors.append({"message_id": mid, "error": str(exc)})
                db.rollback()
        return {"ingested": ingested, "processed": processed, "errors": errors}
    finally:
        db.close()


def _maybe_auto_send(db: Session, email: Email, in_reply_to: str | None) -> None:
    """If a reply was auto-marked sent (auto_send mode), actually deliver it via Gmail."""
    if email.status != "replied":
        return
    reply = email.replies[-1] if email.replies else None
    if not reply or not reply.sent:
        return
    try:
        gmail.send_reply(
            to=email.sender,
            subject=email.subject or "",
            body=reply.body,
            thread_id=email.thread_id,
            in_reply_to=in_reply_to,
        )
    except Exception:
        logger.exception("Auto-send failed for email %s", email.id)
