"""Completed Quacktuaries runs for the shared performance contract."""
import json
from datetime import timezone
from app.ecosystem import AccountLink
from app.models import Player, Session, Event


def snapshots(db, session_ids=None):
    query = (db.query(Player, AccountLink, Session)
             .join(AccountLink, AccountLink.local_id == Player.id)
             .join(Session, Session.id == Player.session_id)
             .filter(AccountLink.role == 'player', AccountLink.kind == 'google', Session.status == 'ended'))
    if session_ids is not None:
        query = query.filter(Session.id.in_(session_ids))
    for player, link, session in query:
        events = db.query(Event).filter_by(player_id=player.id).order_by(Event.ts, Event.id).all()
        sold = [json.loads(e.payload_json) for e in events if e.type == 'SELL']
        tested = [json.loads(e.payload_json) for e in events if e.type == 'TEST']
        ts = max([e.ts for e in events] + [session.started_at or session.created_at])
        yield {
            'source_id': 'session:' + player.id, 'user_id': link.account_id,
            'activity': 'quacktuaries', 'occurred_at': ts.replace(tzinfo=timezone.utc).isoformat(),
            'metrics': {'score': player.score, 'policies_sold': len(sold),
                        'intervals_covering_truth': sum(bool(s['hit']) for s in sold),
                        'mean_interval_width': sum(s['w'] for s in sold)/len(sold) if sold else None,
                        'samples_inspected': sum(t['n'] for t in tested),
                        'turns_used': player.turns_used, 'budget_used': player.budget_used,
                        'policies': sold},
            'context': {'classroom_id': session.id, 'device_count': session.device_count,
                        'max_turns': session.max_turns, 'test_budget': session.test_budget,
                        'premium_scale': session.premium_scale,
                        'confidence_bonus': json.loads(session.confidence_bonus_json),
                        'miss_penalty': json.loads(session.miss_penalty_json)},
        }
