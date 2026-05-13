from __future__ import annotations
from .base import AgentFinding, BaseAgent, num, severity

class PerformanceAgent(BaseAgent):
    name='performance_agent'
    role='model and signal performance intelligence'
    def findings(self,snapshot):
        out=[]
        summary=snapshot.get('summary') or {}
        avg_ev=num(summary.get('avg_ev_pct'),None)
        if avg_ev is not None and avg_ev<0:
            score=min(100,abs(avg_ev)*20+35)
            out.append(AgentFinding(self.name,'ev_performance',severity(score),score/100,'EV agregado negativo','O EV médio dos sinais disponíveis está abaixo de zero.',{'avg_ev_pct':avg_ev},'Revisar thresholds do decision engine e bloquear sinais abaixo de EV mínimo.'))
        models=(snapshot.get('analytics') or {}).get('model_trends') or []
        low=[m for m in models if num(m.get('value'),100)<55]
        if low:
            out.append(AgentFinding(self.name,'model_degradation','medium',0.64,'Modelo abaixo do patamar mínimo','Há métricas de modelo abaixo de 55 na registry.',{'models':low[:5]},'Rodar validação por mercado/liga antes de confiar nesses modelos.'))
        return out
