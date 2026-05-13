from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from .parser import parse_text_rows, parse_structured_event, extract_match_id, finalize_row
from .schemas import FlashScoreMatch
from .network_capture import build_capture_record, classify_response, is_relevant_response, try_load_payload, flatten_dicts


class FlashScoreClient:
    """Internal FlashScore client with real Playwright scraping first and explicit demo fallback only when enabled.

    The client avoids hard failing the MatchFlow pipeline when Playwright/browser/network is unavailable:
    it returns no real rows plus warnings. Demo rows are only emitted when DATA_ENGINE_MODE=demo or
    FLASHSCORE_USE_DEMO=true, so demo data never masquerades as real production data.
    """

    def __init__(self, *, headless: bool = True, sleep_seconds: float = 0.5, timeout_seconds: int = 30, use_demo: bool = False) -> None:
        self.headless = headless
        self.sleep_seconds = sleep_seconds
        self.timeout_seconds = timeout_seconds
        self.use_demo = use_demo
        self.warnings: list[str] = []
        self.network_samples: list[dict[str, Any]] = []
        self.capture_counts: dict[str, int] = {"fixtures": 0, "match_detail": 0, "odds": 0, "stats": 0, "events": 0, "standings": 0, "unknown": 0}
        self.failed_urls: list[str] = []

    def fetch_league_matches(self, league: dict[str, Any], *, test_mode: bool = True) -> list[dict[str, Any]]:
        if self.use_demo:
            return self._demo_rows(league, test_mode=test_mode)
        return self._fetch_with_playwright(league, test_mode=test_mode)

    def _fetch_with_playwright(self, league: dict[str, Any], *, test_mode: bool = True) -> list[dict[str, Any]]:
        if os.getenv('CI', '').lower() == 'true' and os.getenv('FLASHSCORE_ALLOW_CI_SCRAPING', 'false').lower() not in {'1', 'true', 'yes'}:
            self.warnings.append('ci_browser_scraping_disabled; no_demo_fallback_in_internal_mode')
            return []
        try:
            from playwright.sync_api import sync_playwright  # type: ignore
        except Exception as exc:
            self.warnings.append(f'playwright_unavailable:{type(exc).__name__}; no_demo_fallback_in_internal_mode')
            return []

        url = league.get('url') or self._build_fixtures_url(league)
        max_rows = 1 if test_mode else 80
        for attempt in range(1, 3):
            try:
                with sync_playwright() as pw:
                    browser = pw.chromium.launch(headless=self.headless)
                    context = browser.new_context(locale='en-US', timezone_id=os.getenv('FLASHSCORE_TIMEZONE', 'UTC'))
                    page = context.new_page()
                    page.set_default_timeout(self.timeout_seconds * 1000)
                    captured: list[dict[str, Any]] = []

                    def on_response(response):
                        try:
                            if not is_relevant_response(response.url, response.request.resource_type, response.status):
                                return
                            ctype = (response.headers or {}).get('content-type', '')
                            body = response.text()
                            if not body or len(body) > 350_000:
                                return
                            parsed_rows = self._parse_network_payload(body, league, max_rows=max_rows)
                            capture = build_capture_record(response.url, response.status, ctype, body, parsed_items_count=len(parsed_rows))
                            self.capture_counts[capture.response_type] = self.capture_counts.get(capture.response_type, 0) + 1
                            self.network_samples.append(capture.sanitized())
                            captured.extend(parsed_rows)
                        except Exception as exc:  # network capture is opportunistic
                            self.warnings.append(f'network_capture_warning:{type(exc).__name__}')

                    page.on('response', on_response)
                    page.goto(url, wait_until='domcontentloaded')
                    page.wait_for_load_state('networkidle', timeout=min(self.timeout_seconds * 1000, 12_000))
                    time.sleep(max(0.0, self.sleep_seconds))
                    rows = self._parse_dom_rows(page, league, max_rows=max_rows)
                    if not rows:
                        text = page.locator('body').inner_text(timeout=self.timeout_seconds * 1000)
                        rows = parse_text_rows(text, league, max_rows=max_rows)
                    browser.close()
                    merged = self._merge_rows(captured + rows, max_rows=max_rows)
                    if merged:
                        if captured:
                            self.warnings.append('flashscore_network_capture_used')
                        return merged
            except Exception as exc:
                self.failed_urls.append(str(url))
                self.warnings.append(f'flashscore_scrape_attempt_{attempt}_failed:{type(exc).__name__}; url={url}')
                time.sleep(min(2.0, max(0.2, self.sleep_seconds)) * attempt)
        self.warnings.append(f'flashscore_no_rows_parsed; url={url}; no_demo_fallback_in_internal_mode')
        return []

    def _build_fixtures_url(self, league: dict[str, Any]) -> str:
        country = str(league.get('country') or '').strip().lower().replace(' ', '-') or 'england'
        slug = str(league.get('league_slug') or league.get('league_name') or 'premier-league').strip().lower().replace(' ', '-')
        return f'https://www.flashscore.com/football/{country}/{slug}/fixtures/'

    def _parse_dom_rows(self, page: Any, league: dict[str, Any], *, max_rows: int) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        selectors = [
            '[id^="g_1_"]', '.event__match', '[class*="event__match"]', '[data-event-id]', '[data-testid*="match"]'
        ]
        for selector in selectors:
            try:
                loc = page.locator(selector)
                count = min(loc.count(), max_rows)
                for idx in range(count):
                    item = loc.nth(idx)
                    text = item.inner_text(timeout=1500)
                    attrs = self._element_attrs(item)
                    parsed = self._parse_event_text(text, league, attrs=attrs, index=len(rows)+1)
                    if parsed:
                        rows.append(parsed)
                if rows:
                    return rows[:max_rows]
            except Exception:
                continue
        return rows

    def _element_attrs(self, locator: Any) -> dict[str, Any]:
        attrs = {}
        for name in ['id', 'data-event-id', 'data-id', 'href']:
            try:
                value = locator.get_attribute(name, timeout=500)
                if value:
                    attrs[name] = value
            except Exception:
                pass
        return attrs

    def _parse_event_text(self, text: str, league: dict[str, Any], *, attrs: dict[str, Any], index: int) -> dict[str, Any] | None:
        lines = [x.strip() for x in str(text or '').splitlines() if x.strip()]
        if len(lines) < 3:
            return None
        time_re = re.compile(r'^(?:[01]?\d|2[0-3]):[0-5]\d$')
        time_value = next((x for x in lines if time_re.match(x)), '')
        teams = [x for x in lines if self._team_like(x)]
        if len(teams) < 2:
            return None
        score_line = next((x for x in lines if re.match(r'^\d+\s*[-:–]\s*\d+', x)), '')
        from .parser import parse_score, normalize_status
        match_id = extract_match_id(attrs, text) or attrs.get('id') or attrs.get('data-event-id') or f"flashscore_{league.get('league_slug','league')}_{index}"
        row = {
            'provider': 'flashscore', 'source': 'flashscore', 'is_demo_data': False,
            'flashscore_match_id': str(match_id).replace('g_1_', ''),
            'league': str(league.get('league_name') or league.get('league_slug') or 'Unknown League'),
            'season': str(league.get('season') or datetime.now(timezone.utc).year),
            'match_date': datetime.now(timezone.utc).date().isoformat(),
            'kickoff_time': time_value,
            'home_team': teams[0], 'away_team': teams[1],
            'status': normalize_status(next((x for x in lines if x.upper() in {'FT','HT','LIVE','POSTPONED'}), 'SCHEDULED')),
            'provider_warnings': 'real_flashscore_dom_scrape;odds_stats_events_optional_if_unavailable',
            'data_quality_score': 0.76,
        }
        row.update(parse_score(score_line))
        return finalize_row(row, league)

    def _parse_network_payload(self, body: str, league: dict[str, Any], *, max_rows: int) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        payload = try_load_payload(body)
        if payload is None:
            # Some FlashScore payloads are compact pseudo-json/plain text; extract conservative event fragments.
            for mid in re.finditer(r'(?P<id>[A-Za-z0-9]{8})[^\n]{0,100}(?P<home>[A-Z][^~|]{2,40})[~|][^~|]{0,60}[~|](?P<away>[A-Z][^~|]{2,40})', body):
                row = {
                    'provider': 'flashscore', 'source': 'flashscore', 'is_demo_data': False,
                    'flashscore_match_id': mid.group('id'),
                    'league': str(league.get('league_name') or league.get('league_slug') or 'Unknown League'),
                    'season': str(league.get('season') or datetime.now(timezone.utc).year),
                    'match_date': datetime.now(timezone.utc).date().isoformat(),
                    'kickoff_time': '', 'home_team': mid.group('home').strip(), 'away_team': mid.group('away').strip(),
                    'status': 'SCHEDULED', 'provider_warnings': 'real_flashscore_network_text_capture;structured_json_unavailable', 'data_quality_score': 0.74,
                }
                rows.append(finalize_row(row, league))
                if len(rows) >= max_rows:
                    return rows
            return rows

        for event in self._walk_events(payload):
            row = parse_structured_event(event, league)
            if row:
                response_type = classify_response('', event, json.dumps(event, default=str)[:800])
                row['provider_warnings'] = f'real_flashscore_network_capture;structured_payload;response_type={response_type}'
                rows.append(finalize_row(row, league))
                if len(rows) >= max_rows:
                    break
        return rows

    def _walk_events(self, obj: Any) -> list[dict[str, Any]]:
        found: list[dict[str, Any]] = []
        for item in flatten_dicts(obj):
            keys = {str(k).lower() for k in item.keys()}
            has_team_pair = ({'home', 'away'} <= keys or {'homename', 'awayname'} <= keys or {'home_team','away_team'} <= keys or {'homeparticipantname','awayparticipantname'} <= keys)
            has_event_marker = bool(keys & {'id','eventid','event_id','matchid','match_id','score','starttime','date','markets','odds','stats','statistics','events','incidents'})
            if has_team_pair and has_event_marker:
                found.append(item)
        return found

    def _merge_rows(self, rows: list[dict[str, Any]], *, max_rows: int) -> list[dict[str, Any]]:
        merged: dict[str, dict[str, Any]] = {}
        for row in rows:
            if not row:
                continue
            mid = str(row.get('flashscore_match_id') or row.get('match_id') or f"{row.get('home_team')}::{row.get('away_team')}::{row.get('match_date')}")
            if mid not in merged:
                merged[mid] = row
            else:
                for k, v in row.items():
                    if merged[mid].get(k) in {None, '', 'nan'} and v not in {None, ''}:
                        merged[mid][k] = v
        return list(merged.values())[:max_rows]

    def _team_like(self, value: str) -> bool:
        low = str(value or '').lower()
        banned = {'standings', 'draw', 'fixtures', 'results', 'loading', 'odds', 'betting', 'summary', 'advertisement', 'show more', 'table'}
        return len(str(value or '')) >= 3 and not any(b in low for b in banned) and not re.match(r'^(?:[01]?\d|2[0-3]):[0-5]\d$', str(value))

    def _demo_rows(self, league: dict[str, Any], *, test_mode: bool) -> list[dict[str, Any]]:
        base = datetime.now(timezone.utc).date() + timedelta(days=1)
        name = league.get('league_name', 'Unknown League')
        slug = league.get('league_slug', 'league')
        sample = {
            'premier': [('Man Utd', 'Manchester City'), ('Arsenal', 'Chelsea')],
            'brasile': [('São Paulo FC', 'Palmeiras'), ('Atlético-MG', 'Flamengo')],
            'liga': [('Barcelona', 'Valencia'), ('Real Madrid', 'Real Sociedad')],
            'serie': [('Inter Milan', 'Roma'), ('Juventus', 'Napoli')],
        }
        key = next((k for k in sample if k in f'{slug} {name}'.lower()), 'premier')
        rows = []
        for idx, (home, away) in enumerate(sample[key][:1 if test_mode else 2], start=1):
            rows.append(FlashScoreMatch(
                flashscore_match_id=f'flashscore_demo_{slug}_{idx}', provider='flashscore', source='demo', is_demo_data=True,
                league=name, season=str(league.get('season') or base.year), match_date=str(base + timedelta(days=idx)),
                kickoff_time=f'{18+idx:02d}:00', home_team=home, away_team=away, status='SCHEDULED',
                odds_home=1.80 + idx / 10, odds_draw=3.25, odds_away=3.80 - idx / 10, odds_over_25=1.86,
                odds_under_25=1.94, odds_btts_yes=1.78, odds_btts_no=1.96,
                provider_warnings='demo fallback explicitly enabled', data_quality_score=0.62,
            ).to_dict())
        return rows
