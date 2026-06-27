"""Pydantic response/request schemas for the API."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ReplyOut(BaseModel):
    id: int
    body: str
    tone: str | None = None
    confidence: float | None = None
    kb_sources: list = []
    is_ai: bool
    sent: bool
    sent_at: datetime | None = None
    approved_by: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class EscalationOut(BaseModel):
    id: int
    reasons: list = []
    resolved: bool
    created_at: datetime

    class Config:
        from_attributes = True


class EmailSummary(BaseModel):
    id: int
    sender: str
    sender_name: str | None = None
    subject: str | None = None
    category: str | None = None
    sentiment: str | None = None
    intent: list = []
    is_vip: bool = False
    status: str
    has_attachments: bool = False
    received_at: datetime | None = None

    class Config:
        from_attributes = True


class EmailDetail(EmailSummary):
    body: str
    thread_id: str | None = None
    attachment_names: list = []
    analysis: dict = {}
    replies: list[ReplyOut] = []
    escalation: EscalationOut | None = None


class SimulateEmailIn(BaseModel):
    sender: str
    sender_name: str | None = None
    subject: str
    body: str
    thread_id: str | None = None
    has_attachments: bool = False
    attachment_names: list[str] = []


class EditReplyIn(BaseModel):
    body: str


class KBArticleOut(BaseModel):
    id: int
    title: str
    category: str | None = None
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class KBArticleIn(BaseModel):
    title: str
    content: str
    category: str | None = None
