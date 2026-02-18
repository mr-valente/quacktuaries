"""Admin / Teacher routes: login, session management, dashboard."""

import csv
import io
import json
import secrets

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session as DBSession

from app.config import (
    ADMIN_PASSWORD,
    DEFAULT_DEVICE_COUNT,
    DEFAULT_MAX_TURNS,
    DEFAULT_TEST_BUDGET,
    DEFAULT_MIN_N,
    DEFAULT_MAX_N,
    DEFAULT_PREMIUM_SCALE,
    DEFAULT_CONFIDENCE_FEE,
    DEFAULT_MISS_PENALTY,
    DEFAULT_REQUIRE_PRIOR_TEST,
)
from app.database import get_db
from app.models import Session, Player, Event
from app.game import (
    generate_device_ps,
    generate_join_code,
    get_leaderboard,
    DIFFICULTY_PRESETS,
)
from app.templating import templates

router = APIRouter(prefix="/admin")


def _require_admin(request: Request):
    """Check admin session; redirect to login if missing."""
    if not request.session.get("is_admin"):
        return False
    return True


# ── Login ──────────────────────────────────────────────────────────────────────

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def admin_login_page(request: Request):
    if _require_admin(request):
        return RedirectResponse(url="/admin/dashboard", status_code=303)
    return templates.TemplateResponse("admin_login.html", {"request": request, "error": None})


@router.post("/login")
def admin_login(request: Request, password: str = Form(...)):
    if password == ADMIN_PASSWORD:
        request.session["is_admin"] = True
        return RedirectResponse(url="/admin/dashboard", status_code=303)
    return templates.TemplateResponse(
        "admin_login.html",
        {"request": request, "error": "Incorrect password."},
        status_code=401,
    )


@router.get("/logout")
def admin_logout(request: Request):
    request.session.pop("is_admin", None)
    return RedirectResponse(url="/", status_code=303)


# ── Dashboard ──────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_class=HTMLResponse)
def admin_dashboard(request: Request, db: DBSession = Depends(get_db)):
    if not _require_admin(request):
        return RedirectResponse(url="/admin", status_code=303)
    sessions = db.query(Session).order_by(Session.created_at.desc()).all()
    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request,
        "sessions": sessions,
    })


# ── Create session ─────────────────────────────────────────────────────────────

@router.get("/sessions/new", response_class=HTMLResponse)
def new_session_form(request: Request):
    if not _require_admin(request):
        return RedirectResponse(url="/admin", status_code=303)
    return templates.TemplateResponse("admin_new_session.html", {
        "request": request,
        "presets": DIFFICULTY_PRESETS,
        "defaults": {
            "device_count": DEFAULT_DEVICE_COUNT,
            "max_turns": DEFAULT_MAX_TURNS,
            "test_budget": DEFAULT_TEST_BUDGET,
            "min_n": DEFAULT_MIN_N,
            "max_n": DEFAULT_MAX_N,
            "premium_scale": DEFAULT_PREMIUM_SCALE,
        },
    })


@router.post("/session/create")
def create_session(
    request: Request,
    difficulty: str = Form("medium"),
    device_count: int = Form(DEFAULT_DEVICE_COUNT),
    max_turns: int = Form(DEFAULT_MAX_TURNS),
    test_budget: int = Form(DEFAULT_TEST_BUDGET),
    min_n: int = Form(DEFAULT_MIN_N),
    max_n: int = Form(DEFAULT_MAX_N),
    premium_scale: int = Form(DEFAULT_PREMIUM_SCALE),
    db: DBSession = Depends(get_db),
):
    if not _require_admin(request):
        return RedirectResponse(url="/admin", status_code=303)

    seed = secrets.randbelow(2**31)
    join_code = generate_join_code()

    # Ensure unique join code
    while db.query(Session).filter_by(join_code=join_code).first():
        join_code = generate_join_code()

    ps = generate_device_ps(device_count, seed, difficulty)

    session = Session(
        join_code=join_code,
        seed=seed,
        device_ps_json=json.dumps(ps),
        device_count=device_count,
        max_turns=max_turns,
        test_budget=test_budget,
        min_n=min_n,
        max_n=max_n,
        premium_scale=premium_scale,
        confidence_fee_json=json.dumps(DEFAULT_CONFIDENCE_FEE),
        miss_penalty_json=json.dumps(DEFAULT_MISS_PENALTY),
        require_prior_test=DEFAULT_REQUIRE_PRIOR_TEST,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return RedirectResponse(url=f"/admin/s/{session.id}", status_code=303)


# ── Session admin dashboard ───────────────────────────────────────────────────

@router.get("/s/{session_id}", response_class=HTMLResponse)
def admin_session_dashboard(session_id: str, request: Request, db: DBSession = Depends(get_db)):
    if not _require_admin(request):
        return RedirectResponse(url="/admin", status_code=303)

    session = db.query(Session).filter_by(id=session_id).first()
    if not session:
        return RedirectResponse(url="/admin/dashboard", status_code=303)

    leaderboard = get_leaderboard(db, session.id)
    players = db.query(Player).filter_by(session_id=session.id).all()
    device_ps = json.loads(session.device_ps_json)

    return templates.TemplateResponse("admin_session.html", {
        "request": request,
        "session": session,
        "leaderboard": leaderboard,
        "players": players,
        "device_ps": device_ps,
    })


# ── Start / End ────────────────────────────────────────────────────────────────

@router.post("/session/{session_id}/start")
def start_session(session_id: str, request: Request, db: DBSession = Depends(get_db)):
    if not _require_admin(request):
        return RedirectResponse(url="/admin", status_code=303)
    session = db.query(Session).filter_by(id=session_id).first()
    if session and session.status == "lobby":
        session.status = "active"
        event = Event(session_id=session.id, type="SYSTEM", payload_json=json.dumps({"message": "Session started"}))
        db.add(event)
        db.commit()
    return RedirectResponse(url=f"/admin/s/{session_id}", status_code=303)


@router.post("/session/{session_id}/end")
def end_session(session_id: str, request: Request, db: DBSession = Depends(get_db)):
    if not _require_admin(request):
        return RedirectResponse(url="/admin", status_code=303)
    session = db.query(Session).filter_by(id=session_id).first()
    if session and session.status == "active":
        session.status = "ended"
        event = Event(session_id=session.id, type="SYSTEM", payload_json=json.dumps({"message": "Session ended"}))
        db.add(event)
        db.commit()
    return RedirectResponse(url=f"/admin/s/{session_id}", status_code=303)


# ── Reveal ─────────────────────────────────────────────────────────────────────

@router.get("/session/{session_id}/reveal")
def reveal_ps(session_id: str, request: Request, db: DBSession = Depends(get_db)):
    if not _require_admin(request):
        return {"error": "Unauthorized"}
    session = db.query(Session).filter_by(id=session_id).first()
    if not session:
        return {"error": "Not found"}
    if session.status != "ended":
        return {"error": "Session must be ended to reveal probabilities."}
    return {
        "session_id": session.id,
        "device_ps": json.loads(session.device_ps_json),
    }


# ── CSV export ─────────────────────────────────────────────────────────────────

@router.get("/session/{session_id}/export")
def export_events_csv(session_id: str, request: Request, db: DBSession = Depends(get_db)):
    if not _require_admin(request):
        return RedirectResponse(url="/admin", status_code=303)

    events = (
        db.query(Event)
        .filter_by(session_id=session_id)
        .order_by(Event.ts.asc())
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "session_id", "player_id", "ts", "type", "payload", "delta_score"])
    for e in events:
        writer.writerow([e.id, e.session_id, e.player_id, e.ts, e.type, e.payload_json, e.delta_score])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=events_{session_id}.csv"},
    )
