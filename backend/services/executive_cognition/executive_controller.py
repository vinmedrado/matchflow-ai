from __future__ import annotations
from typing import Any


class ExecutiveController:
    def decide(self, cognitive: dict[str, Any], hierarchy: dict[str, Any], roadmap: dict[str, Any], goal_evolution: dict[str, Any], governance: dict[str, Any], digital_twin: dict[str, Any]) -> dict[str, Any]:
        decision = cognitive.get("cognitive_decision") or {}
        health = float(digital_twin.get("cognitive_health_score") or 0)
        blocks = int(governance.get("governance_block_count") or 0)
        if governance.get("safe_mode") or health < 0.55:
            action = "EXECUTIVE_SAFE_MODE"
            control_mode = "wait_and_review"
        elif goal_evolution.get("conflicts"):
            action = "EXECUTIVE_RESOLVE_GOAL_CONFLICTS"
            control_mode = "review_before_action"
        elif roadmap.get("posture") == "capital_preservation":
            action = "EXECUTIVE_CAPITAL_PRESERVATION"
            control_mode = "act_conservatively"
        else:
            action = "EXECUTIVE_BALANCED_AUTONOMY"
            control_mode = "act_with_guardrails"
        quality = round(max(0, min(1, health * 0.5 + float(decision.get("confidence_score") or 0) * 0.3 + (1 - min(blocks, 5) / 5) * 0.2)), 3)
        return {"ok": True, "engine_version": "1.0.0-executive-cognition", "executive_action": action, "control_mode": control_mode, "decision_quality_score": quality, "decision_layer": hierarchy.get("decision_layer"), "reasoning": f"{action}: health={health}, governance_blocks={blocks}, posture={roadmap.get('posture')}", "supervision_scope": ["agents", "goals", "workflows", "world_model", "governance", "experiments"], "autonomous_action_policy": "advisory/read-only unless governance approves and human review is not required"}
