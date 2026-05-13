from __future__ import annotations
from typing import Any


class SystemSelfModel:
    def build(self, cognitive: dict[str, Any], governance: dict[str, Any], experiments: dict[str, Any]) -> dict[str, Any]:
        obs = cognitive.get("observability") or {}
        uncertainty = float((cognitive.get("uncertainty") or {}).get("uncertainty_score") or 0)
        reasoning = float((cognitive.get("meta_reasoning") or {}).get("reasoning_quality_score") or 0)
        health = max(0.0, min(1.0, (reasoning * 0.55) + ((1 - uncertainty) * 0.35) + (0.1 if not governance.get("safe_mode") else 0)))
        weak: list[str] = []
        if uncertainty > 0.5:
            weak.append("uncertainty high; reduce autonomy and request stronger evidence")
        if reasoning < 0.7:
            weak.append("reasoning robustness below enterprise target")
        if governance.get("safe_mode"):
            weak.append("governance safe mode active")
        if experiments.get("summary", {}).get("inconclusive", 0):
            weak.append("experiments inconclusive; avoid strategy promotion")
        return {"ok": True, "engine_version": "1.0.0-cognitive-digital-twin", "cognitive_health_score": round(health, 3), "capabilities": ["structured reasoning", "agent coordination", "goal planning", "governance blocking", "reflection cycles", "shadow experimentation"], "limitations": weak or ["no critical limitation detected in current deterministic cycle"], "component_health": {"world_model": obs.get("world_model_regime", "unknown"), "reasoning": reasoning, "uncertainty": uncertainty, "governance_safe_mode": governance.get("safe_mode"), "experimentation": experiments.get("summary")}, "answers": {"onde_estou_fraco": weak[0] if weak else "não há fraqueza crítica nesta rodada", "motor_instavel": "governance/uncertainty" if governance.get("safe_mode") else "none", "decisao_baixa_robustez": "requires review" if uncertainty > 0.5 or reasoning < 0.7 else "none"}, "forecast": "stable_guarded" if health >= 0.65 else "needs_review"}
