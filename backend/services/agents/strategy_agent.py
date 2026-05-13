from __future__ import annotations
from typing import Any
from .base import AgentFinding, BaseAgent, num

class StrategyAgent(BaseAgent):
    name = 'strategy_agent'
    role = 'strategy consistency and edge selection'

    def findings(self, snapshot: dict[str, Any]) -> list[AgentFinding]:
        out=[]
        markets=(snapshot.get('analytics') or {}).get('market_performance') or []
        positive=[m for m in markets if num(m.get('avg_ev_pct'),0)>0 and m.get('signals',0)>=2]
        negative=[m for m in markets if num(m.get('avg_ev_pct'),0)<0 and m.get('signals',0)>=2]
        if positive:
            best=positive[0]
            out.append(AgentFinding(self.name,'edge_candidate','info',0.72,'Mercado com edge operacional',f"{best.get('name')} lidera por EV médio na janela atual.",{'market':best},'Priorizar validação desse mercado, mantendo limite de stake por amostra.'))
        if negative:
            worst=sorted(negative,key=lambda x:num(x.get('avg_ev_pct'),0))[0]
            out.append(AgentFinding(self.name,'strategy_filter','medium',0.69,'Mercado exige filtro temporário',f"{worst.get('name')} está negativo na janela atual.",{'market':worst},'Exigir threshold/confidence maior ou pausar mercado até nova amostra.'))
        return out
