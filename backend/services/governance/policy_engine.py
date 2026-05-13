from __future__ import annotations
from typing import Any


class PolicyEngine:
    critical_actions = {"ALTER_PRIMARY_MODEL", "INCREASE_EXPOSURE", "AGGRESSIVE_MODE", "AUTO_EXECUTE_BET", "PROMOTE_STRATEGY"}

    def evaluate(self, proposed_actions: list[dict[str, Any]], cognitive: dict[str, Any]) -> dict[str, Any]:
        blocks: list[dict[str, Any]] = []
        approvals: list[dict[str, Any]] = []
        allowed: list[dict[str, Any]] = []
        uncertainty = float((cognitive.get("uncertainty") or {}).get("uncertainty_score") or 0)
        for action in proposed_actions:
            name = str(action.get("action") or action.get("id") or "UNKNOWN")
            critical = name in self.critical_actions or "AGGRESSIVE" in name or "INCREASE" in name or "HUMAN_REVIEW" in name
            if critical:
                blocks.append({"action": name, "reason": "Ação crítica exige aprovação humana e trilha de auditoria.", "policy": "human_approval_required"})
            elif uncertainty > 0.6 and ("RECALIBRATE" in name or "EXPAND" in name):
                blocks.append({"action": name, "reason": "Incerteza elevada bloqueia recalibração/expansão.", "policy": "uncertainty_guardrail"})
            elif "RECALIBRATE" in name or "THRESHOLD" in name:
                approvals.append({"action": name, "reason": "Permitido apenas como proposta versionada, sem execução cega.", "policy": "reviewed_recalibration"})
            else:
                allowed.append({"action": name, "reason": "Ação diagnóstica/advisory permitida.", "policy": "advisory_allowed"})
        safe_mode = bool(blocks) or uncertainty > 0.7
        return {"ok": True, "engine_version": "1.0.0-governance", "safe_mode": safe_mode, "blocks": blocks, "approvals_required": approvals, "allowed_actions": allowed, "governance_block_count": len(blocks), "risk_limits": {"max_exposure_increase_without_approval": 0, "model_change_requires_approval": True, "aggressive_mode_requires_low_uncertainty": True}, "auditability": "every block includes policy, reason and action id"}
