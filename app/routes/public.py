"""Public API: centers, mocked session, chat. Shapes are fixed in docs/CONTRACTS.md §3."""

import json
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app import chat, config, db, limits, session as sessions

router = APIRouter(prefix="/api")


def _center_public(row: dict) -> dict:
    return {
        "slug": row["slug"], "name": row["name"], "tagline": row["tagline"],
        "main_phone": row["main_phone"], "main_email": row["main_email"],
        "theme": json.loads(row["theme_json"] or "{}"),
    }


def _get_center(slug: str) -> dict | None:
    with db.connect() as conn:
        found = db.rows(conn, "SELECT * FROM centers WHERE slug = ?", (slug,))
    return _center_public(found[0]) if found else None


@router.get("/centers")
def list_centers():
    with db.connect() as conn:
        return [_center_public(r) for r in db.rows(conn, "SELECT * FROM centers ORDER BY name")]


class SessionIn(BaseModel):
    role: Literal["parent", "admin"]
    center_slug: str
    display_name: str | None = None


def _session_out(s: dict) -> dict:
    return {"role": s["role"], "display_name": s["display_name"], "center": _get_center(s["center_slug"])}


@router.post("/session")
def create_session(body: SessionIn, response: Response):
    if not _get_center(body.center_slug):
        raise HTTPException(400, "Unknown center.")
    name = (body.display_name or "").strip()[:60] or None
    if body.role == "admin" and not name:
        raise HTTPException(400, "Admins must enter a display name.")
    return _session_out(sessions.create_session(response, body.role, body.center_slug, name))


@router.get("/session")
def get_session(session: dict = Depends(sessions.require_session)):
    return _session_out(session)


@router.delete("/session")
def delete_session(request: Request, response: Response):
    sessions.clear_session(request, response)
    return {"ok": True}


class ChatIn(BaseModel):
    message: str
    conversation_id: str | None = None


def client_ip(request: Request) -> str:
    """Caddy sets X-Forwarded-For. Used only as an in-memory limiter key."""
    fwd = request.headers.get("x-forwarded-for")
    return fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "unknown")


@router.post("/chat")
def post_chat(body: ChatIn, request: Request, session: dict = Depends(sessions.require_session)):
    message = body.message.strip()
    if not message or len(message) > config.MAX_MESSAGE_CHARS:
        raise HTTPException(400, f"Message must be 1-{config.MAX_MESSAGE_CHARS} characters.")
    try:
        return chat.answer(session, message, body.conversation_id, client_ip(request))
    except limits.LimitExceeded as e:
        return JSONResponse({"detail": e.detail, "kind": e.kind}, status_code=429)
    except chat.UpstreamError:
        raise HTTPException(503, "The assistant is temporarily unavailable. Please try again shortly.")
