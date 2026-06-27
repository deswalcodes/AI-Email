"""Gmail OAuth 2.0 — authorization URL, callback exchange, and credential loading.

Tokens are persisted to backend/token.json. Uses the web-app flow so the callback can
be handled by a FastAPI route. For a single-inbox prototype this is sufficient.
"""
from __future__ import annotations

import json
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from app.core.config import settings
from app.core.db import SessionLocal
from app.models import AppSetting

TOKEN_KEY = "gmail_token"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",  # for applying labels
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
]


def _flow() -> Flow:
    if not settings.client_secrets_path.exists():
        raise FileNotFoundError(
            f"Gmail client secrets not found at {settings.client_secrets_path}. "
            "Download an OAuth client from Google Cloud Console and place it there."
        )
    return Flow.from_client_secrets_file(
        str(settings.client_secrets_path),
        scopes=SCOPES,
        redirect_uri=settings.google_oauth_redirect_uri,
    )


def authorization_url() -> str:
    flow = _flow()
    url, _state = flow.authorization_url(
        access_type="offline", include_granted_scopes="true", prompt="consent"
    )
    return url


def exchange_code(code: str) -> Credentials:
    flow = _flow()
    flow.fetch_token(code=code)
    creds = flow.credentials
    _save_credentials(creds)
    return creds


def _save_credentials(creds: Credentials) -> None:
    """Persist the OAuth token in the DB (survives ephemeral hosts & restarts)."""
    db = SessionLocal()
    try:
        row = db.get(AppSetting, TOKEN_KEY)
        if row:
            row.value = creds.to_json()
        else:
            db.add(AppSetting(key=TOKEN_KEY, value=creds.to_json()))
        db.commit()
    finally:
        db.close()


def _load_token_data() -> dict | None:
    """Read token JSON from the DB, falling back to a legacy token.json file."""
    db = SessionLocal()
    try:
        row = db.get(AppSetting, TOKEN_KEY)
        if row and row.value:
            return json.loads(row.value)
    finally:
        db.close()
    # Legacy/local fallback: migrate an existing token.json into the DB on first read.
    if Path(settings.token_path).exists():
        data = json.loads(Path(settings.token_path).read_text(encoding="utf-8"))
        db = SessionLocal()
        try:
            if not db.get(AppSetting, TOKEN_KEY):
                db.add(AppSetting(key=TOKEN_KEY, value=json.dumps(data)))
                db.commit()
        finally:
            db.close()
        return data
    return None


def load_credentials() -> Credentials | None:
    """Load saved credentials, refreshing if expired. Returns None if not connected."""
    data = _load_token_data()
    if not data:
        return None
    creds = Credentials.from_authorized_user_info(data, SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _save_credentials(creds)
    return creds


def is_connected() -> bool:
    try:
        return load_credentials() is not None
    except Exception:
        return False
