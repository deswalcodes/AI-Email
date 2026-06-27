"""Escalation queue endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import Email, Escalation
from app.schemas import EmailSummary

router = APIRouter(prefix="/api/escalations", tags=["escalations"])


@router.get("", response_model=list[EmailSummary])
def list_escalations(db: Session = Depends(get_db), resolved: bool = False):
    q = (
        db.query(Email)
        .join(Escalation, Escalation.email_id == Email.id)
        .filter(Escalation.resolved == resolved)
        .order_by(Email.received_at.desc())
    )
    return q.all()


@router.post("/{email_id}/resolve")
def resolve(email_id: int, db: Session = Depends(get_db)):
    esc = db.query(Escalation).filter(Escalation.email_id == email_id).first()
    if not esc:
        raise HTTPException(404, "No escalation for this email")
    esc.resolved = True
    db.commit()
    return {"ok": True, "email_id": email_id}
