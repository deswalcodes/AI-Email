"""Email inbox + thread endpoints, including 'simulate incoming email' for testing."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import Email
from app.schemas import EmailSummary, EmailDetail, SimulateEmailIn
from app.ai.pipeline import process_email

router = APIRouter(prefix="/api/emails", tags=["emails"])


@router.get("", response_model=list[EmailSummary])
def list_emails(
    db: Session = Depends(get_db),
    category: str | None = Query(None),
    sentiment: str | None = Query(None),
    status: str | None = Query(None),
):
    q = db.query(Email).order_by(Email.received_at.desc())
    if category:
        q = q.filter(Email.category == category)
    if sentiment:
        q = q.filter(Email.sentiment == sentiment)
    if status:
        q = q.filter(Email.status == status)
    return q.all()


@router.get("/{email_id}", response_model=EmailDetail)
def get_email(email_id: int, db: Session = Depends(get_db)):
    email = db.query(Email).filter(Email.id == email_id).first()
    if not email:
        raise HTTPException(404, "Email not found")
    return email


@router.get("/{email_id}/thread", response_model=list[EmailDetail])
def get_thread(email_id: int, db: Session = Depends(get_db)):
    email = db.query(Email).filter(Email.id == email_id).first()
    if not email:
        raise HTTPException(404, "Email not found")
    if not email.thread_id:
        return [email]
    return (
        db.query(Email)
        .filter(Email.thread_id == email.thread_id)
        .order_by(Email.received_at.asc())
        .all()
    )


@router.post("/simulate", response_model=EmailDetail)
def simulate_email(payload: SimulateEmailIn, db: Session = Depends(get_db)):
    """Inject a fake inbound email and run it through the full AI pipeline.

    Lets the prototype be demoed end-to-end without waiting for real Gmail traffic.
    """
    email = Email(
        sender=payload.sender,
        sender_name=payload.sender_name,
        subject=payload.subject,
        body=payload.body,
        thread_id=payload.thread_id,
        has_attachments=payload.has_attachments,
        attachment_names=payload.attachment_names,
        received_at=datetime.now(timezone.utc),
    )
    db.add(email)
    db.commit()
    db.refresh(email)
    process_email(db, email)
    return email


@router.post("/{email_id}/reprocess", response_model=EmailDetail)
def reprocess(email_id: int, db: Session = Depends(get_db)):
    email = db.query(Email).filter(Email.id == email_id).first()
    if not email:
        raise HTTPException(404, "Email not found")
    # Clear prior AI output so the pipeline starts fresh.
    for r in list(email.replies):
        db.delete(r)
    if email.escalation:
        db.delete(email.escalation)
    db.commit()
    process_email(db, email)
    db.refresh(email)
    return email
