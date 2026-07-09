"""Placeholder sign-in for tier testing (design doc §4.1 staged rollout).

This is deliberately NOT security. It exists so the anonymous-vs-signed-in
upload tiers have real UX and enforcement before the managed auth provider
(Supabase: Google first, then email/password) lands in Phase 2. The swap
plan: get_current_user() is the only integration point - Phase 2 replaces
its body with provider JWT verification and nothing else changes.

Session: HMAC-signed cookie. Secret comes from CCR_SESSION_SECRET or is
random per process (restart signs everyone out - acceptable for a demo).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets

from fastapi import Request

COOKIE_NAME = "ccr_demo_session"
_SECRET = (os.environ.get("CCR_SESSION_SECRET") or secrets.token_hex(32)).encode()

# Tier limits; env-overridable so tests and the hosted demo can tune them.
ANON_MAX_BYTES_DEFAULT = 2 * 1024 * 1024
ANON_MAX_ROWS_DEFAULT = 500


def anon_max_bytes() -> int:
    return int(os.environ.get("CCR_ANON_MAX_BYTES", ANON_MAX_BYTES_DEFAULT))


def anon_max_rows() -> int:
    return int(os.environ.get("CCR_ANON_MAX_ROWS", ANON_MAX_ROWS_DEFAULT))


def _sign(payload: bytes) -> str:
    return hmac.new(_SECRET, payload, hashlib.sha256).hexdigest()


def create_token(name: str) -> str:
    payload = base64.urlsafe_b64encode(name.encode()).decode()
    return f"{payload}.{_sign(payload.encode())}"


def verify_token(token: str | None) -> str | None:
    """Return the signed-in name, or None for anonymous/invalid tokens."""
    if not token or "." not in token:
        return None
    payload, signature = token.rsplit(".", 1)
    if not hmac.compare_digest(signature, _sign(payload.encode())):
        return None
    try:
        return base64.urlsafe_b64decode(payload.encode()).decode()
    except Exception:
        return None


def get_current_user(request: Request) -> dict | None:
    """Phase 2 integration point: replace body with provider JWT verification."""
    name = verify_token(request.cookies.get(COOKIE_NAME))
    return {"name": name, "tier": "member"} if name else None
