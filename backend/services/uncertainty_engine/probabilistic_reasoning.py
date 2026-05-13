from __future__ import annotations
from typing import Any

class ProbabilisticReasoningEngine:
    version='1.0.0-uncertainty'
    def evaluate(self, snapshot: dict[str, Any], world_model: dict[str, Any]) -> dict[str, Any]:
        data_state=snapshot.get('data_state')
        summary=snapshot.get('summary') or {}
        sample=int(summary.get('signals_count') or summary.get('total_signals') or 0)
        alert_count=len(snapshot.get('alerts') or [])
        base=0.18 if data_state=='real_data' else 0.62
        sample_penalty=0.22 if sample < 30 else 0.1 if sample < 100 else 0.0
        alert_penalty=min(0.24, alert_count*0.035)
        uncertainty=min(0.95, base+sample_penalty+alert_penalty)
        distribution=[{'bucket':'low','probability':round(max(0,1-uncertainty)*0.45,3)},{'bucket':'medium','probability':round(0.35,3)},{'bucket':'high','probability':round(uncertainty*0.65,3)}]
        scenarios=[
            {'name':'base_case','probability':round(max(0.1,1-uncertainty),3),'expected_state':world_model.get('regime')},
            {'name':'stress_case','probability':round(min(0.8, uncertainty),3),'expected_state':'defensive'},
            {'name':'recovery_case','probability':round(max(0.05, .45-uncertainty/3),3),'expected_state':'balanced'},
        ]
        return {'ok':True,'version':self.version,'uncertainty_score':round(uncertainty,3),'ambiguity_level':'high' if uncertainty>.65 else 'medium' if uncertainty>.38 else 'low','confidence_distribution':distribution,'probabilistic_scenarios':scenarios,'robustness_score':round(1-uncertainty,3),'explanation':'Incerteza aumenta com dados ausentes, amostra pequena e pressão de alertas.'}
