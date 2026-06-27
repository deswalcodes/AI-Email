"""One-off migration: copy all rows from the local SQLite DB into a target database
(e.g. a hosted Postgres) given by the TARGET_DATABASE_URL env var.

Usage:
    cd backend && source .venv/bin/activate
    TARGET_DATABASE_URL="postgresql://user:pass@host/db?sslmode=require" \
        python migrate_to_postgres.py

It reads from backend/data/app.db (the SQLite default) and writes into the target,
creating tables first. Safe to re-run with --fresh to wipe the target first.
"""
from __future__ import annotations

import os
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import BACKEND_DIR
from app.core.db import Base
from app.models import Email, Reply, Escalation, KBArticle  # noqa: F401

SQLITE_URL = f"sqlite:///{BACKEND_DIR / 'data' / 'app.db'}"
MODELS = [KBArticle, Email, Reply, Escalation]  # KB + Email before their dependents


def _columns(model):
    return [c.name for c in model.__table__.columns]


def main() -> None:
    target_url = os.environ.get("TARGET_DATABASE_URL")
    if not target_url:
        sys.exit("Set TARGET_DATABASE_URL to your Postgres connection string.")
    fresh = "--fresh" in sys.argv

    src_engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
    dst_engine = create_engine(target_url, pool_pre_ping=True)

    Base.metadata.create_all(bind=dst_engine)  # ensure tables exist in target

    Src = sessionmaker(bind=src_engine)()
    Dst = sessionmaker(bind=dst_engine)()

    try:
        if fresh:
            for model in reversed(MODELS):
                Dst.query(model).delete()
            Dst.commit()
            print("Target tables cleared (--fresh).")

        for model in MODELS:
            rows = Src.query(model).all()
            cols = _columns(model)
            copied = 0
            for row in rows:
                data = {c: getattr(row, c) for c in cols}
                Dst.merge(model(**data))  # merge keeps primary keys, allows re-runs
                copied += 1
            Dst.commit()
            print(f"  {model.__tablename__:14} -> {copied} rows")

        print("\n✅ Migration complete.")
    finally:
        Src.close()
        Dst.close()


if __name__ == "__main__":
    main()
