"""Gmail OAuth connect/callback + manual poll endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse

from app.gmail import auth
from app.gmail.client import get_connected_email
from app.gmail.poller import poll_once

router = APIRouter(prefix="/api/gmail", tags=["gmail"])


@router.get("/status")
def status():
    connected = auth.is_connected()
    return {
        "connected": connected,
        "email": get_connected_email() if connected else None,
    }


@router.get("/connect")
def connect():
    """Redirect the user to Google's consent screen."""
    try:
        return RedirectResponse(auth.authorization_url())
    except FileNotFoundError as exc:
        raise HTTPException(400, str(exc))


@router.get("/oauth/callback", response_class=HTMLResponse)
def callback(code: str | None = None, error: str | None = None):
    if error:
        return HTMLResponse(f"<h3>Authorization failed: {error}</h3>", status_code=400)
    if not code:
        raise HTTPException(400, "Missing authorization code")
    auth.exchange_code(code)
    return HTMLResponse(
        "<h3>✅ Gmail connected. You can close this tab and return to the dashboard.</h3>"
    )


@router.post("/poll")
def poll(max_results: int = 20):
    if not auth.is_connected():
        raise HTTPException(400, "Gmail not connected")
    return poll_once(max_results=max_results)
