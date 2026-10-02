"""Public routes: home page, join session, student guide."""

import json
import os
import re
import secrets
import markdown
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session as DBSession

from app import ecosystem
from app.routes.student import _get_player
from app.database import get_db
from app.models import Session, Player
from app.game import get_leaderboard
from app.templating import templates

router = APIRouter()


def _render_guide_md(md_text: str) -> str:
    """Render markdown to HTML, preserving LaTeX math blocks for KaTeX."""
    # Extract and protect math blocks from markdown processing
    placeholders = {}
    counter = 0

    def _protect(match):
        nonlocal counter
        key = f"\x00MATH{counter}\x00"
        placeholders[key] = match.group(0)
        counter += 1
        return key

    # Protect $$...$$ (display) first, then $...$ (inline)
    md_text = re.sub(r'\$\$.*?\$\$', _protect, md_text, flags=re.DOTALL)
    md_text = re.sub(r'\$[^\$\n]+?\$', _protect, md_text)

    html = markdown.markdown(md_text, extensions=["tables", "fenced_code"])

    # Restore math blocks
    for key, val in placeholders.items():
        html = html.replace(key, val)

    return html


# Pre-render the student guide markdown
_base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_guide_md_path = os.path.join(_base_dir, "docs", "student-guide.md")
with open(_guide_md_path, "r") as f:
    _guide_html = _render_guide_md(f.read())


@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request=request, name="home.html", context={"request": request})


@router.get("/guide", response_class=HTMLResponse)
def student_guide(request: Request):
    return templates.TemplateResponse(request=request, name="guide.html", context={"request": request, "guide_html": _guide_html})


@router.get("/join", response_class=HTMLResponse)
def join_form(request: Request):
    return templates.TemplateResponse(request=request, name="join.html", context={"request": request, "error": None})


@router.post("/session/join")
def join_session(
    request: Request,
    join_code: str = Form(...),
    player_name: str = Form(''),
    db: DBSession = Depends(get_db),
):
    join_code = join_code.strip().upper()
    player_name = ecosystem.display_name(request, ' '.join(player_name.split())[:60])

    if not player_name:
        return templates.TemplateResponse(request=request, name="join.html", context={"request": request, "error": "Please enter your name."},
            status_code=400,
        )

    ecosystem.lock_profiles(db)
    session = db.query(Session).filter_by(join_code=join_code).first()
    if session is None:
        return templates.TemplateResponse(request=request, name="join.html", context={"request": request, "error": f"No session found with code '{join_code}'."},
            status_code=404,
        )

    if session.status == "ended":
        return templates.TemplateResponse(request=request, name="join.html", context={"request": request, "error": "This session has already ended."},
            status_code=400,
        )

    user = ecosystem.account(request)
    persistent = user and user['kind'] == 'google'
    linked = ecosystem.owned(request, db, "player", Player, session.id)
    browser_player = db.get(Player, request.session.get("player_id", ""))
    if not (browser_player and browser_player.session_id == session.id
            and request.session.get("rejoin_token") == browser_player.rejoin_token
            and ecosystem.permitted(request, db, "player", browser_player)):
        browser_player = None
    existing = linked or browser_player
    if not persistent and db.query(Player).filter_by(session_id=session.id, name=player_name).filter(
            Player.id != (existing.id if existing else '')).first():
        return templates.TemplateResponse(request=request, name="join.html", context={"request": request, "error": "That name is already taken in this session. Try adding an initial."}, status_code=400)
    if existing:
        existing.name = player_name
        db.commit()
        ecosystem.remember_binding(request)
        request.session["player_id"] = existing.id
        request.session["session_id"] = session.id
        request.session["rejoin_token"] = existing.rejoin_token
        return RedirectResponse(url=request.url_for("student_dashboard", session_id=session.id), status_code=303)

    # Block new player creation if the session is locked
    if session.status == "active" and session.locked:
        return templates.TemplateResponse(request=request, name="join.html", context={"request": request, "error": "This game is already in progress and the session is locked. New players cannot join."},
            status_code=400,
        )

    rejoin_token = secrets.token_hex(16)
    player = Player(session_id=session.id, name=player_name, rejoin_token=rejoin_token)
    db.add(player)
    db.flush()
    ecosystem.bind(request, db, "player", player)
    db.commit()
    db.refresh(player)

    request.session["player_id"] = player.id
    request.session["session_id"] = session.id
    request.session["rejoin_token"] = rejoin_token

    return RedirectResponse(url=request.url_for("student_dashboard", session_id=session.id), status_code=303)


@router.get("/session/{session_id}/state")
def session_state(
    session_id: str,
    request: Request,
    db: DBSession = Depends(get_db),
):
    """Public JSON endpoint: session status + leaderboard + player state."""
    session = db.query(Session).filter_by(id=session_id).first()
    if not session:
        return {"error": "Session not found."}

    leaderboard = get_leaderboard(db, session_id)
    player, _ = _get_player(request, session_id, db)
    player_state = None
    if player:
        player_state = {
            "id": player.id, "name": player.name, "score": player.score,
            "turns_used": player.turns_used, "budget_used": player.budget_used,
        }

    return {
        "session_id": session.id,
        "status": session.status,
        "join_code": session.join_code,
        "leaderboard": leaderboard,
        "player": player_state,
    }
