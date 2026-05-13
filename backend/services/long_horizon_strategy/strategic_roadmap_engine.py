from __future__ import annotations
from typing import Any


class StrategicRoadmapEngine:
    horizons = ["intraday", "7_days", "30_days", "90_days", "season"]

    def build(self, cognitive: dict[str, Any], hierarchy: dict[str, Any]) -> dict[str, Any]:
        world = cognitive.get("world_model") or {}
        decision = cognitive.get("cognitive_decision") or {}
        uncertainty = cognitive.get("uncertainty") or {}
        regime = world.get("regime", "diagnostic")
        u = float(uncertainty.get("uncertainty_score") or 0)
        defensive = regime in {"defensive", "diagnostic"} or u > 0.55 or decision.get("requires_human_review")
        posture = "capital_preservation" if defensive else "selective_growth"
        roadmap = []
        for h in self.horizons:
            if h == "intraday":
                actions = ["bloquear ações críticas sem approval", "monitorar alertas de risco", "atualizar world model"]
            elif h == "7_days":
                actions = ["comparar performance por mercado/liga", "revisar drawdown e EV", "executar reflections semanais leves"]
            elif h == "30_days":
                actions = ["validar robustez de estratégias", "avaliar degradação gradual", "priorizar estabilidade do bankroll"]
            elif h == "90_days":
                actions = ["medir regimes recorrentes", "consolidar knowledge evolution", "revisar metas conflitantes"]
            else:
                actions = ["comparar temporada por mercado", "avaliar sobrevivência de edge", "planejar melhoria de dados/modelos"]
            roadmap.append({"horizon": h, "posture": posture, "objective": "reduzir risco e preservar bankroll" if defensive else "capturar EV com controle de volatilidade", "actions": actions, "risk": "high" if defensive and h in {"intraday", "7_days"} else "moderate", "success_criteria": ["sem aumento de drawdown não aprovado", "decisões rastreáveis", "melhora ou estabilidade de robustez"]})
        return {"ok": True, "engine_version": "1.0.0-long-horizon", "posture": posture, "exploration_vs_protection": "protection_first" if defensive else "balanced_selective_exploration", "roadmap": roadmap, "tradeoffs": ["EV capture vs bankroll preservation", "exploration vs robustness", "speed vs governance"], "decision_layer": hierarchy.get("decision_layer")}
