"""Public routes: home page, join session, student guide."""

import json
import os
import re
import secrets
import markdown
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session as DBSession

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
    return templates.TemplateResponse("home.html", {"request": request})


@router.get("/guide", response_class=HTMLResponse)
def student_guide(request: Request):
    return templates.TemplateResponse("guide.html", {"request": request, "guide_html": _guide_html})


@router.get("/join", response_class=HTMLResponse)
def join_form(request: Request):
    return templates.TemplateResponse("join.html", {"request": request, "error": None})


@router.post("/session/join")
def join_session(
    request: Request,
    join_code: str = Form(...),
    player_name: str = Form(...),
    db: DBSession = Depends(get_db),
):
    join_code = join_code.strip().upper()
    player_name = player_name.strip()

    if not player_name:
        return templates.TemplateResponse(
            "join.html",
            {"request": request, "error": "Please enter your name."},
            status_code=400,
        )

    session = db.query(Session).filter_by(join_code=join_code).first()
    if session is None:
        return templates.TemplateResponse(
            "join.html",
            {"request": request, "error": f"No session found with code '{join_code}'."},
            status_code=404,
        )

    if session.status == "ended":
        return templates.TemplateResponse(
            "join.html",
            {"request": request, "error": "This session has already ended."},
            status_code=400,
        )

    # Check if player already exists (by name in this session)
    existing = db.query(Player).filter_by(session_id=session.id, name=player_name).first()
    if existing:
        # Re-join: verify the rejoin token from the cookie
        cookie_token = request.session.get("rejoin_token")
        if cookie_token != existing.rejoin_token:
            return templates.TemplateResponse(
                "join.html",
                {"request": request, "error": "That name is already taken in this session."},
                status_code=400,
            )
        request.session["player_id"] = existing.id
        request.session["session_id"] = session.id
        return RedirectResponse(url=f"/s/{session.id}", status_code=303)

    # Block new player creation once the game is active (prevents multi-accounting)
    if session.status == "active":
        return templates.TemplateResponse(
            "join.html",
            {"request": request, "error": "This game is already in progress. New players can only join during the lobby."},
            status_code=400,
        )

    rejoin_token = secrets.token_hex(16)
    player = Player(session_id=session.id, name=player_name, rejoin_token=rejoin_token)
    db.add(player)
    db.commit()
    db.refresh(player)

    request.session["player_id"] = player.id
    request.session["session_id"] = session.id
    request.session["rejoin_token"] = rejoin_token

    return RedirectResponse(url=f"/s/{session.id}", status_code=303)


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
    player_id = request.session.get("player_id")
    player_state = None
    if player_id:
        player = db.query(Player).filter_by(id=player_id, session_id=session_id).first()
        if player:
            player_state = {
                "id": player.id,
                "name": player.name,
                "score": player.score,
                "turns_used": player.turns_used,
                "budget_used": player.budget_used,
            }

    return {
        "session_id": session.id,
        "status": session.status,
        "join_code": session.join_code,
        "leaderboard": leaderboard,
        "player": player_state,
    }
