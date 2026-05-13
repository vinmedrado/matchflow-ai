from __future__ import annotations

from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class OperationalObjective:
    id: str
    title: str
    intent: str
    target_metric: str
    desired_direction: str
    baseline_threshold: float
    guardrail: str
    owner: str

DEFAULT_OBJECTIVES = [
    OperationalObjective('protect_bankroll','Proteger bankroll','reduzir drawdown e preservar capital','drawdown_pct','up_to_zero',-5.0,'não aumentar exposição durante queda relevante','bankroll_agent'),
    OperationalObjective('stabilize_roi','Estabilizar ROI','reduzir volatilidade de retorno','roi_volatility','down',12.0,'não mascarar baixa amostra com ROI isolado','performance_agent'),
    OperationalObjective('maximize_ev_quality','Maximizar qualidade do EV','priorizar sinais com EV consistente','avg_ev_pct','up',1.0,'não escalar quando EV agregado for negativo','strategy_agent'),
    OperationalObjective('reduce_exposure','Reduzir exposição excessiva','evitar concentração por mercado/liga','exposure_score','down',55.0,'limitar mercados correlacionados','risk_agent'),
    OperationalObjective('detect_degradation','Detectar degradação','identificar queda de modelo/mercado','degradation_score','down',35.0,'abrir investigação antes de recalibrar','anomaly_agent'),
    OperationalObjective('improve_confidence','Melhorar confiança','elevar qualidade dos sinais aprovados','avg_score','up',60.0,'exigir amostra real para aumentar threshold','execution_agent'),
    OperationalObjective('reduce_volatility','Reduzir volatilidade','suavizar variação operacional','volatility_score','down',35.0,'preferir modo defensivo em regime instável','risk_agent'),
    OperationalObjective('improve_robustness','Melhorar robustez','validar edges contra overfitting','robustness_score','up',65.0,'usar paper/backtest segmentado antes de escala','research_agent'),
]

def list_objectives() -> list[dict[str, Any]]:
    return [o.__dict__ for o in DEFAULT_OBJECTIVES]
