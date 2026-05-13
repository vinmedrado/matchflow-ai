from __future__ import annotations
from typing import Any

class LearningStrategyEngine:
    def analyze(self, executive: dict[str, Any], recursive: dict[str, Any]) -> dict[str, Any]:
        experiments = ((executive.get("experimentation") or {}).get("experiments") or [])
        inconclusive = sum(1 for e in experiments if e.get("status") == "inconclusive")
        total = len(experiments)
        efficiency = 1 - (inconclusive / total) if total else 0.5
        if (recursive.get("cognition") or {}).get("bottlenecks"):
            efficiency *= 0.9
        return {"learning_efficiency_score": round(efficiency, 3), "learning_strategy": "evidence_first_incremental_adaptation", "detected_learning_patterns": ["experiments_require_robustness_before_promotion", "uncertainty_reduces_autonomy"], "over_adaptation_risk": inconclusive > total/2 if total else False}
