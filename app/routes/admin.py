"""Admin data editor API: CRUD over app.registry, audit history, reset-to-seed. STUB: Track D implements.

All routes depend on session.require_admin and use the session's center_slug only.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/admin")
