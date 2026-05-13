from __future__ import annotations
from typing import Any


class GoalLifecycleManager:
    def evolve(self, cognitive: dict[str, Any], hierarchy: dict[str, Any], roadmap: dict[str, Any]) -> dict[str, Any]:
        uncertainty = cognitive.get("uncertainty") or {}
        decision = cognitive.get("cognitive_decision") or {}
        world = cognitive.get("world_model") or {}
        u = float(uncertainty.get("uncertainty_score") or 0)
        mutations = []
        if world.get("regime") in {"defensive", "diagnostic"} or decision.get("requires_human_review"):
            mutations.append({"goal_id": "protect_bankroll", "mutation": "promote_priority", "reason": "Regime defensivo/diagnóstico ou revisão humana exigida.", "new_priority": 95})
            mutations.append({"goal_id": "maximize_ev", "mutation": "demote_priority", "reason": "Maximização de EV não deve superar proteção em contexto fraco.", "new_priority": 45})
        if u > 0.55:
            mutations.append({"goal_id": "reduce_uncertainty", "mutation": "create_or_promote", "reason": "Incerteza elevada reduz confiabilidade de decisões autônomas.", "new_priority": 90})
        if not mutations:
            mutations.append({"goal_id": "maintain_adaptive_monitoring", "mutation": "keep", "reason": "Objetivos alinhados ao regime atual.", "new_priority": 60})
        conflicts = []
        if any(m["goal_id"] == "maximize_ev" for m in mutations) and any(m["goal_id"] == "protect_bankroll" for m in mutations):
            conflicts.append({"between": ["maximize_ev", "protect_bankroll"], "resolution": "protect_bankroll wins under executive governance"})
        return {"ok": True, "engine_version": "1.0.0-goal-evolution", "mutations": mutations, "conflicts": conflicts, "lifecycle_policy": "objectives are mutated as proposals only; no blind execution", "alignment_score": 0.88 if mutations else 0.72, "roadmap_posture": roadmap.get("posture")}
