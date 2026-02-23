"""Lightweight JSON API: timer/keepalive endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.models import Session
from app.game import get_remaining_seconds, _check_time_expired

router = APIRouter(prefix="/api")


@router.get("/session/{session_id}/timer")
def session_timer(session_id: str, db: DBSession = Depends(get_db)):
    """Return remaining seconds + status. Also serves as keepalive for Cloud Run."""
    session = db.query(Session).filter_by(id=session_id).first()
    if not session:
        return {"error": "not_found"}

    # Auto-end if time expired
    if session.status == "active":
        try:
            _check_time_expired(db, session)
        except Exception:
            pass  # status already changed to ended

    remaining = get_remaining_seconds(session)
    return {
        "status": session.status,
        "remaining_seconds": remaining,
        "time_limit_minutes": session.time_limit_minutes,
    }
