"""Mocked user session, and the center lock.

The cookie holds only a signed session id. Role and center live in the `sessions` row,
so a client can't switch centers by editing a request: every handler gets center_slug
from `require_session` / `require_admin`, never from the request body or query.
"""

import secrets

from fastapi import Depends, HTTPException, Request, Response
from itsdangerous import BadSignature, URLSafeSerializer

from app import config, db

_signer = URLSafeSerializer(config.SESSION_SECRET, salt="session")


def create_session(response: Response, role: str, center_slug: str, display_name: str | None) -> dict:
    sid = secrets.token_urlsafe(24)
    with db.connect() as conn:
        conn.execute(
            "INSERT INTO sessions (id, role, center_slug, display_name) VALUES (?, ?, ?, ?)",
            (sid, role, center_slug, display_name),
        )
    response.set_cookie(
        config.SESSION_COOKIE, _signer.dumps(sid),
        httponly=True, samesite="lax", secure=config.SESSION_SECRET != "dev-only-not-secret",
        max_age=60 * 60 * 24 * 30,
    )
    return get_session_by_id(sid)


def clear_session(request: Request, response: Response) -> None:
    session = current_session(request)
    if session:
        with db.connect() as conn:
            conn.execute("DELETE FROM sessions WHERE id = ?", (session["id"],))
    response.delete_cookie(config.SESSION_COOKIE)


def get_session_by_id(sid: str) -> dict | None:
    with db.connect() as conn:
        found = db.rows(conn, "SELECT id, role, center_slug, display_name FROM sessions WHERE id = ?", (sid,))
    return found[0] if found else None


def current_session(request: Request) -> dict | None:
    raw = request.cookies.get(config.SESSION_COOKIE)
    if not raw:
        return None
    try:
        sid = _signer.loads(raw)
    except BadSignature:
        return None
    return get_session_by_id(sid)


def require_session(request: Request) -> dict:
    """FastAPI dependency: {id, role, center_slug, display_name}, or 401."""
    session = current_session(request)
    if not session:
        raise HTTPException(401, "No session. Choose a role and center first.")
    return session


def require_admin(session: dict = Depends(require_session)) -> dict:
    """FastAPI dependency: an admin session, or 403."""
    if session["role"] != "admin":
        raise HTTPException(403, "Admin only.")
    return session
