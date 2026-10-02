"""Admin Q/A log viewer API. STUB: Track E implements.

All routes depend on session.require_admin and return only the session's center's rows.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/admin/logs")
