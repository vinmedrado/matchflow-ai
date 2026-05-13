from __future__ import annotations

from typing import Any, Dict, List


def get_strategies(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    markets = config.get("markets", {})
    strategies: List[Dict[str, Any]] = []
    for name in ("goals_over_2_5", "goals_over_1_5"):
        item = markets.get(name, {})
        if item.get("enabled", True):
            strategies.append({
                "strategy": name,
                "market": "goals",
                "selection": "over",
                "line": float(item.get("line", 2.5)),
                "thresholds": item.get("thresholds", {}),
                "odds_aliases": item.get("odds_aliases", []),
            })
    return strategies
