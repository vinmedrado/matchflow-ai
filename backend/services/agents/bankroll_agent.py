from __future__ import annotations
from .base import AgentFinding, BaseAgent, num, severity

class BankrollAgent(BaseAgent):
    name='bankroll_agent'
    role='bankroll, staking and capital preservation'
    def findings(self,snapshot):
        out=[]
        for a in snapshot.get('alerts') or []:
            if a.get('type')=='BANKROLL':
                out.append(AgentFinding(self.name,'drawdown',a.get('severity','high'),num(a.get('priority'),70)/100,a.get('title','Drawdown detectado'),a.get('reason',''),{'alert':a},a.get('recommendation','Ativar modo conservador.'),a.get('state','real_data')))
        summary=snapshot.get('summary') or {}
        alerts=num(summary.get('alerts'),0) or 0
        if alerts>=3:
            out.append(AgentFinding(self.name,'stake_control','medium',0.66,'Concentração de alertas aumenta risco de staking','O AI Brain reportou múltiplos alertas simultâneos.',{'alerts':alerts},'Aplicar cap de stake e evitar aumentar exposição enquanto houver alertas ativos.'))
        return out
