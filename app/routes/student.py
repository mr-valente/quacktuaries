"""Student routes: dashboard, test, sell."""

import json
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session as DBSession

from app import ecosystem
from app.database import get_db
from app.models import Session, Player
from app.game import (
    GameError,
    execute_test,
    execute_sell,
    execute_purchase_turn,
    execute_purchase_budget,
    get_leaderboard,
    get_player_devices,
    get_player_events,
    get_remaining_seconds,
    _check_time_expired,
)
from app.templating import templates
from app.config import TURN_COST, BUDGET_COST, BUDGET_PURCHASE_AMOUNT

router = APIRouter()


def _get_player(request: Request, session_id: str, db: DBSession):
    """Retrieve the current player from the session cookie."""
    player = ecosystem.owned(request, db, "player", Player, session_id)
    if player:
        ecosystem.remember_binding(request)
    else:
        player_id = request.session.get("player_id")
        player = db.query(Player).filter_by(id=player_id, session_id=session_id).first() if player_id else None
        if not ecosystem.permitted(request, db, "player", player):
            return None, None
    session = db.query(Session).filter_by(id=session_id).first()
    return player, session


@router.get("/s/{session_id}", response_class=HTMLResponse)
def student_dashboard(session_id: str, request: Request, db: DBSession = Depends(get_db)):
    player, session = _get_player(request, session_id, db)
    if player is None:
        return RedirectResponse(url=request.url_for("join_form"), status_code=303)

    # Auto-end if time expired
    if session.status == "active":
        try:
            _check_time_expired(db, session)
        except Exception:
            pass

    devices = get_player_devices(db, player.id, session.device_count)
    events = get_player_events(db, player.id, limit=20)
    leaderboard = get_leaderboard(db, session.id)
    conf_bonus = json.loads(session.confidence_bonus_json)
    remaining = get_remaining_seconds(session)

    return templates.TemplateResponse(request=request, name="student_dashboard.html", context={
        "request": request,
        "session": session,
        "player": player,
        "devices": devices,
        "events": events,
        "leaderboard": leaderboard,
        "confidence_levels": list(conf_bonus.keys()),
        "turn_cost": TURN_COST,
        "budget_cost": BUDGET_COST,
        "budget_amount": BUDGET_PURCHASE_AMOUNT,
        "remaining_seconds": remaining,
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
        return RedirectResponse(url=request.url_for("join_form"), status_code=303)

    try:
        result = execute_test(db, player, session, device_id, n)
        msg = f"INSPECT Batch {result.device_id}: {result.x}/{result.n} defective ducks found 🦆"
        return RedirectResponse(url=request.url_for("student_dashboard", session_id=session_id).include_query_params(success=msg), status_code=303)
    except GameError as e:
        return RedirectResponse(url=request.url_for("student_dashboard", session_id=session_id).include_query_params(error=str(e)), status_code=303)


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
        return RedirectResponse(url=request.url_for("join_form"), status_code=303)

    try:
        result = execute_sell(db, player, session, device_id, confidence, lower, upper)
        if result.hit:
            msg = f"SELL Batch {result.device_id}: HIT! ✅ Premium {result.premium}, +{result.delta} points"
        else:
            msg = f"SELL Batch {result.device_id}: MISS ❌ Premium {result.premium}, Penalty {result.penalty}, {result.delta} points"
        return RedirectResponse(url=request.url_for("student_dashboard", session_id=session_id).include_query_params(success=msg), status_code=303)
    except GameError as e:
        return RedirectResponse(url=request.url_for("student_dashboard", session_id=session_id).include_query_params(error=str(e)), status_code=303)


@router.post("/session/{session_id}/buy-turn")
def buy_turn(
    session_id: str,
    request: Request,
    db: DBSession = Depends(get_db),
):
    player, session = _get_player(request, session_id, db)
    if player is None:
        return RedirectResponse(url=request.url_for("join_form"), status_code=303)

    try:
        result = execute_purchase_turn(db, player, session)
        msg = f"Purchased 1 extra turn for {result.cost} 🪙"
        return RedirectResponse(url=request.url_for("student_dashboard", session_id=session_id).include_query_params(success=msg), status_code=303)
    except GameError as e:
        return RedirectResponse(url=request.url_for("student_dashboard", session_id=session_id).include_query_params(error=str(e)), status_code=303)


@router.post("/session/{session_id}/buy-budget")
def buy_budget(
    session_id: str,
    request: Request,
    db: DBSession = Depends(get_db),
):
    player, session = _get_player(request, session_id, db)
    if player is None:
        return RedirectResponse(url=request.url_for("join_form"), status_code=303)

    try:
        result = execute_purchase_budget(db, player, session)
        msg = f"Purchased {result.amount} extra budget for {result.cost} 🪙"
        return RedirectResponse(url=request.url_for("student_dashboard", session_id=session_id).include_query_params(success=msg), status_code=303)
    except GameError as e:
        return RedirectResponse(url=request.url_for("student_dashboard", session_id=session_id).include_query_params(error=str(e)), status_code=303)
