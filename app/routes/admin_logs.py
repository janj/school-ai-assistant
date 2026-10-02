"""Admin Q/A log viewer API (docs/CONTRACTS.md §3). Own center only, from the session."""

import json
from typing import Literal

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from app import db, placeholders, session as sess
from app.routes.admin import _audit

router = APIRouter(prefix="/api/admin/logs")


@router.get("")
def list_logs(
    found: Literal["all", "true", "false"] = "all",
    status: Literal["open"] | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: dict = Depends(sess.require_admin),
):
    sql = "SELECT * FROM qa_log WHERE center_slug = ?"
    params: list = [session["center_slug"]]
    if status == "open":  # unanswered and not yet turned into an FAQ
        sql += " AND found = 0 AND resolved_faq_id IS NULL"
    elif found != "all":
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
                   COALESCE(SUM(found = 0 AND resolved_faq_id IS NULL), 0) AS open_unanswered,
                   COALESCE(SUM(created_at >= datetime('now', '-7 days')), 0) AS last_7_days,
                   COALESCE(SUM(input_tokens), 0) AS i,
                   COALESCE(SUM(output_tokens), 0) AS o,
                   COALESCE(SUM(cache_read_tokens), 0) AS c
            FROM qa_log WHERE center_slug = ?""", (session["center_slug"],))[0]
    return {"total": r["total"], "unanswered": r["unanswered"],
            "open_unanswered": r["open_unanswered"], "last_7_days": r["last_7_days"],
            "tokens": {"input": r["i"], "output": r["o"], "cache_read": r["c"]}}


@router.post("/{log_id}/answer")
def answer(log_id: int, body: dict = Body(...), session: dict = Depends(sess.require_admin)):
    question = str(body.get("question") or "").strip()
    answer_text = str(body.get("answer") or "").strip()
    if not question or not answer_text:
        raise HTTPException(400, "Both a question and an answer are required.")
    center = session["center_slug"]
    with db.connect() as conn:
        log = db.rows(conn, "SELECT id, resolved_faq_id FROM qa_log WHERE id = ? AND center_slug = ?",
                      (log_id, center))
        if not log:
            raise HTTPException(404, "Log entry not found.")
        if log[0]["resolved_faq_id"] is not None:
            raise HTTPException(409, f"Already answered in FAQ #{log[0]['resolved_faq_id']}.")
        bad = placeholders.invalid(answer_text, placeholders.context(conn, center))
        if bad:
            raise HTTPException(400, f"Unknown placeholder(s): {', '.join(dict.fromkeys(bad))}. "
                                     "Check the key exists, or pick one from the placeholder list.")
        cur = conn.execute(
            "INSERT INTO faq (center_slug, question, answer, source_qa_id, created_by) VALUES (?, ?, ?, ?, ?)",
            (center, question, answer_text, log_id, session["display_name"] or "admin"))
        conn.execute("UPDATE qa_log SET resolved_faq_id = ? WHERE id = ?", (cur.lastrowid, log_id))
        row = db.rows(conn, "SELECT * FROM faq WHERE id = ?", (cur.lastrowid,))[0]
        _audit(conn, session, "faq", cur.lastrowid, "create", None, row)
    return row
