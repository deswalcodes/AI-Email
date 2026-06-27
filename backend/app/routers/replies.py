"""Reply approval / editing / sending endpoints."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import Email, Reply
from app.schemas import ReplyOut, EditReplyIn
from app.gmail import client as gmail
from app.gmail.auth import is_connected

router = APIRouter(prefix="/api/replies", tags=["replies"])


@router.patch("/{reply_id}", response_model=ReplyOut)
def edit_reply(reply_id: int, payload: EditReplyIn, db: Session = Depends(get_db)):
    reply = db.query(Reply).filter(Reply.id == reply_id).first()
    if not reply:
        raise HTTPException(404, "Reply not found")
    if reply.sent:
        raise HTTPException(400, "Reply already sent")
    reply.body = payload.body
    reply.is_ai = False  # human-edited
    db.commit()
    db.refresh(reply)
    return reply


@router.post("/{reply_id}/approve", response_model=ReplyOut)
def approve_and_send(reply_id: int, db: Session = Depends(get_db)):
    """Approve an AI draft and send it via Gmail (if connected) or mark sent (demo)."""
    reply = db.query(Reply).filter(Reply.id == reply_id).first()
    if not reply:
        raise HTTPException(404, "Reply not found")
    if reply.sent:
        raise HTTPException(400, "Reply already sent")

    email = db.query(Email).filter(Email.id == reply.email_id).first()

    # Send through Gmail only for real (gmail_id present) emails when connected.
    if email and email.gmail_id and is_connected():
        in_reply_to = (email.analysis or {}).get("message_id_header")
        gmail.send_reply(
            to=email.sender,
            subject=email.subject or "",
            body=reply.body,
            thread_id=email.thread_id,
            in_reply_to=in_reply_to,
        )

    reply.sent = True
    reply.sent_at = datetime.now(timezone.utc)
    reply.approved_by = "agent"
    if email:
        email.status = "replied"
    db.commit()
    db.refresh(reply)
    return reply
