"""Lightweight embedding-based vector store backed by SQLite (KBArticle rows).

Keeps dependencies minimal: embeddings are stored as JSON lists and similarity is
plain cosine via numpy. Good enough for a prototype KB of dozens–hundreds of chunks.
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
from sqlalchemy.orm import Session

from app.core.config import BACKEND_DIR
from app.models import KBArticle
from app.ai.client import embed

KB_FILE = BACKEND_DIR / "data" / "knowledge_base.md"


def _parse_markdown_kb(text: str) -> list[dict]:
    """Split the KB markdown into articles on each `## ` heading.

    A trailing `[Category]` in the heading is captured as the article category.
    """
    articles: list[dict] = []
    # Split keeping headings; skip the top-level `# ` title block.
    chunks = re.split(r"\n(?=## )", text)
    for chunk in chunks:
        if not chunk.strip().startswith("## "):
            continue
        first_nl = chunk.find("\n")
        heading = chunk[3:first_nl].strip() if first_nl != -1 else chunk[3:].strip()
        body = chunk[first_nl + 1:].strip() if first_nl != -1 else ""
        category = None
        m = re.search(r"\[([^\]]+)\]\s*$", heading)
        if m:
            category = m.group(1).strip()
            heading = heading[: m.start()].strip()
        if body:
            articles.append({"title": heading, "category": category, "content": body})
    return articles


def seed_kb_from_file(db: Session, *, force: bool = False) -> int:
    """Load the mock KB markdown into the DB and embed each article.

    Returns the number of articles ingested. No-op if already seeded unless `force`.
    """
    existing = db.query(KBArticle).count()
    if existing and not force:
        return 0
    if force:
        db.query(KBArticle).delete()
        db.commit()

    text = Path(KB_FILE).read_text(encoding="utf-8")
    articles = _parse_markdown_kb(text)
    for art in articles:
        row = KBArticle(
            title=art["title"],
            category=art["category"],
            content=art["content"],
            embedding=embed(f"{art['title']}\n{art['content']}"),
        )
        db.add(row)
    db.commit()
    return len(articles)


def add_article(db: Session, title: str, content: str, category: str | None = None) -> KBArticle:
    row = KBArticle(
        title=title, category=category, content=content,
        embedding=embed(f"{title}\n{content}"),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) or 1.0
    return float(np.dot(a, b) / denom)


def retrieve(db: Session, query: str, *, top_k: int = 3) -> list[dict]:
    """Return the top-k most relevant KB articles for the query."""
    rows = db.query(KBArticle).filter(KBArticle.embedding.isnot(None)).all()
    if not rows:
        return []
    qv = np.array(embed(query), dtype=float)
    scored = []
    for r in rows:
        try:
            score = _cosine(qv, np.array(r.embedding, dtype=float))
        except Exception:
            continue
        scored.append((score, r))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [
        {"id": r.id, "title": r.title, "category": r.category,
         "content": r.content, "score": round(score, 4)}
        for score, r in scored[:top_k]
    ]
