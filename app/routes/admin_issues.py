"""Data issues queue API (Track K). Admin only; the center always comes from the session."""

import threading
import time
from typing import Literal

from fastapi import APIRouter, Body, Depends, HTTPException

from app import db, maintenance, session as sess

router = APIRouter(prefix="/api/admin/issues")

AI_COOLDOWN_S = 600
_last_ai: dict[str, float] = {}  # center -> monotonic time of its last AI run (in memory: POC, one process)
_lock = threading.Lock()

_ORDER = "CASE severity WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END, id"


@router.get("")
def list_issues(status: Literal["open", "resolved", "dismissed", "all"] = "open",
                s: dict = Depends(sess.require_admin)):
    sql, params = "SELECT * FROM kb_issues WHERE center_slug = ?", [s["center_slug"]]
    if status != "all":
        sql += " AND status = ?"
        params.append(status)
    with db.connect() as conn:
        return db.rows(conn, f"{sql} ORDER BY {_ORDER}", params)


@router.get("/auto-fixes")
def auto_fixes(s: dict = Depends(sess.require_admin)):
    """Recent edits made by the agent itself (same rows as History, filtered)."""
    with db.connect() as conn:
        return db.rows(conn, "SELECT id, table_name, row_id, action, before_json, after_json, created_at"
                       " FROM audit_log WHERE center_slug = ? AND admin_name = ? ORDER BY id DESC LIMIT 20",
                       (s["center_slug"], maintenance.AGENT))


@router.post("/run")
def run_check(body: dict = Body(default={}), s: dict = Depends(sess.require_admin)):
    ai = bool(body.get("ai"))
    slug = s["center_slug"]
    if ai:
        with _lock:
            wait = AI_COOLDOWN_S - (time.monotonic() - _last_ai.get(slug, -AI_COOLDOWN_S))
            if wait > 0:
                raise HTTPException(429, f"The AI review was just run. Please try again in {int(wait // 60) + 1} "
                                         "minute(s); the quick checks can run any time.")
            _last_ai[slug] = time.monotonic()
    summary = maintenance.run(slug, rules=True, ai=ai)
    if ai and summary["ai_error"]:
        _last_ai.pop(slug, None)  # a failed call doesn't use up the allowance
    return summary


@router.post("/{issue_id}/status")
def set_status(issue_id: int, body: dict = Body(...), s: dict = Depends(sess.require_admin)):
    status = body.get("status")
    if status not in ("resolved", "dismissed"):
        raise HTTPException(400, 'status must be "resolved" or "dismissed".')
    with db.connect() as conn:
        cur = conn.execute("UPDATE kb_issues SET status = ?, resolved_by = ?, updated_at = datetime('now')"
                           " WHERE id = ? AND center_slug = ?",
                           (status, s["display_name"] or "admin", issue_id, s["center_slug"]))
        if cur.rowcount != 1:
            raise HTTPException(404, "Issue not found.")
        return db.rows(conn, "SELECT * FROM kb_issues WHERE id = ?", (issue_id,))[0]
