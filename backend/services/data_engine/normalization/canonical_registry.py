from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from .text_normalizer import canonical_slug, normalize_text

DEFAULT_TEAMS = {
    'manchester_united': {'canonical_name': 'Manchester United', 'country': 'England', 'aliases': ['man utd','man united','manchester united fc']},
    'manchester_city': {'canonical_name': 'Manchester City', 'country': 'England', 'aliases': ['man city','manchester city fc']},
    'internazionale': {'canonical_name': 'Internazionale', 'country': 'Italy', 'aliases': ['inter milan','internazionale milano']},
    'inter_miami': {'canonical_name': 'Inter Miami', 'country': 'USA', 'aliases': ['inter miami cf']},
    'sao_paulo': {'canonical_name': 'São Paulo', 'country': 'Brazil', 'aliases': ['sao paulo fc','são paulo fc']},
    'atletico_mineiro': {'canonical_name': 'Atlético Mineiro', 'country': 'Brazil', 'aliases': ['atletico-mg','atlético-mg','atl mineiro']},
    'paris_saint_germain': {'canonical_name': 'Paris Saint-Germain', 'country': 'France', 'aliases': ['psg','paris sg']},
}
DEFAULT_LEAGUES = {
    'premier_league': {'canonical_name': 'Premier League', 'country': 'England', 'aliases': ['epl','english premier league']},
    'la_liga': {'canonical_name': 'La Liga', 'country': 'Spain', 'aliases': ['primera division','laliga']},
    'brasileiro_serie_a': {'canonical_name': 'Brasileiro Serie A', 'country': 'Brazil', 'aliases': ['brasileirao serie a','campeonato brasileiro serie a']},
    'serie_a': {'canonical_name': 'Serie A', 'country': 'Italy', 'aliases': ['italian serie a']},
    'bundesliga': {'canonical_name': 'Bundesliga', 'country': 'Germany', 'aliases': ['german bundesliga']},
    'ligue_1': {'canonical_name': 'Ligue 1', 'country': 'France', 'aliases': ['france ligue 1']},
}

class CanonicalRegistry:
    def __init__(self, root: Path | None = None):
        self.root = Path(root) if root else Path(__file__).resolve().parents[4]
        self.storage = self.root / 'backend/services/data_engine/storage'
        self.storage.mkdir(parents=True, exist_ok=True)
        self.team_path = self.storage / 'canonical_teams.json'
        self.league_path = self.storage / 'canonical_leagues.json'
        self.team_alias_path = self.storage / 'provider_team_aliases.json'
        self.league_alias_path = self.storage / 'provider_league_aliases.json'
        self.match_links_path = self.storage / 'provider_match_links.json'
        self.teams = self._load_or_seed(self.team_path, DEFAULT_TEAMS, 'team')
        self.leagues = self._load_or_seed(self.league_path, DEFAULT_LEAGUES, 'league')
        self.team_aliases = self._load_json(self.team_alias_path, {})
        self.league_aliases = self._load_json(self.league_alias_path, {})
        self.match_links = self._load_json(self.match_links_path, {})

    def _load_json(self, path: Path, default: Any) -> Any:
        try:
            return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default
        except Exception:
            return default

    def _load_or_seed(self, path: Path, defaults: dict, entity_type: str) -> dict:
        if path.exists():
            return self._load_json(path, {})
        now = datetime.now(timezone.utc).isoformat()
        payload = {}
        for cid, meta in defaults.items():
            aliases = sorted(set(meta.get('aliases', []) + [meta.get('canonical_name', cid)]))
            payload[cid] = {
                f'canonical_{entity_type}_id': cid,
                'canonical_id': cid,
                'canonical_name': meta.get('canonical_name', cid.replace('_',' ').title()),
                'country': meta.get('country'),
                'aliases': aliases,
                'provider_ids': {},
                'provider_names': {},
                'first_seen_at': now,
                'last_seen_at': now,
                'review_status': 'seeded',
                'confidence': 1.0,
                'notes': 'Seeded canonical registry entry.',
            }
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
        return payload

    def save(self) -> None:
        for path, data in [(self.team_path,self.teams),(self.league_path,self.leagues),(self.team_alias_path,self.team_aliases),(self.league_alias_path,self.league_aliases),(self.match_links_path,self.match_links)]:
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')

    def alias_lookup(self, raw_name: str, entity_type: str, provider: str | None = None) -> str | None:
        aliases = self.team_aliases if entity_type == 'team' else self.league_aliases
        key = f'{provider or "any"}:{normalize_text(raw_name, entity_type=entity_type)}'
        if key in aliases:
            return aliases[key]
        generic = f'any:{normalize_text(raw_name, entity_type=entity_type)}'
        return aliases.get(generic)

    def provider_id_lookup(self, provider: str, provider_id: str, entity_type: str) -> str | None:
        data = self.teams if entity_type == 'team' else self.leagues
        for cid, meta in data.items():
            if str(meta.get('provider_ids', {}).get(provider, '')) == str(provider_id):
                return cid
        return None

    def candidates(self, entity_type: str) -> dict:
        return self.teams if entity_type == 'team' else self.leagues

    def ensure_entity(self, raw_name: str, entity_type: str, provider: str = 'unknown', provider_id: str | None = None, confidence: float = 0.65) -> str:
        data = self.teams if entity_type == 'team' else self.leagues
        cid = canonical_slug(raw_name, entity_type=entity_type)
        now = datetime.now(timezone.utc).isoformat()
        if cid not in data:
            data[cid] = {
                f'canonical_{entity_type}_id': cid, 'canonical_id': cid,
                'canonical_name': str(raw_name).strip() or cid.replace('_',' ').title(),
                'country': None, 'aliases': [str(raw_name).strip()], 'provider_ids': {}, 'provider_names': {},
                'first_seen_at': now, 'last_seen_at': now, 'review_status': 'auto_created',
                'confidence': confidence, 'notes': 'Created by entity resolution fallback.'
            }
        data[cid]['last_seen_at'] = now
        data[cid].setdefault('provider_names', {}).setdefault(provider, [])
        if raw_name and raw_name not in data[cid]['provider_names'][provider]:
            data[cid]['provider_names'][provider].append(str(raw_name))
        if provider_id:
            data[cid].setdefault('provider_ids', {})[provider] = str(provider_id)
        alias_store = self.team_aliases if entity_type == 'team' else self.league_aliases
        alias_store[f'{provider}:{normalize_text(raw_name, entity_type=entity_type)}'] = cid
        alias_store[f'any:{normalize_text(raw_name, entity_type=entity_type)}'] = cid
        self.save()
        return cid
