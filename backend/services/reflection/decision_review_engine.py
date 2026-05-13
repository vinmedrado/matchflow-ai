from __future__ import annotations
from datetime import datetime, timezone
from typing import Any


class DecisionReviewEngine:
    cycles = ["daily", "weekly", "after_drawdown", "after_model_degradation", "after_strategy_failure", "after_anomaly_cluster"]

    def run(self, cognitive: dict[str, Any], goal_evolution: dict[str, Any]) -> dict[str, Any]:
        decision = cognitive.get("cognitive_decision") or {}
        uncertainty = cognitive.get("uncertainty") or {}
        knowledge = cognitive.get("knowledge_evolution") or {}
        reflections = []
        for cycle in self.cycles:
            evidence = "partial" if cognitive.get("data_state") != "real_data" else "operational"
            learning = "manter decisão em modo advisory até evidência suficiente"
            if cycle == "daily":
                learning = "revisar alertas, exposição e qualidade do reasoning antes de qualquer execução"
            if cycle == "weekly":
                learning = "comparar tendências e validar se objetivos ainda fazem sentido"
            if cycle == "after_drawdown":
                learning = "priorizar proteção de bankroll e investigar ligas/mercados problemáticos"
            reflections.append({"cycle": cycle, "status": "ready", "evidence_level": evidence, "decision_reviewed": decision.get("action"), "uncertainty_score": uncertainty.get("uncertainty_score"), "learning": learning, "feeds_memory_graph": True})
        return {"ok": True, "engine_version": "1.0.0-reflection", "generated_at": datetime.now(timezone.utc).isoformat(), "reflections": reflections, "summary": {"total": len(reflections), "low_evidence": len([r for r in reflections if r["evidence_level"] == "partial"]), "knowledge_patterns_used": len(knowledge.get("patterns") or [])}, "feedback_targets": ["memory_graph", "knowledge_evolution", "goal_evolution"]}
