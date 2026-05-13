from __future__ import annotations
from typing import Any


class ExperimentRunner:
    def run(self, cognitive: dict[str, Any], roadmap: dict[str, Any]) -> dict[str, Any]:
        data_state = cognitive.get("data_state")
        experiments = [
            {"id": "exp_confidence_filter_defensive", "hypothesis": "Aumentar filtro de confidence em regime defensivo reduz drawdown sem zerar EV.", "data_used": data_state, "success_criteria": ["drawdown menor", "EV não negativo", "amostra mínima válida"], "risk": "medium", "robustness": "pending" if data_state != "real_data" else "monitoring", "status": "inconclusive" if data_state != "real_data" else "ready_for_backtest", "recommendation": "não promover sem backtest e aprovação"},
            {"id": "exp_reduce_low_liquidity_leagues", "hypothesis": "Reduzir peso de ligas inconsistentes melhora estabilidade da curva.", "data_used": data_state, "success_criteria": ["ROI estável", "menor volatilidade", "CLV não deteriorado"], "risk": "low", "robustness": "pending", "status": "designed", "recommendation": "executar como shadow experiment"},
            {"id": "exp_ev_vs_bankroll_tradeoff", "hypothesis": "Em incerteza alta, preservar bankroll supera maximização de EV bruto.", "data_used": data_state, "success_criteria": ["menor max drawdown", "streaks negativas menores"], "risk": "low", "robustness": "conceptual", "status": "designed", "recommendation": "usar simulação antes de qualquer alteração real"},
        ]
        success_rate = 0.0 if not [e for e in experiments if e["status"] == "promoted"] else 1.0
        return {"ok": True, "engine_version": "1.0.0-experimentation", "experiments": experiments, "summary": {"total": len(experiments), "ready": len([e for e in experiments if "ready" in e["status"]]), "inconclusive": len([e for e in experiments if e["status"] == "inconclusive"]), "experiment_success_rate": success_rate}, "guardrail": "experiments are advisory/shadow by default"}
