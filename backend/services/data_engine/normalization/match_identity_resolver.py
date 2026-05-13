from __future__ import annotations
from datetime import datetime
from typing import Any
import os


def _date(value: Any) -> str:
    try:
        return str(datetime.fromisoformat(str(value).replace('Z','+00:00')).date())
    except Exception:
        return str(value or '')[:10]

def _hour(value: Any) -> int | None:
    try:
        text = str(value or '').strip()
        if not text: return None
        return int(text.split(':')[0])
    except Exception:
        return None

def build_match_identity_key(record: dict) -> str:
    parts = [
        record.get('canonical_league_id') or record.get('league') or 'unknown_league',
        record.get('canonical_home_team_id') or record.get('home_team_key') or record.get('home_team') or 'home',
        record.get('canonical_away_team_id') or record.get('away_team_key') or record.get('away_team') or 'away',
        _date(record.get('match_date') or record.get('date')),
        str(record.get('season') or '')
    ]
    return '|'.join(str(p).lower().replace(' ', '_') for p in parts)

def resolve_match_identity(record: dict) -> dict:
    key = build_match_identity_key(record)
    warnings = []
    if not record.get('canonical_home_team_id') or not record.get('canonical_away_team_id'):
        warnings.append('missing_canonical_team_id')
    if not record.get('canonical_league_id'):
        warnings.append('missing_canonical_league_id')
    if not _date(record.get('match_date')):
        warnings.append('missing_match_date')
    confidence = 1.0 - min(0.5, 0.12 * len(warnings))
    return {'match_identity_key': key, 'identity_confidence': round(confidence, 3), 'identity_warnings': warnings, 'provider_match_ids': {str(record.get('source') or 'unknown'): str(record.get('match_id') or key)}, 'linked_sources': [str(record.get('source') or 'unknown')]}

def kickoff_conflict(a: dict, b: dict) -> bool:
    if _date(a.get('match_date')) != _date(b.get('match_date')):
        return True
    ah, bh = _hour(a.get('kickoff_time')), _hour(b.get('kickoff_time'))
    if ah is None or bh is None:
        return False
    return abs(ah - bh) > int(os.getenv('MATCH_TIME_TOLERANCE_HOURS', '24'))
