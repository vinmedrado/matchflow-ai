from __future__ import annotations
from .base import AgentFinding, BaseAgent, num, severity, trend

class MarketAgent(BaseAgent):
    name='market_agent'
    role='market regime, odds drift and CLV intelligence'
    def findings(self,snapshot):
        out=[]
        markets=(snapshot.get('analytics') or {}).get('market_performance') or []
        for m in markets[:8]:
            tr=m.get('trend') or {}
            if tr.get('available') and num(tr.get('delta'),0)<-0.01:
                score=min(100,abs(num(tr.get('delta'),0))*1800)
                out.append(AgentFinding(self.name,'market_degradation',severity(score),score/100,f"Degradação em {m.get('name')}",f"EV recente caiu contra a metade anterior da amostra.",{'market':m,'trend':tr},'Reduzir exposição nesse mercado até estabilizar.'))
        if not out and markets:
            out.append(AgentFinding(self.name,'market_regime','info',0.58,'Regime de mercado monitorado','Sem drift crítico inferido pelos dados disponíveis.',{'markets_checked':len(markets)},'Manter coleta de odds/CLV para aumentar robustez.'))
        return out
