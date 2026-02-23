"""Admin / Teacher routes: login, session management, dashboard."""

import csv
import io
import json
import secrets

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session as DBSession

from app.config import (
    DEFAULT_DEVICE_COUNT,
    DEFAULT_MAX_TURNS,
    DEFAULT_TEST_BUDGET,
    DEFAULT_MIN_N,
    DEFAULT_MAX_N,
    DEFAULT_PREMIUM_SCALE,
    DEFAULT_CONFIDENCE_BONUS,
    DEFAULT_MISS_PENALTY,
    DEFAULT_REQUIRE_PRIOR_TEST,
)
from app.database import get_db
from app.models import Session, Player, Event, Teacher
from app.game import (
    generate_device_ps,
    generate_join_code,
    get_leaderboard,
    DIFFICULTY_PRESETS,
)
from app.templating import templates

router = APIRouter(prefix="/admin")


def _get_teacher(request: Request, db: DBSession):
    """Return the current Teacher from the session cookie, or None."""
    teacher_id = request.session.get("teacher_id")
    if not teacher_id:
        return None
    return db.query(Teacher).filter_by(id=teacher_id).first()


def _require_own_session(teacher: Teacher, session: Session) -> bool:
    """Check that the teacher owns the given session."""
    return teacher is not None and session is not None and session.teacher_id == teacher.id


# ── Login ──────────────────────────────────────────────────────────────────────

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def admin_login_page(request: Request, db: DBSession = Depends(get_db)):
    teacher = _get_teacher(request, db)
    if teacher:
        return RedirectResponse(url="/admin/dashboard", status_code=303)
    return templates.TemplateResponse("admin_login.html", {"request": request, "error": None})


@router.post("/login")
def admin_login(request: Request, teacher_name: str = Form(...), db: DBSession = Depends(get_db)):
    teacher_name = teacher_name.strip()
    if not teacher_name:
        return templates.TemplateResponse(
            "admin_login.html",
            {"request": request, "error": "Please enter your name."},
            status_code=400,
        )

    # Check if a teacher with this name already exists
    existing = db.query(Teacher).filter_by(name=teacher_name).first()
    if existing:
        # Re-login: verify the rejoin token from the cookie
        cookie_token = request.session.get("teacher_rejoin_token")
        if cookie_token != existing.rejoin_token:
            return templates.TemplateResponse(
                "admin_login.html",
                {"request": request, "error": "That teacher name is already taken."},
                status_code=400,
            )
        request.session["teacher_id"] = existing.id
        return RedirectResponse(url="/admin/dashboard", status_code=303)

    rejoin_token = secrets.token_hex(16)
    teacher = Teacher(name=teacher_name, rejoin_token=rejoin_token)
    db.add(teacher)
    db.commit()
    db.refresh(teacher)

    request.session["teacher_id"] = teacher.id
    request.session["teacher_rejoin_token"] = rejoin_token
    return RedirectResponse(url="/admin/dashboard", status_code=303)


@router.get("/logout")
def admin_logout(request: Request):
    request.session.pop("teacher_id", None)
    return RedirectResponse(url="/", status_code=303)


# ── Dashboard ──────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_class=HTMLResponse)
def admin_dashboard(request: Request, db: DBSession = Depends(get_db)):
    teacher = _get_teacher(request, db)
    if not teacher:
        return RedirectResponse(url="/admin", status_code=303)
    sessions = (
        db.query(Session)
        .filter_by(teacher_id=teacher.id)
        .order_by(Session.created_at.desc())
        .all()
    )
    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request,
        "sessions": sessions,
        "teacher": teacher,
    })


# ── Create session ─────────────────────────────────────────────────────────────

@router.get("/sessions/new", response_class=HTMLResponse)
def new_session_form(request: Request, db: DBSession = Depends(get_db)):
    teacher = _get_teacher(request, db)
    if not teacher:
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
        "teacher": teacher,
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
    teacher = _get_teacher(request, db)
    if not teacher:
        return RedirectResponse(url="/admin", status_code=303)

    seed = secrets.randbelow(2**31)
    join_code = generate_join_code()

    # Ensure unique join code
    while db.query(Session).filter_by(join_code=join_code).first():
        join_code = generate_join_code()

    ps = generate_device_ps(device_count, seed, difficulty)

    session = Session(
        teacher_id=teacher.id,
        join_code=join_code,
        seed=seed,
        device_ps_json=json.dumps(ps),
        device_count=device_count,
        max_turns=max_turns,
        test_budget=test_budget,
        min_n=min_n,
        max_n=max_n,
        premium_scale=premium_scale,
        confidence_bonus_json=json.dumps(DEFAULT_CONFIDENCE_BONUS),
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
    teacher = _get_teacher(request, db)
    if not teacher:
        return RedirectResponse(url="/admin", status_code=303)

    session = db.query(Session).filter_by(id=session_id).first()
    if not session or not _require_own_session(teacher, session):
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
        "teacher": teacher,
    })


# ── Start / End ────────────────────────────────────────────────────────────────

@router.post("/session/{session_id}/start")
def start_session(
    session_id: str,
    request: Request,
    lock_session: bool = Form(False),
    db: DBSession = Depends(get_db),
):
    teacher = _get_teacher(request, db)
    if not teacher:
        return RedirectResponse(url="/admin", status_code=303)
    session = db.query(Session).filter_by(id=session_id).first()
    if session and _require_own_session(teacher, session) and session.status == "lobby":
        session.status = "active"
        session.locked = lock_session
        event = Event(session_id=session.id, type="SYSTEM", payload_json=json.dumps({"message": "Session started"}))
        db.add(event)
        db.commit()
    return RedirectResponse(url=f"/admin/s/{session_id}", status_code=303)


@router.post("/session/{session_id}/end")
def end_session(session_id: str, request: Request, db: DBSession = Depends(get_db)):
    teacher = _get_teacher(request, db)
    if not teacher:
        return RedirectResponse(url="/admin", status_code=303)
    session = db.query(Session).filter_by(id=session_id).first()
    if session and _require_own_session(teacher, session) and session.status == "active":
        session.status = "ended"
        event = Event(session_id=session.id, type="SYSTEM", payload_json=json.dumps({"message": "Session ended"}))
        db.add(event)
        db.commit()
    return RedirectResponse(url=f"/admin/s/{session_id}", status_code=303)


# ── Reveal ─────────────────────────────────────────────────────────────────────

@router.get("/session/{session_id}/reveal")
def reveal_ps(session_id: str, request: Request, db: DBSession = Depends(get_db)):
    teacher = _get_teacher(request, db)
    if not teacher:
        return {"error": "Unauthorized"}
    session = db.query(Session).filter_by(id=session_id).first()
    if not session or not _require_own_session(teacher, session):
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
    teacher = _get_teacher(request, db)
    if not teacher:
        return RedirectResponse(url="/admin", status_code=303)
    session_obj = db.query(Session).filter_by(id=session_id).first()
    if not session_obj or not _require_own_session(teacher, session_obj):
        return RedirectResponse(url="/admin/dashboard", status_code=303)

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
