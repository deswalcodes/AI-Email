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
    Path(settings.token_path).write_text(creds.to_json(), encoding="utf-8")


def load_credentials() -> Credentials | None:
    """Load saved credentials, refreshing if expired. Returns None if not connected."""
    if not Path(settings.token_path).exists():
        return None
    data = json.loads(Path(settings.token_path).read_text(encoding="utf-8"))
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
