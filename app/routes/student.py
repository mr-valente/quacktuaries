"""Student routes: dashboard, test, sell."""

import json
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.models import Session, Player
from app.game import (
    GameError,
    execute_test,
    execute_sell,
    get_leaderboard,
    get_player_devices,
    get_player_events,
)
from app.templating import templates

router = APIRouter()


def _get_player(request: Request, session_id: str, db: DBSession):
    """Retrieve the current player from the session cookie."""
    player_id = request.session.get("player_id")
    if not player_id:
        return None, None
    player = db.query(Player).filter_by(id=player_id, session_id=session_id).first()
    if not player:
        return None, None
    session = db.query(Session).filter_by(id=session_id).first()
    return player, session


@router.get("/s/{session_id}", response_class=HTMLResponse)
def student_dashboard(session_id: str, request: Request, db: DBSession = Depends(get_db)):
    player, session = _get_player(request, session_id, db)
    if player is None:
        return RedirectResponse(url="/join", status_code=303)

    devices = get_player_devices(db, player.id, session.device_count)
    events = get_player_events(db, player.id, limit=20)
    leaderboard = get_leaderboard(db, session.id)
    conf_fee = json.loads(session.confidence_fee_json)

    return templates.TemplateResponse("student_dashboard.html", {
        "request": request,
        "session": session,
        "player": player,
        "devices": devices,
        "events": events,
        "leaderboard": leaderboard,
        "confidence_levels": list(conf_fee.keys()),
        "error": request.query_params.get("error"),
        "success": request.query_params.get("success"),
    })


@router.post("/session/{session_id}/test")
def do_test(
    session_id: str,
    request: Request,
    device_id: int = Form(...),
    n: int = Form(...),
    db: DBSession = Depends(get_db),
):
    player, session = _get_player(request, session_id, db)
    if player is None:
        return RedirectResponse(url="/join", status_code=303)

    try:
        result = execute_test(db, player, session, device_id, n)
        msg = f"INSPECT Batch {result.device_id}: {result.x}/{result.n} defective ducks found 🦆"
        return RedirectResponse(url=f"/s/{session_id}?success={msg}", status_code=303)
    except GameError as e:
        return RedirectResponse(url=f"/s/{session_id}?error={str(e)}", status_code=303)


@router.post("/session/{session_id}/sell")
def do_sell(
    session_id: str,
    request: Request,
    device_id: int = Form(...),
    confidence: str = Form(...),
    lower: float = Form(...),
    upper: float = Form(...),
    db: DBSession = Depends(get_db),
):
    player, session = _get_player(request, session_id, db)
    if player is None:
        return RedirectResponse(url="/join", status_code=303)

    try:
        result = execute_sell(db, player, session, device_id, confidence, lower, upper)
        if result.hit:
            msg = f"SELL Batch {result.device_id}: HIT! ✅ Premium {result.premium}, +{result.delta} points"
        else:
            msg = f"SELL Batch {result.device_id}: MISS ❌ Premium {result.premium}, Penalty {result.penalty}, {result.delta} points"
        return RedirectResponse(url=f"/s/{session_id}?success={msg}", status_code=303)
    except GameError as e:
        return RedirectResponse(url=f"/s/{session_id}?error={str(e)}", status_code=303)
