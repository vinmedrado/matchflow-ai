from __future__ import annotations

from typing import Any, Dict, List


def get_strategies(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    markets = config.get("markets", {})
    strategies: List[Dict[str, Any]] = []
    for name in ("corners_over_8_5", "corners_over_9_5"):
        item = markets.get(name, {})
        if item.get("enabled", True):
            strategies.append({
                "strategy": name,
                "market": "corners",
                "selection": "over",
                "line": float(item.get("line", 8.5)),
                "thresholds": item.get("thresholds", {}),
                "odds_aliases": item.get("odds_aliases", []),
            })
    return strategies
