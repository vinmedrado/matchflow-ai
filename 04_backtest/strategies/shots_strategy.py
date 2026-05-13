from __future__ import annotations

from typing import Any, Dict, List


def get_strategies(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    item = config.get("markets", {}).get("shots_over_threshold", {})
    if not item.get("enabled", True):
        return []
    return [{
        "strategy": "shots_over_threshold",
        "market": "shots",
        "selection": "over",
        "line": float(item.get("line", 10.5)),
        "thresholds": item.get("thresholds", {}),
        "odds_aliases": item.get("odds_aliases", []),
    }]
