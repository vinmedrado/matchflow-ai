from __future__ import annotations
from typing import Any

class CognitionOptimizer:
    def evaluate(self, executive: dict[str, Any]) -> dict[str, Any]:
        obs = executive.get("executive_observability") or {}
        reasoning = float(obs.get("reasoning_robustness_score") or 0.0)
        quality = float(obs.get("decision_quality_score") or 0.0)
        uncertainty = float(obs.get("uncertainty_score") or 0.5)
        bottlenecks = []
        if reasoning < 0.65: bottlenecks.append("reasoning_quality_below_target")
        if quality < 0.65: bottlenecks.append("decision_quality_below_target")
        if uncertainty > 0.45: bottlenecks.append("uncertainty_pressure_high")
        score = round(max(0.0, min(1.0, (reasoning + quality + (1-uncertainty)) / 3)), 3)
        return {"recursive_improvement_score": score, "bottlenecks": bottlenecks, "improvement_plan": self._plan(bottlenecks), "safe_to_apply_automatically": False, "audit_note": "Engine only proposes bounded improvements; it never changes code or primary models automatically."}
    def _plan(self, bottlenecks: list[str]) -> list[dict[str, str]]:
        if not bottlenecks:
            return [{"area":"cognitive_pipeline", "action":"maintain_current_controls", "reason":"quality and uncertainty are within guardrails"}]
        mapping = {"reasoning_quality_below_target":"increase meta-reasoning review before executive decisions", "decision_quality_below_target":"route critical decisions to executive board and governance", "uncertainty_pressure_high":"lower autonomy level and require more evidence"}
        return [{"area": b, "action": mapping.get(b, "review"), "reason": "recursive feedback detected improvement opportunity"} for b in bottlenecks]
