from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

_SCORE_RE = re.compile(r"^(?P<h>\d{1,2})\s*[-:–]\s*(?P<a>\d{1,2})(?:\s*\((?P<hh>\d{1,2})\s*[-:–]\s*(?P<ha>\d{1,2})\))?$")
_TIME_RE = re.compile(r"^(?:[01]?\d|2[0-3]):[0-5]\d$")
_DATE_RE = re.compile(r"(?:(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+)?(?P<d>\d{1,2})[./-](?P<m>\d{1,2})(?:[./-](?P<y>\d{2,4}))?")
_ID_RE = re.compile(r"(?:match[-_/]summary|match-detail|/match/|#/match/)[^A-Za-z0-9]*(?P<id>[A-Za-z0-9]{6,})", re.I)

MISSING_OPTIONAL_FIELDS = [
    'odds_home','odds_draw','odds_away','odds_over_05','odds_under_05','odds_over_15','odds_under_15','odds_over_25','odds_under_25','odds_btts_yes','odds_btts_no',
    'corners_home','corners_away','shots_home','shots_away','shots_on_target_home','shots_on_target_away','xg_home','xg_away',
    'goals_home_ft','goals_away_ft','goals_home_ht','goals_away_ht','goal_minutes_home','goal_minutes_away',
]


def safe_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(',', '.')
    if not text or text in {'-', '—', 'N/A', 'None', 'null'}:
        return None
    # Handle fractional odds conservatively.
    if '/' in text and re.match(r'^\d+(?:\.\d+)?/\d+(?:\.\d+)?$', text):
        a, b = text.split('/', 1)
        try:
            return round(float(a) / float(b) + 1, 4)
        except Exception:
            return None
    m = re.search(r"\d+(?:\.\d+)?", text)
    return float(m.group(0)) if m else None


def safe_int(value: Any) -> int | None:
    f = safe_float(value)
    return int(f) if f is not None else None


def append_warning(existing: Any, *warnings: str) -> str:
    parts = [x.strip() for x in str(existing or '').split(';') if x.strip()]
    for warning in warnings:
        if warning and warning not in parts:
            parts.append(warning)
    return ';'.join(parts)


def parse_score(value: Any) -> dict[str, int | None]:
    m = _SCORE_RE.match(str(value or '').strip())
    if not m:
        return {'goals_home_ft': None, 'goals_away_ft': None, 'goals_home_ht': None, 'goals_away_ht': None}
    return {
        'goals_home_ft': safe_int(m.group('h')),
        'goals_away_ft': safe_int(m.group('a')),
        'goals_home_ht': safe_int(m.group('hh')),
        'goals_away_ht': safe_int(m.group('ha')),
    }


def extract_match_id(*values: Any) -> str | None:
    for value in values:
        if value is None:
            continue
        text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
        for pattern in [
            r"data-(?:event|match|id)=['\"](?P<id>[A-Za-z0-9]{6,})['\"]",
            r"(?:eventId|event_id|matchId|match_id|flashscore_match_id|id)['\"]?\s*[:=]\s*['\"](?P<id>[A-Za-z0-9_-]{6,})['\"]",
            r"id=['\"]g_\d_(?P<id>[A-Za-z0-9]{6,})['\"]",
        ]:
            m = re.search(pattern, text, flags=re.I)
            if m:
                return m.group('id')
        m = _ID_RE.search(text)
        if m:
            return m.group('id')
    return None


def normalize_status(value: Any) -> str:
    low = str(value or '').strip().lower()
    if not low:
        return 'SCHEDULED'
    if any(x in low for x in ['finished', 'after penalties', 'aet', 'full time', 'ft']):
        return 'FINISHED'
    if any(x in low for x in ['live', '1st half', '2nd half', 'half time', 'ht']):
        return 'LIVE'
    if any(x in low for x in ['postponed', 'cancelled', 'canceled', 'abandoned']):
        return 'POSTPONED'
    return str(value).strip().upper().replace(' ', '_')[:40]


def _first(payload: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        if key not in payload:
            continue
        value = payload[key]
        if value is None:
            continue
        if isinstance(value, str) and value == '':
            continue
        return value
    return None


def _pair_from_value(value: Any) -> tuple[Any, Any] | None:
    if isinstance(value, dict):
        home = _first(value, ['home', 'homeValue', 'home_value', 'homeScore', 'home_score', 'h'])
        away = _first(value, ['away', 'awayValue', 'away_value', 'awayScore', 'away_score', 'a'])
        if home is not None and away is not None:
            return home, away
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        return value[0], value[1]
    if isinstance(value, str) and re.search(r"\d\s*[-:–]\s*\d", value):
        parts = re.split(r"\s*[-:–]\s*", value, maxsplit=1)
        return parts[0], parts[1]
    return None


def parse_stats_from_pairs(pairs: dict[str, Any] | list[Any]) -> dict[str, Any]:
    out = {
        'corners_home': None, 'corners_away': None,
        'shots_home': None, 'shots_away': None,
        'shots_on_target_home': None, 'shots_on_target_away': None,
        'xg_home': None, 'xg_away': None,
    }
    iterable: list[tuple[str, Any]] = []
    if isinstance(pairs, dict):
        iterable = list(pairs.items())
    elif isinstance(pairs, list):
        for item in pairs:
            if isinstance(item, dict):
                name = str(_first(item, ['name', 'categoryName', 'type', 'key', 'statName']) or '')
                iterable.append((name, item))
    for raw_key, value in iterable:
        key = str(raw_key).lower().strip()
        pair = _pair_from_value(value)
        if not pair:
            continue
        h, a = pair
        if 'corner' in key:
            out['corners_home'], out['corners_away'] = safe_int(h), safe_int(a)
        elif 'on target' in key or 'shots on' in key:
            out['shots_on_target_home'], out['shots_on_target_away'] = safe_int(h), safe_int(a)
        elif key in {'shots', 'goal attempts', 'total shots'} or 'shots total' in key or key == 'attempts on goal':
            out['shots_home'], out['shots_away'] = safe_int(h), safe_int(a)
        elif key in {'xg', 'expected goals'} or 'expected goals' in key:
            out['xg_home'], out['xg_away'] = safe_float(h), safe_float(a)
    return out


def parse_odds_from_markets(markets: dict[str, Any] | list[Any]) -> dict[str, Any]:
    out = {
        'odds_home': None, 'odds_draw': None, 'odds_away': None,
        'odds_over_05': None, 'odds_under_05': None,
        'odds_over_15': None, 'odds_under_15': None,
        'odds_over_25': None, 'odds_under_25': None,
        'odds_btts_yes': None, 'odds_btts_no': None,
    }
    iterable: list[tuple[str, Any]] = []
    if isinstance(markets, dict):
        iterable = list(markets.items())
    elif isinstance(markets, list):
        for item in markets:
            if isinstance(item, dict):
                name = str(_first(item, ['name', 'marketName', 'label', 'type']) or '')
                values = _first(item, ['values', 'odds', 'outcomes', 'selections']) or item
                iterable.append((name, values))
    for raw_key, value in iterable:
        key = str(raw_key).lower().strip()
        vals: list[Any] = []
        if isinstance(value, dict):
            vals = value.get('values') or value.get('odds') or value.get('outcomes') or []
            if not vals and {'home', 'draw', 'away'} & set(value.keys()):
                vals = [value.get('home'), value.get('draw'), value.get('away')]
            if not vals and {'yes', 'no'} & set(value.keys()):
                vals = [value.get('yes'), value.get('no')]
            if not vals and {'over', 'under'} & set(value.keys()):
                vals = [value.get('over'), value.get('under')]
        elif isinstance(value, (list, tuple)):
            vals = list(value)
        if vals and isinstance(vals[0], dict):
            vals = [v.get('odds') or v.get('value') or v.get('decimal') or v.get('price') for v in vals]
        if key in {'1x2', 'match winner', 'h2h', 'full time result'} and len(vals) >= 3:
            out['odds_home'], out['odds_draw'], out['odds_away'] = safe_float(vals[0]), safe_float(vals[1]), safe_float(vals[2])
        if ('over/under' in key or 'total' in key or 'goals' in key) and '0.5' in key and len(vals) >= 2:
            out['odds_over_05'], out['odds_under_05'] = safe_float(vals[0]), safe_float(vals[1])
        if ('over/under' in key or 'total' in key or 'goals' in key) and '1.5' in key and len(vals) >= 2:
            out['odds_over_15'], out['odds_under_15'] = safe_float(vals[0]), safe_float(vals[1])
        if ('over/under' in key or 'total' in key or 'goals' in key) and '2.5' in key and len(vals) >= 2:
            out['odds_over_25'], out['odds_under_25'] = safe_float(vals[0]), safe_float(vals[1])
        if ('btts' in key or 'both teams' in key) and len(vals) >= 2:
            out['odds_btts_yes'], out['odds_btts_no'] = safe_float(vals[0]), safe_float(vals[1])
    return out


def parse_events(payload: Any) -> dict[str, Any]:
    events = payload if isinstance(payload, list) else []
    home_minutes: list[int] = []
    away_minutes: list[int] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        etype = str(_first(event, ['type', 'incidentType', 'eventType']) or '').lower()
        if 'goal' not in etype:
            continue
        minute = safe_int(_first(event, ['minute', 'time', 'matchTime']))
        side = str(_first(event, ['side', 'teamSide', 'participant']) or '').lower()
        if minute is None:
            continue
        if side.startswith('h') or side == 'home':
            home_minutes.append(minute)
        elif side.startswith('a') or side == 'away':
            away_minutes.append(minute)
    return {'goal_minutes_home': home_minutes or None, 'goal_minutes_away': away_minutes or None}


def parse_structured_event(payload: dict[str, Any], league: dict[str, Any]) -> dict[str, Any] | None:
    home = _first(payload, ['home_team', 'home', 'homeName', 'homeParticipantName', 'homeTeamName'])
    away = _first(payload, ['away_team', 'away', 'awayName', 'awayParticipantName', 'awayTeamName'])
    if isinstance(home, dict):
        home = _first(home, ['name', 'shortName', 'participantName'])
    if isinstance(away, dict):
        away = _first(away, ['name', 'shortName', 'participantName'])
    if not home or not away:
        return None
    score = parse_score(_first(payload, ['score', 'result', 'ftScore']) or '')
    if not any(v is not None for v in score.values()) and isinstance(payload.get('score'), dict):
        sc = payload['score']
        score = {
            'goals_home_ft': safe_int(_first(sc, ['home', 'homeScore', 'home_score'])),
            'goals_away_ft': safe_int(_first(sc, ['away', 'awayScore', 'away_score'])),
            'goals_home_ht': safe_int(_first(sc, ['homeHT', 'home_ht', 'homeHalfTime'])),
            'goals_away_ht': safe_int(_first(sc, ['awayHT', 'away_ht', 'awayHalfTime'])),
        }
    odds = parse_odds_from_markets(_first(payload, ['markets', 'odds', 'bookmakers']) or {})
    stats = parse_stats_from_pairs(_first(payload, ['stats', 'statistics']) or {})
    events = parse_events(_first(payload, ['events', 'incidents']) or [])
    match_id = _first(payload, ['flashscore_match_id', 'id', 'eventId', 'event_id', 'matchId', 'match_id']) or extract_match_id(payload)
    raw_date = _first(payload, ['match_date', 'date', 'startTime', 'start_time'])
    kickoff = _first(payload, ['kickoff_time', 'time', 'startTimeTime']) or ''
    row = {
        'provider': 'flashscore', 'source': 'flashscore', 'is_demo_data': False,
        'flashscore_match_id': str(match_id or ''),
        'league': str(_first(payload, ['league', 'competitionName']) or league.get('league_name') or league.get('league_slug') or 'Unknown League'),
        'season': str(_first(payload, ['season']) or league.get('season') or datetime.now().year),
        'match_date': str(raw_date or datetime.now(timezone.utc).date().isoformat())[:10],
        'kickoff_time': str(kickoff)[:5] if re.match(r'^\d{2}:\d{2}', str(kickoff)) else str(kickoff),
        'home_team': str(home), 'away_team': str(away),
        'status': normalize_status(_first(payload, ['status', 'stage', 'matchStatus'])),
        **score, **odds, **stats, **events,
        'provider_warnings': str(payload.get('provider_warnings') or 'structured_flashscore_capture'),
        'data_quality_score': safe_float(payload.get('data_quality_score')) or 0.80,
    }
    return finalize_row(row, league)


def finalize_row(row: dict[str, Any], league: dict[str, Any] | None = None) -> dict[str, Any]:
    out = dict(row)
    out.setdefault('provider', 'flashscore')
    out.setdefault('source', 'flashscore')
    out.setdefault('is_demo_data', False)
    out.setdefault('league', str((league or {}).get('league_name') or (league or {}).get('league_slug') or 'Unknown League'))
    out.setdefault('season', str((league or {}).get('season') or datetime.now(timezone.utc).year))
    out.setdefault('match_date', datetime.now(timezone.utc).date().isoformat())
    out.setdefault('kickoff_time', '')
    out.setdefault('status', 'SCHEDULED')
    for col in MISSING_OPTIONAL_FIELDS:
        out.setdefault(col, None)
    mid = out.get('flashscore_match_id') or out.get('match_id') or extract_match_id(out)
    if not mid:
        base = f"{out.get('league')}|{out.get('match_date')}|{out.get('home_team')}|{out.get('away_team')}"
        mid = 'fallback_' + re.sub(r'[^a-z0-9]+', '_', base.lower()).strip('_')[:140]
        out['provider_warnings'] = append_warning(out.get('provider_warnings'), 'missing_flashscore_match_id;fallback_provider_match_id_generated')
        out['data_quality_score'] = min(float(out.get('data_quality_score') or 0.70), 0.64)
    out['flashscore_match_id'] = str(mid).replace('g_1_', '')
    out['provider_match_id'] = out['flashscore_match_id']
    out['match_id'] = out.get('match_id') or out['flashscore_match_id']
    missing = [c for c in ['odds_home','odds_over_25','corners_home','shots_home','xg_home'] if out.get(c) is None]
    if missing:
        out['provider_warnings'] = append_warning(out.get('provider_warnings'), 'optional_fields_missing:' + ','.join(missing))
    return out


def parse_text_rows(text: str, league: dict[str, Any], *, max_rows: int) -> list[dict[str, Any]]:
    lines = [l.strip() for l in str(text or '').splitlines() if l.strip()]
    rows: list[dict[str, Any]] = []
    current_date = datetime.now(timezone.utc).date().isoformat()
    i = 0
    while i < len(lines) - 2 and len(rows) < max_rows:
        date_m = _DATE_RE.search(lines[i])
        if date_m:
            d, mth, y = int(date_m.group('d')), int(date_m.group('m')), date_m.group('y')
            year = int(y) if y and len(y) == 4 else datetime.now(timezone.utc).year
            try:
                current_date = datetime(year, mth, d).date().isoformat()
            except ValueError:
                pass
        if _TIME_RE.match(lines[i]):
            home, away = lines[i + 1], lines[i + 2]
            if _team_like(home) and _team_like(away) and home.lower() != away.lower():
                match_id = extract_match_id(' '.join(lines[max(0, i - 3): i + 6]))
                row = {
                    'provider': 'flashscore', 'source': 'flashscore', 'is_demo_data': False,
                    'flashscore_match_id': match_id or '',
                    'league': str(league.get('league_name') or league.get('league_slug') or 'Unknown League'),
                    'season': str(league.get('season') or datetime.now().year),
                    'match_date': current_date, 'kickoff_time': lines[i],
                    'home_team': home, 'away_team': away, 'status': 'SCHEDULED',
                    'provider_warnings': 'real_flashscore_browser_scrape;text_parser;odds_stats_events_optional_if_unavailable',
                    'data_quality_score': 0.72,
                }
                row.update(parse_score(lines[i + 3] if i + 3 < len(lines) else ''))
                rows.append(finalize_row(row, league))
                i += 3
                continue
        i += 1
    return rows


def _team_like(value: str) -> bool:
    low = value.lower()
    banned = {'standings', 'draw', 'fixtures', 'results', 'loading', 'odds', 'betting', 'summary', 'advertisement', 'show more', 'table'}
    return len(value) >= 3 and not any(b in low for b in banned) and not _TIME_RE.match(value)


def parse_matches(raw_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    parsed = []
    for row in raw_rows:
        if not isinstance(row, dict):
            continue
        parsed.append(finalize_row(row, {'league_name': row.get('league'), 'season': row.get('season')}))
    return parsed
