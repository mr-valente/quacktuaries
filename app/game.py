"""Core game logic: device generation, test simulation, policy scoring."""

from __future__ import annotations

import json
import math
import random
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session as DBSession

from app.models import Session, Player, DeviceStat, Event
from app.config import TURN_COST, BUDGET_COST, BUDGET_PURCHASE_AMOUNT


# ── Device generation ──────────────────────────────────────────────────────────

DIFFICULTY_PRESETS: dict[str, dict] = {
    "easy": {
        "description": "wide spread of defect rates",
        "p_ranges": [(0.05, 0.25), (0.35, 0.65), (0.75, 0.95)],
        "device_count": 8,
        "max_turns": 20,
        "test_budget": 500,
        "min_n": 5,
        "max_n": 100,
    },
    "medium": {
        "description": "moderate clustering",
        "p_ranges": [(0.15, 0.40), (0.40, 0.70), (0.60, 0.85)],
        "device_count": 10,
        "max_turns": 20,
        "test_budget": 400,
        "min_n": 5,
        "max_n": 80,
    },
    "hard": {
        "description": "tightly clustered rates",
        "p_ranges": [(0.25, 0.50), (0.45, 0.65), (0.50, 0.75)],
        "device_count": 12,
        "max_turns": 18,
        "test_budget": 300,
        "min_n": 10,
        "max_n": 60,
    },
}


def generate_device_ps(device_count: int, seed: int, difficulty: str = "medium") -> list[float]:
    """Generate hidden device probabilities using the given seed and difficulty."""
    rng = random.Random(seed)
    preset = DIFFICULTY_PRESETS.get(difficulty, DIFFICULTY_PRESETS["medium"])
    ranges = preset["p_ranges"]

    ps: list[float] = []
    for i in range(device_count):
        lo, hi = ranges[i % len(ranges)]
        p = round(rng.uniform(lo, hi), 4)
        ps.append(p)

    rng.shuffle(ps)
    return ps


def generate_join_code() -> str:
    """Generate a 6-character alphanumeric join code."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no ambiguous chars
    return "".join(secrets.choice(alphabet) for _ in range(6))


# ── Test action ────────────────────────────────────────────────────────────────

@dataclass
class TestResult:
    device_id: int
    n: int
    x: int  # successes observed
    budget_used: int
    turns_used: int


def execute_test(
    db: DBSession,
    player: Player,
    session: Session,
    device_id: int,
    n: int,
) -> TestResult:
    """Run a TEST action: draw x ~ Binomial(n, p_i), update stats."""
    ps = json.loads(session.device_ps_json)
    settings = _session_settings(session)

    # Validation
    if session.status != "active":
        raise GameError("Session is not active.")
    _check_time_expired(db, session)
    if device_id < 0 or device_id >= session.device_count:
        raise GameError(f"Invalid batch id {device_id}.")
    if n < settings["min_n"] or n > settings["max_n"]:
        raise GameError(f"n must be between {settings['min_n']} and {settings['max_n']}.")
    if player.turns_used >= session.max_turns + player.extra_turns:
        raise GameError("No turns remaining.")
    if player.budget_used + n > session.test_budget + player.extra_budget:
        raise GameError(f"Insufficient inspection budget (have {session.test_budget + player.extra_budget - player.budget_used}, need {n}).")

    # Block inspecting a batch that already has a sold policy
    if _has_sold_device(db, player.id, session.id, device_id):
        raise GameError(f"You've already sold a policy on Batch {device_id}. No need to inspect it further!")

    p_i = ps[device_id]
    x = sum(1 for _ in range(n) if secrets.randbelow(10000) < int(p_i * 10000))

    # Update device stats
    stat = (
        db.query(DeviceStat)
        .filter_by(player_id=player.id, device_id=device_id)
        .first()
    )
    if stat is None:
        stat = DeviceStat(player_id=player.id, device_id=device_id, x_total=0, n_total=0)
        db.add(stat)
    stat.x_total += x
    stat.n_total += n

    player.turns_used += 1
    player.budget_used += n

    # Log event
    event = Event(
        session_id=session.id,
        player_id=player.id,
        type="TEST",
        payload_json=json.dumps({
            "device_id": device_id,
            "n": n,
            "x": x,
        }),
        delta_score=0,
    )
    db.add(event)
    db.commit()

    return TestResult(device_id=device_id, n=n, x=x, budget_used=player.budget_used, turns_used=player.turns_used)


# ── Sell-Policy action ─────────────────────────────────────────────────────────

@dataclass
class SellResult:
    device_id: int
    confidence: str
    L: float
    U: float
    premium: int
    penalty: int
    delta: int
    hit: bool
    p_i: float  # revealed only after game ends (but stored)


def execute_sell(
    db: DBSession,
    player: Player,
    session: Session,
    device_id: int,
    confidence: str,
    L: float,
    U: float,
) -> SellResult:
    """Run a SELL_POLICY action."""
    ps = json.loads(session.device_ps_json)
    settings = _session_settings(session)

    if session.status != "active":
        raise GameError("Session is not active.")
    _check_time_expired(db, session)
    if device_id < 0 or device_id >= session.device_count:
        raise GameError(f"Invalid batch id {device_id}.")
    if player.turns_used >= session.max_turns + player.extra_turns:
        raise GameError("No turns remaining.")

    conf_key = confidence
    if conf_key not in settings["confidence_bonus"]:
        raise GameError(f"Invalid confidence level: {confidence}. Choose from {list(settings['confidence_bonus'].keys())}.")

    if not (0.0 <= L < U <= 1.0):
        raise GameError("Require 0 <= L < U <= 1.")

    # Check prior test requirement
    if settings["require_prior_test"]:
        stat = db.query(DeviceStat).filter_by(player_id=player.id, device_id=device_id).first()
        if stat is None or stat.n_total == 0:
            raise GameError("You must inspect this batch at least once before selling a policy on it.")

    # Check one-policy-per-batch limit
    if _has_sold_device(db, player.id, session.id, device_id):
        raise GameError(f"You've already sold a policy on Batch {device_id}. One policy per batch!")

    p_i = ps[device_id]
    w = U - L
    premium = max(0, math.floor(settings["premium_scale"] * (1 - w) ** 2 * settings["confidence_bonus"][conf_key]))
    hit = L <= p_i <= U
    penalty = 0 if hit else settings["miss_penalty"][conf_key]
    delta = premium - penalty

    player.turns_used += 1
    player.score += delta

    # Log event
    event = Event(
        session_id=session.id,
        player_id=player.id,
        type="SELL",
        payload_json=json.dumps({
            "device_id": device_id,
            "confidence": confidence,
            "L": L,
            "U": U,
            "w": round(w, 4),
            "premium": premium,
            "penalty": penalty,
            "delta": delta,
            "hit": hit,
        }),
        delta_score=delta,
    )
    db.add(event)
    db.commit()

    return SellResult(
        device_id=device_id,
        confidence=confidence,
        L=L, U=U,
        premium=premium,
        penalty=penalty,
        delta=delta,
        hit=hit,
        p_i=p_i,
    )


# ── Purchase actions ────────────────────────────────────────────────────────────

@dataclass
class PurchaseResult:
    item: str
    cost: int
    amount: int  # how many turns or budget units gained


def execute_purchase_turn(
    db: DBSession,
    player: Player,
    session: Session,
) -> PurchaseResult:
    """Spend score to buy 1 extra turn."""
    if session.status != "active":
        raise GameError("Session is not active.")
    _check_time_expired(db, session)
    if player.score < TURN_COST:
        raise GameError(f"Not enough score to buy a turn (need {TURN_COST}, have {player.score}).")

    player.score -= TURN_COST
    player.extra_turns += 1

    event = Event(
        session_id=session.id,
        player_id=player.id,
        type="PURCHASE",
        payload_json=json.dumps({"item": "turn", "cost": TURN_COST, "amount": 1}),
        delta_score=-TURN_COST,
    )
    db.add(event)
    db.commit()

    return PurchaseResult(item="turn", cost=TURN_COST, amount=1)


def execute_purchase_budget(
    db: DBSession,
    player: Player,
    session: Session,
) -> PurchaseResult:
    """Spend score to buy extra inspection budget."""
    if session.status != "active":
        raise GameError("Session is not active.")
    _check_time_expired(db, session)
    if player.score < BUDGET_COST:
        raise GameError(f"Not enough score to buy budget (need {BUDGET_COST}, have {player.score}).")

    player.score -= BUDGET_COST
    player.extra_budget += BUDGET_PURCHASE_AMOUNT

    event = Event(
        session_id=session.id,
        player_id=player.id,
        type="PURCHASE",
        payload_json=json.dumps({
            "item": "budget",
            "cost": BUDGET_COST,
            "amount": BUDGET_PURCHASE_AMOUNT,
        }),
        delta_score=-BUDGET_COST,
    )
    db.add(event)
    db.commit()

    return PurchaseResult(item="budget", cost=BUDGET_COST, amount=BUDGET_PURCHASE_AMOUNT)


# ── Helpers ────────────────────────────────────────────────────────────────────

class GameError(Exception):
    """Raised when a game rule is violated."""


def get_remaining_seconds(session: Session) -> int | None:
    """Return seconds remaining for an active session, or None if no timer."""
    if session.started_at is None or session.time_limit_minutes <= 0:
        return None
    started = session.started_at
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    elapsed = (datetime.now(timezone.utc) - started).total_seconds()
    remaining = session.time_limit_minutes * 60 - elapsed
    return max(0, int(remaining))


def _check_time_expired(db: DBSession, session: Session) -> None:
    """If the session's time limit has elapsed, auto-end it and raise."""
    remaining = get_remaining_seconds(session)
    if remaining is not None and remaining <= 0 and session.status == "active":
        session.status = "ended"
        event = Event(
            session_id=session.id,
            type="SYSTEM",
            payload_json=json.dumps({"message": "Time expired — session ended automatically"}),
        )
        db.add(event)
        db.commit()
        raise GameError("Time's up! The game has ended.")


def _has_sold_device(db: DBSession, player_id: str, session_id: str, device_id: int) -> bool:
    """Check whether a player has already sold a policy on a specific device.

    Uses proper JSON parsing instead of substring matching to avoid
    false positives (e.g. device_id 1 matching device_id 10).
    """
    sell_events = (
        db.query(Event)
        .filter_by(player_id=player_id, session_id=session_id, type="SELL")
        .all()
    )
    for e in sell_events:
        payload = json.loads(e.payload_json)
        if payload.get("device_id") == device_id:
            return True
    return False


def _session_settings(session: Session) -> dict:
    return {
        "min_n": session.min_n,
        "max_n": session.max_n,
        "premium_scale": session.premium_scale,
        "confidence_bonus": json.loads(session.confidence_bonus_json),
        "miss_penalty": json.loads(session.miss_penalty_json),
        "require_prior_test": session.require_prior_test,
    }


def get_leaderboard(db: DBSession, session_id: str) -> list[dict]:
    """Return sorted leaderboard for a session."""
    players = (
        db.query(Player)
        .filter_by(session_id=session_id)
        .order_by(Player.score.desc())
        .all()
    )
    return [
        {
            "rank": i + 1,
            "name": p.name,
            "score": p.score,
            "turns_used": p.turns_used,
            "budget_used": p.budget_used,
            "player_id": p.id,
        }
        for i, p in enumerate(players)
    ]


def get_player_devices(db: DBSession, player_id: str, device_count: int) -> list[dict]:
    """Return list of device stats for a player."""
    stats = {
        s.device_id: s
        for s in db.query(DeviceStat).filter_by(player_id=player_id).all()
    }
    # Find which batches already have a sold policy
    sell_events = db.query(Event).filter_by(player_id=player_id, type="SELL").all()
    sold_device_ids = set()
    for e in sell_events:
        payload = json.loads(e.payload_json)
        sold_device_ids.add(payload["device_id"])

    devices = []
    for d in range(device_count):
        s = stats.get(d)
        devices.append({
            "device_id": d,
            "n_total": s.n_total if s else 0,
            "x_total": s.x_total if s else 0,
            "tested": s is not None and s.n_total > 0,
            "sold": d in sold_device_ids,
        })
    return devices


def get_player_events(db: DBSession, player_id: str, limit: int = 20) -> list[dict]:
    """Return recent events for a player."""
    events = (
        db.query(Event)
        .filter_by(player_id=player_id)
        .order_by(Event.ts.desc())
        .limit(limit)
        .all()
    )
    results = []
    for e in events:
        payload = json.loads(e.payload_json)
        results.append({
            "id": e.id,
            "type": e.type,
            "ts": e.ts.isoformat() if e.ts else "",
            "payload": payload,
            "delta_score": e.delta_score,
        })
    return results
