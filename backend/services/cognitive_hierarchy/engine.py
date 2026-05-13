from __future__ import annotations
from typing import Any


def _score(data: dict[str, Any], *keys: str, default: float = 0.0) -> float:
    cur: Any = data
    try:
        for key in keys:
            cur = cur.get(key) if isinstance(cur, dict) else None
        return float(cur if cur is not None else default)
    except Exception:
        return default


class CognitiveHierarchyEngine:
    version = "1.0.0-executive-hierarchy"

    def evaluate(self, cognitive: dict[str, Any]) -> dict[str, Any]:
        world = cognitive.get("world_model") or {}
        uncertainty = cognitive.get("uncertainty") or {}
        decision = cognitive.get("cognitive_decision") or {}
        meta = cognitive.get("meta_reasoning") or {}
        regime = world.get("regime", "diagnostic")
        uncertainty_score = _score(uncertainty, "uncertainty_score")
        reasoning_quality = _score(meta, "reasoning_quality_score")
        requires_review = bool(decision.get("requires_human_review"))
        layers = [
            {"id": "reactive", "name": "Reactive Cognition", "purpose": "Responder a eventos imediatos e alertas.", "active": True, "decision_scope": "alerts/live changes", "state": "watching"},
            {"id": "tactical", "name": "Tactical Cognition", "purpose": "Ajustar exposição, filtros e thresholds sugeridos.", "active": regime in {"defensive", "aggressive", "balanced"}, "decision_scope": "short-term controls", "state": "defensive" if regime == "defensive" else "adaptive"},
            {"id": "strategic", "name": "Strategic Cognition", "purpose": "Interpretar regimes, padrões e saúde de médio/longo prazo.", "active": True, "decision_scope": "regime and roadmap", "state": regime},
            {"id": "executive", "name": "Executive Cognition", "purpose": "Priorizar objetivos e controlar ações autônomas.", "active": True, "decision_scope": "system priorities", "state": "review" if requires_review else "supervising"},
            {"id": "meta", "name": "Meta-Cognition", "purpose": "Auditar reasoning, incerteza e overconfidence.", "active": uncertainty_score > 0.35 or reasoning_quality < 0.75, "decision_scope": "reasoning audit", "state": "guarding" if uncertainty_score > 0.5 else "validating"},
        ]
        if requires_review or uncertainty_score > 0.55:
            decision_layer = "meta"
            explanation = "Decisão escalada para Meta-Cognition por incerteza ou revisão humana."
        elif regime in {"defensive", "diagnostic"}:
            decision_layer = "executive"
            explanation = "Executive Cognition supervisiona postura defensiva/diagnóstica."
        elif regime == "aggressive":
            decision_layer = "strategic"
            explanation = "Strategic Cognition permite expansão seletiva, mas sob limites."
        else:
            decision_layer = "tactical"
            explanation = "Tactical Cognition mantém ajustes operacionais bounded."
        return {"ok": True, "engine_version": self.version, "decision_layer": decision_layer, "decision_layer_explanation": explanation, "layers": layers, "diagnostics": {"uncertainty_score": uncertainty_score, "reasoning_quality_score": reasoning_quality, "requires_review": requires_review, "regime": regime}}
