"""Supabase authentication: persisted session, refresh and password login."""
import base64
import json
import os
import sys
import time
from pathlib import Path

import requests

SUPABASE_URL = "https://cyrxjeppjqsxxjayfrur.supabase.co"
PROJECT_REF = "cyrxjeppjqsxxjayfrur"
COOKIE_NAME = f"sb-{PROJECT_REF}-auth-token"
COOKIE_CHUNK_SIZE = 3180  # same chunking as @supabase/ssr
DEFAULT_ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN5cnhqZXBwanFzeHhqYXlmcnVyIiwi"
    "cm9sZSI6ImFub24iLCJpYXQiOjE3NzM4ODAzMzksImV4cCI6MjA4OTQ1NjMzOX0.BZluyXygNxuQGDPxFX1zG5i-cqp10CVK-8GGtuak4Rg"
)
EXPIRY_MARGIN = 60  # seconds: renew slightly before the real expiry

ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", DEFAULT_ANON_KEY)
STATE_FILE = Path(os.environ.get("WIKIMASTERS_STATE_FILE", "session.json"))


def _auth_request(grant_type: str, payload: dict) -> dict:
    resp = requests.post(
        f"{SUPABASE_URL}/auth/v1/token",
        params={"grant_type": grant_type},
        headers={"apikey": ANON_KEY, "Content-Type": "application/json"},
        json=payload,
        timeout=30,
    )
    if not resp.ok:
        raise RuntimeError(f"auth {grant_type}: HTTP {resp.status_code} {resp.text[:200]}")
    return resp.json()


def _load_session() -> dict | None:
    try:
        return json.loads(STATE_FILE.read_text())
    except (OSError, ValueError):
        return None


def _save_session(session: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(session))
    tmp.chmod(0o600)
    tmp.replace(STATE_FILE)  # atomic: the refresh token rotates, we must never lose it


def parse_cookie(cookie: str) -> dict:
    """Extract the session from a Cookie header copied from the browser (chunks .0, .1, ...)."""
    chunks = {}
    for part in cookie.split(";"):
        name, _, value = part.strip().partition("=")
        if name == COOKIE_NAME:
            chunks[0] = value
        elif name.startswith(COOKIE_NAME + "."):
            chunks[int(name.rsplit(".", 1)[1])] = value
    if not chunks:
        raise ValueError(f"cookie {COOKIE_NAME} not found")
    raw = "".join(chunks[i] for i in sorted(chunks)).removeprefix("base64-")
    raw += "=" * (-len(raw) % 4)
    session = json.loads(base64.urlsafe_b64decode(raw))
    if not session.get("refresh_token"):
        raise ValueError("no refresh_token in the cookie")
    return session


def get_session() -> dict:
    """Return a valid session, making as few auth calls as possible."""
    session = _load_session()

    # Seeding: no saved session but a browser cookie was provided.
    seed = os.environ.get("WIKIMASTERS_COOKIE")
    if not session and seed:
        try:
            session = parse_cookie(seed)
        except ValueError as exc:
            sys.exit(f"Invalid WIKIMASTERS_COOKIE: {exc}")
        _save_session(session)
        print("Session imported from WIKIMASTERS_COOKIE.")

    if session and session.get("expires_at", 0) - time.time() > EXPIRY_MARGIN:
        return session

    if session and session.get("refresh_token"):
        try:
            session = _auth_request("refresh_token", {"refresh_token": session["refresh_token"]})
            _save_session(session)
            print("Session renewed (refresh token).")
            return session
        except RuntimeError as exc:
            print(f"Refresh failed ({exc}), falling back to password login.")

    email = os.environ.get("WIKIMASTERS_EMAIL")
    password = os.environ.get("WIKIMASTERS_PASSWORD")
    if not email or not password:
        sys.exit("Login required: set WIKIMASTERS_COOKIE (recommended) or WIKIMASTERS_EMAIL and WIKIMASTERS_PASSWORD")
    try:
        session = _auth_request("password", {"email": email, "password": password})
    except RuntimeError as exc:
        if "captcha" in str(exc):
            sys.exit(
                "Password login is protected by a captcha. Log in from your browser, "
                "copy the cookie and provide it through WIKIMASTERS_COOKIE (see README)."
            )
        raise
    _save_session(session)
    print("Logged in (email + password).")
    return session


def build_cookie(session: dict) -> str:
    """Rebuild the cookie set by @supabase/ssr: 'base64-' + JSON, split into chunks."""
    encoded = "base64-" + base64.urlsafe_b64encode(json.dumps(session).encode()).decode().rstrip("=")
    if len(encoded) <= COOKIE_CHUNK_SIZE:
        return f"{COOKIE_NAME}={encoded}"
    chunks = [encoded[i:i + COOKIE_CHUNK_SIZE] for i in range(0, len(encoded), COOKIE_CHUNK_SIZE)]
    return "; ".join(f"{COOKIE_NAME}.{i}={chunk}" for i, chunk in enumerate(chunks))
