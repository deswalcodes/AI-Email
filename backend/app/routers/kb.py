"""Knowledge Base management + RAG retrieval preview endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import KBArticle
from app.schemas import KBArticleOut, KBArticleIn
from app.rag.store import add_article, retrieve, seed_kb_from_file

router = APIRouter(prefix="/api/kb", tags=["knowledge-base"])


@router.get("", response_model=list[KBArticleOut])
def list_articles(db: Session = Depends(get_db)):
    return db.query(KBArticle).order_by(KBArticle.id.asc()).all()


@router.post("", response_model=KBArticleOut)
def create_article(payload: KBArticleIn, db: Session = Depends(get_db)):
    return add_article(db, payload.title, payload.content, payload.category)


@router.delete("/{article_id}")
def delete_article(article_id: int, db: Session = Depends(get_db)):
    art = db.query(KBArticle).filter(KBArticle.id == article_id).first()
    if not art:
        raise HTTPException(404, "Article not found")
    db.delete(art)
    db.commit()
    return {"ok": True}


@router.post("/seed")
def reseed(db: Session = Depends(get_db)):
    count = seed_kb_from_file(db, force=True)
    return {"seeded": count}


@router.get("/preview")
def preview_retrieval(q: str = Query(..., min_length=2), top_k: int = 3,
                      db: Session = Depends(get_db)):
    """Show which KB chunks would be retrieved for a query (brief 4: KB Manager)."""
    return {"query": q, "results": retrieve(db, q, top_k=top_k)}
