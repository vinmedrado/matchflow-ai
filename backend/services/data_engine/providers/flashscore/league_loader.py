from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from .config import provider_root, get_flashscore_config
from .schemas import FlashScoreLeague


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"leagues": [], "warnings": [f"invalid_json:{path.name}:{exc}"]}


def load_leagues(country: str | None = None, season: str | None = None, max_leagues: int | None = None, test_mode: bool | None = None) -> dict[str, Any]:
    cfg = get_flashscore_config()
    base = provider_root() / "config" / "leagues"
    warnings: list[str] = []
    rows: list[dict[str, Any]] = []
    for path in sorted(base.glob("*.json")):
        payload = _read_json(path)
        warnings.extend(payload.get("warnings", [])) if isinstance(payload, dict) else None
        items = payload.get("leagues", []) if isinstance(payload, dict) else payload
        if not isinstance(items, list):
            warnings.append(f"invalid_leagues_payload:{path.name}")
            continue
        for raw in items:
            if not isinstance(raw, dict):
                continue
            item = FlashScoreLeague(
                league_slug=str(raw.get("league_slug") or raw.get("slug") or raw.get("name") or "unknown"),
                league_name=str(raw.get("league_name") or raw.get("name") or raw.get("league_slug") or "Unknown"),
                country=str(raw.get("country") or ""),
                season=str(raw.get("season") or "2023+"),
                enabled=bool(raw.get("enabled", True)),
                provider="flashscore",
                priority=int(raw.get("priority", 1)),
                canonical_league_id=raw.get("canonical_league_id"),
            ).__dict__
            if not item["enabled"]:
                continue
            if country and item["country"].lower() != country.lower():
                continue
            if season and str(item["season"]) != str(season):
                continue
            rows.append(item)
    limit = max_leagues if max_leagues is not None else cfg.max_leagues
    if test_mode is None:
        test_mode = cfg.test_mode
    if test_mode and limit:
        rows = rows[:limit]
    return {"ok": True, "total": len(rows), "leagues": rows, "warnings": warnings, "config": {"test_mode": test_mode, "max_leagues": limit}}
