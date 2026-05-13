"""
league_mapper.py — Mapeamento canônico entre todas as fontes de dados.

Delega para o serviço interno em:
  backend/services/data_engine/normalization/canonical_registry.py

Fontes suportadas:
  flashscore_slug   : "england/premier-league"
  flashscore_name   : "England Premier League"
  football_data_code: "PL"
  odds_api_key      : "soccer_epl"
  canonical         : "Premier League"
"""
from __future__ import annotations
import json
import logging
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger("matchflow.data_ops.league_mapper")

_ROOT = Path(__file__).resolve().parents[1]
_MAP_FILE = _ROOT / "config/league_source_map.json"

# Tentar usar o serviço interno primeiro
def _internal_registry():
    try:
        sys.path.insert(0, str(_ROOT / "backend/services/data_engine/normalization"))
        from canonical_registry import CanonicalRegistry
        return CanonicalRegistry(_ROOT)
    except Exception:
        return None


@lru_cache(maxsize=1)
def _load_static_map() -> list[dict]:
    if not _MAP_FILE.exists():
        return []
    try:
        return json.loads(_MAP_FILE.read_text(encoding="utf-8")).get("leagues", [])
    except Exception:
        return []


def _norm(s: str) -> str:
    return str(s).lower().strip().replace("-", " ").replace("/", " ")


def get_canonical_name(source: str, value: str) -> str:
    """
    Resolve qualquer identificador para o nome canônico.

    Exemplos:
      get_canonical_name('flashscore_name', 'England Premier League') → 'Premier League'
      get_canonical_name('football_data_code', 'PL')                  → 'Premier League'
      get_canonical_name('odds_api_key', 'soccer_epl')                → 'Premier League'
    """
    val_norm = _norm(value)
    key_map = {
        "flashscore_name":      lambda l: any(_norm(v) == val_norm for v in l.get("flashscore_name_variants", [])),
        "flashscore_slug":      lambda l: _norm(l.get("flashscore_slug", "")) == val_norm,
        "football_data_code":   lambda l: l.get("football_data_code", "").upper() == value.upper(),
        "odds_api_key":         lambda l: l.get("odds_api_key", "").lower() == value.lower(),
    }
    fn = key_map.get(source)
    if fn is None:
        return value
    for league in _load_static_map():
        if fn(league):
            return league.get("canonical", value)
    return value


def get_football_data_code(flashscore_name_or_slug: str) -> str | None:
    """Ex: 'Brazil Serie A' → 'BSA'"""
    val_norm = _norm(flashscore_name_or_slug)
    for league in _load_static_map():
        variants = [_norm(v) for v in league.get("flashscore_name_variants", [])]
        slug = _norm(league.get("flashscore_slug", ""))
        if val_norm in variants or val_norm == slug:
            return league.get("football_data_code")
    return None


def get_odds_api_key(flashscore_name_or_slug: str) -> str | None:
    """Ex: 'England Premier League' → 'soccer_epl'"""
    val_norm = _norm(flashscore_name_or_slug)
    for league in _load_static_map():
        variants = [_norm(v) for v in league.get("flashscore_name_variants", [])]
        slug = _norm(league.get("flashscore_slug", ""))
        if val_norm in variants or val_norm == slug:
            return league.get("odds_api_key")
    return None


def all_league_slugs() -> list[str]:
    """Retorna todos os slugs mapeados."""
    return [l.get("flashscore_slug", "") for l in _load_static_map() if l.get("flashscore_slug")]


if __name__ == "__main__":
    print("=== League Mapper ===")
    tests = [
        ("flashscore_name",   "England Premier League", "Premier League"),
        ("football_data_code","PL",                     "Premier League"),
        ("odds_api_key",      "soccer_epl",             "Premier League"),
        ("flashscore_name",   "Brazil Serie A",         "Brasileirão Série A"),
    ]
    for src, val, exp in tests:
        res = get_canonical_name(src, val)
        print(f"  {'✅' if res==exp else '❌'} {src}({val!r}) → {res!r}")
