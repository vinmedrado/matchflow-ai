from __future__ import annotations
from .base import AgentFinding, BaseAgent, num

class AlertAgent(BaseAgent):
    name='alert_agent'
    role='alert prioritization and escalation'
    def findings(self,snapshot):
        out=[]
        for a in (snapshot.get('alerts') or [])[:8]:
            out.append(AgentFinding(self.name,'alert_escalation',a.get('severity','info'),num(a.get('priority'),25)/100,a.get('title','Alerta'),a.get('reason',''),{'alert':a},a.get('recommendation','Monitorar alerta.'),a.get('state','real_data')))
        return out
