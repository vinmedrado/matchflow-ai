from __future__ import annotations
from typing import Any

class StrategyOptimizer:
    def evaluate(self, executive: dict[str, Any]) -> dict[str, Any]:
        roadmap = executive.get("long_horizon_strategy") or {}
        defensive = sum(1 for r in roadmap.get("roadmap", []) if r.get("posture") in {"defensive", "conservative"})
        return {"strategy_stability_score": round(0.82 - min(defensive, 3)*0.07, 3), "recommended_posture": roadmap.get("posture", "balanced"), "optimization": "protect_bankroll_before_expanding_exposure" if defensive else "maintain_balanced_ev_risk"}
