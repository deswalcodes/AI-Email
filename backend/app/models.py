"""Database models for emails, AI replies, escalations, and KB articles."""
from datetime import datetime, timezone

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey, JSON,
)
from sqlalchemy.orm import relationship

from app.core.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---- Category / status enums kept as plain strings for prototype simplicity ----
CATEGORIES = [
    "Legal", "Product Issue", "Delivery Issue", "Return / Refund",
    "Billing", "General Enquiry", "Feedback / Praise", "Spam / Irrelevant",
]
SENTIMENTS = ["Angry", "Frustrated", "Sad / Distressed", "Neutral", "Happy / Positive"]
STATUSES = ["open", "drafted", "replied", "escalated"]


class Email(Base):
    __tablename__ = "emails"

    id = Column(Integer, primary_key=True)
    gmail_id = Column(String, unique=True, index=True, nullable=True)  # null for seeded/mock
    thread_id = Column(String, index=True, nullable=True)

    sender = Column(String, nullable=False)
    sender_name = Column(String, nullable=True)
    subject = Column(String, nullable=True)
    body = Column(Text, nullable=False)
    has_attachments = Column(Boolean, default=False)
    attachment_names = Column(JSON, default=list)
    received_at = Column(DateTime, default=utcnow)

    # AI analysis
    category = Column(String, nullable=True)
    sentiment = Column(String, nullable=True)
    intent = Column(JSON, default=list)         # list of intent tags
    is_vip = Column(Boolean, default=False)
    analysis = Column(JSON, default=dict)       # raw structured analysis + reasoning

    # Workflow
    status = Column(String, default="open", index=True)
    processed = Column(Boolean, default=False)

    created_at = Column(DateTime, default=utcnow)

    replies = relationship("Reply", back_populates="email", cascade="all, delete-orphan")
    escalation = relationship(
        "Escalation", back_populates="email", uselist=False, cascade="all, delete-orphan"
    )


class Reply(Base):
    __tablename__ = "replies"

    id = Column(Integer, primary_key=True)
    email_id = Column(Integer, ForeignKey("emails.id"), nullable=False)

    body = Column(Text, nullable=False)
    tone = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    kb_sources = Column(JSON, default=list)     # KB article titles/ids used in RAG
    is_ai = Column(Boolean, default=True)

    sent = Column(Boolean, default=False)
    sent_at = Column(DateTime, nullable=True)
    approved_by = Column(String, nullable=True)

    created_at = Column(DateTime, default=utcnow)

    email = relationship("Email", back_populates="replies")


class Escalation(Base):
    __tablename__ = "escalations"

    id = Column(Integer, primary_key=True)
    email_id = Column(Integer, ForeignKey("emails.id"), nullable=False)

    reasons = Column(JSON, default=list)        # list of human-readable reasons
    resolved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow)

    email = relationship("Email", back_populates="escalation")


class AppSetting(Base):
    """Generic key/value store for app state that must persist (e.g. Gmail OAuth token).

    Kept in the DB rather than a local file so it survives on ephemeral hosts (Render
    free tier) and is shared across environments pointing at the same database.
    """
    __tablename__ = "app_settings"

    key = Column(String, primary_key=True)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class KBArticle(Base):
    __tablename__ = "kb_articles"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    category = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    embedding = Column(JSON, nullable=True)     # list[float]; null until embedded
    created_at = Column(DateTime, default=utcnow)
