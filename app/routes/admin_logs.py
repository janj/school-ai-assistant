"""Admin Q/A log viewer API (docs/CONTRACTS.md §3). Own center only, from the session."""

import json
from typing import Literal

from fastapi import APIRouter, Depends, Query

from app import db, session as sess

router = APIRouter(prefix="/api/admin/logs")


@router.get("")
def list_logs(
    found: Literal["all", "true", "false"] = "all",
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: dict = Depends(sess.require_admin),
):
    sql = "SELECT * FROM qa_log WHERE center_slug = ?"
    params: list = [session["center_slug"]]
    if found != "all":
        sql += " AND found = ?"
        params.append(1 if found == "true" else 0)
    sql += " ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?"
    params += [limit, offset]
    with db.connect() as conn:
        out = db.rows(conn, sql, params)
    for r in out:
        r["sources"] = json.loads(r.pop("sources_json") or "[]")
        r["found"] = bool(r["found"])
    return out


@router.get("/stats")
def stats(session: dict = Depends(sess.require_admin)):
    with db.connect() as conn:
        r = db.rows(conn, """
            SELECT COUNT(*) AS total,
                   COALESCE(SUM(found = 0), 0) AS unanswered,
                   COALESCE(SUM(created_at >= datetime('now', '-7 days')), 0) AS last_7_days,
                   COALESCE(SUM(input_tokens), 0) AS i,
                   COALESCE(SUM(output_tokens), 0) AS o,
                   COALESCE(SUM(cache_read_tokens), 0) AS c
            FROM qa_log WHERE center_slug = ?""", (session["center_slug"],))[0]
    return {"total": r["total"], "unanswered": r["unanswered"], "last_7_days": r["last_7_days"],
            "tokens": {"input": r["i"], "output": r["o"], "cache_read": r["c"]}}
