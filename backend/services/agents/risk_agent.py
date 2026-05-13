from __future__ import annotations
from statistics import mean
from typing import Any
from .base import AgentFinding, BaseAgent, num, severity

class RiskAgent(BaseAgent):
    name = 'risk_agent'
    role = 'risk, exposure and drawdown intelligence'

    def findings(self, snapshot: dict[str, Any]) -> list[AgentFinding]:
        out: list[AgentFinding] = []
        alerts = snapshot.get('alerts') or []
        risk_alerts = [a for a in alerts if a.get('type') in {'RISK','EXPOSURE','BANKROLL'}]
        for a in risk_alerts[:5]:
            out.append(AgentFinding(self.name, 'risk_alert', a.get('severity','medium'), num(a.get('priority'),50)/100, a.get('title','Risco detectado'), a.get('reason',''), {'alert': a}, a.get('recommendation','Reduzir exposição até nova validação.'), a.get('state','real_data')))
        risks = []
        for item in (snapshot.get('analytics') or {}).get('league_performance') or []:
            ev = num(item.get('avg_ev_pct'), None)
            if ev is not None and ev < 0 and item.get('signals',0) >= 3:
                risks.append(abs(ev))
        if risks:
            score = min(100, mean(risks) * 12)
            out.append(AgentFinding(self.name,'portfolio_risk',severity(score),score/100,'Risco distribuído por ligas negativas',f'{len(risks)} ligas com EV médio negativo e amostra mínima.',{'negative_leagues':len(risks),'risk_score':round(score,2)},'Diminuir peso das ligas negativas e exigir score maior temporariamente.'))
        return out
