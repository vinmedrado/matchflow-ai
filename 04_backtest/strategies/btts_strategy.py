from __future__ import annotations

from typing import Any, Dict, List


def get_strategies(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    markets = config.get("markets", {})
    strategies: List[Dict[str, Any]] = []
    yes = markets.get("btts_yes", {})
    if yes.get("enabled", True):
        strategies.append({
            "strategy": "btts_yes",
            "market": "btts",
            "selection": "yes",
            "line": None,
            "thresholds": yes.get("thresholds", {}),
            "odds_aliases": yes.get("odds_aliases", []),
        })
    no = markets.get("btts_no", {})
    if no.get("enabled", True):
        strategies.append({
            "strategy": "btts_no",
            "market": "btts",
            "selection": "no",
            "line": None,
            "thresholds": no.get("thresholds", {}),
            "odds_aliases": no.get("odds_aliases", []),
        })
    return strategies
