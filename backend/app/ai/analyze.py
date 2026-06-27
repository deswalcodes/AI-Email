"""Email analysis: categorization + sentiment + intent in a single LLM pass."""
from __future__ import annotations

from typing import Any

from app.ai.client import chat_json
from app.models import CATEGORIES, SENTIMENTS

INTENT_TAGS = [
    "wants_immediate_resolution",
    "seeking_information",
    "threatening_escalation",
    "repeat_contact",
    "high_value_customer",
]

_SYSTEM = f"""You are an email triage engine for a customer support team at an
e-commerce company. Analyze the customer's email and return STRICT JSON.

Classify into exactly one primary category from:
{CATEGORIES}

Detect the dominant sentiment, exactly one of:
{SENTIMENTS}

Detect any applicable intent tags (zero or more) from:
{INTENT_TAGS}

Also decide if the sender appears to be a VIP / high-value customer (explicit mentions
of being a long-time/enterprise/premium customer, large orders, or VIP language).

Return JSON with this exact shape:
{{
  "category": "<one category>",
  "sentiment": "<one sentiment>",
  "intent": ["<intent tags>"],
  "is_vip": true|false,
  "summary": "<one-sentence summary of what the customer wants>",
  "reasoning": "<one short sentence on why this category/sentiment>"
}}"""


def analyze_email(subject: str, body: str, sender: str) -> dict[str, Any]:
    user = f"From: {sender}\nSubject: {subject}\n\n{body}"
    result = chat_json(_SYSTEM, user, temperature=0.0)

    # Defensive normalisation so downstream code can trust the shape.
    category = result.get("category")
    if category not in CATEGORIES:
        category = "General Enquiry"
    sentiment = result.get("sentiment")
    if sentiment not in SENTIMENTS:
        sentiment = "Neutral"
    intent = [t for t in result.get("intent", []) if t in INTENT_TAGS]

    return {
        "category": category,
        "sentiment": sentiment,
        "intent": intent,
        "is_vip": bool(result.get("is_vip", False)),
        "summary": result.get("summary", ""),
        "reasoning": result.get("reasoning", ""),
    }
