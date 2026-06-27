"""Gmail API helpers: list/fetch messages, parse, send replies, apply labels."""
from __future__ import annotations

import base64
from email.mime.text import MIMEText
from typing import Any

from googleapiclient.discovery import build

from app.gmail.auth import load_credentials

PROCESSED_LABEL = "AI-Processed"


def _service():
    creds = load_credentials()
    if creds is None:
        raise RuntimeError("Gmail is not connected. Authorize via /api/gmail/connect first.")
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def list_unprocessed_message_ids(max_results: int = 20) -> list[str]:
    """Return IDs of inbox messages that have not yet been AI-processed."""
    svc = _service()
    label_id = _ensure_label(svc, PROCESSED_LABEL)
    query = f"in:inbox -label:{PROCESSED_LABEL}"
    resp = svc.users().messages().list(
        userId="me", q=query, maxResults=max_results
    ).execute()
    return [m["id"] for m in resp.get("messages", [])]


def fetch_message(message_id: str) -> dict[str, Any]:
    """Fetch and parse a single message into the shape used by our Email model."""
    svc = _service()
    msg = svc.users().messages().get(userId="me", id=message_id, format="full").execute()
    return _parse_message(msg)


def _header(headers: list[dict], name: str) -> str:
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def _parse_message(msg: dict) -> dict[str, Any]:
    payload = msg.get("payload", {})
    headers = payload.get("headers", [])
    from_raw = _header(headers, "From")
    sender_name, sender_email = _split_from(from_raw)

    body, attachments = _extract_body_and_attachments(payload)

    return {
        "gmail_id": msg["id"],
        "thread_id": msg.get("threadId"),
        "sender": sender_email,
        "sender_name": sender_name,
        "subject": _header(headers, "Subject"),
        "body": body.strip(),
        "has_attachments": bool(attachments),
        "attachment_names": attachments,
        "message_id_header": _header(headers, "Message-ID"),
    }


def _split_from(raw: str) -> tuple[str, str]:
    if "<" in raw and ">" in raw:
        name = raw.split("<")[0].strip().strip('"')
        email_addr = raw.split("<")[1].split(">")[0].strip()
        return name, email_addr
    return "", raw.strip()


def _extract_body_and_attachments(payload: dict) -> tuple[str, list[str]]:
    body_text = ""
    attachments: list[str] = []

    def walk(part: dict):
        nonlocal body_text
        mime = part.get("mimeType", "")
        filename = part.get("filename")
        data = part.get("body", {}).get("data")
        if filename:
            attachments.append(filename)
        elif mime == "text/plain" and data:
            body_text += _decode(data)
        elif mime == "text/html" and data and not body_text:
            body_text += _strip_html(_decode(data))
        for sub in part.get("parts", []) or []:
            walk(sub)

    walk(payload)
    if not body_text:
        data = payload.get("body", {}).get("data")
        if data:
            body_text = _decode(data)
    return body_text, attachments


def _decode(data: str) -> str:
    return base64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8", errors="replace")


def _strip_html(html: str) -> str:
    import re
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def send_reply(to: str, subject: str, body: str, thread_id: str | None = None,
               in_reply_to: str | None = None) -> dict:
    """Send a reply email, threaded if thread_id/in_reply_to are provided."""
    svc = _service()
    subj = subject if subject.lower().startswith("re:") else f"Re: {subject}"
    mime = MIMEText(body)
    mime["To"] = to
    mime["Subject"] = subj
    if in_reply_to:
        mime["In-Reply-To"] = in_reply_to
        mime["References"] = in_reply_to
    raw = base64.urlsafe_b64encode(mime.as_bytes()).decode("utf-8")
    payload = {"raw": raw}
    if thread_id:
        payload["threadId"] = thread_id
    return svc.users().messages().send(userId="me", body=payload).execute()


def mark_processed(message_id: str) -> None:
    svc = _service()
    label_id = _ensure_label(svc, PROCESSED_LABEL)
    svc.users().messages().modify(
        userId="me", id=message_id, body={"addLabelIds": [label_id]}
    ).execute()


def _ensure_label(svc, name: str) -> str:
    labels = svc.users().labels().list(userId="me").execute().get("labels", [])
    for lbl in labels:
        if lbl["name"] == name:
            return lbl["id"]
    created = svc.users().labels().create(
        userId="me",
        body={"name": name, "labelListVisibility": "labelShow",
              "messageListVisibility": "show"},
    ).execute()
    return created["id"]


def get_connected_email() -> str | None:
    try:
        svc = _service()
        profile = svc.users().getProfile(userId="me").execute()
        return profile.get("emailAddress")
    except Exception:
        return None
