from __future__ import annotations
from .base import AgentFinding, BaseAgent, num, severity

class AnomalyAgent(BaseAgent):
    name='anomaly_agent'
    role='statistical anomaly and inconsistent behavior detection'
    def findings(self,snapshot):
        out=[]
        analytics=snapshot.get('analytics') or {}
        for group_name in ['league_performance','market_performance']:
            rows=analytics.get(group_name) or []
            vals=[num(r.get('avg_ev_pct'),None) for r in rows]
            vals=[v for v in vals if v is not None]
            if len(vals)>=4:
                avg=sum(vals)/len(vals)
                spread=max(vals)-min(vals)
                if spread>=8:
                    score=min(100,spread*8)
                    out.append(AgentFinding(self.name,'dispersion_anomaly',severity(score),score/100,f'Dispersão anormal em {group_name}',f'Spread de EV entre buckets chegou a {spread:.2f} p.p.',{'bucket':group_name,'avg':round(avg,2),'spread':round(spread,2)},'Investigar buckets extremos antes de consolidar estratégia agregada.'))
        return out
