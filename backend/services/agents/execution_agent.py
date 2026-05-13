from __future__ import annotations
from .base import AgentFinding, BaseAgent

class ExecutionAgent(BaseAgent):
    name='execution_agent'
    role='safe execution guardrails for paper/live operations'
    def findings(self,snapshot):
        state=snapshot.get('data_state','unavailable_data')
        alerts=snapshot.get('alerts') or []
        if state!='real_data':
            return [AgentFinding(self.name,'execution_guardrail','medium',0.8,'Execução bloqueada por dados insuficientes','A camada autônoma não deve agir quando o estado não é real_data.',{'data_state':state},'Manter apenas simulação/paper até dados operacionais completos.','partial_data')]
        high=[a for a in alerts if a.get('severity') in {'high','critical'}]
        if high:
            return [AgentFinding(self.name,'execution_guardrail','high',0.82,'Modo conservador recomendado','Alertas altos/críticos impedem aumento automático de exposição.',{'high_alerts':len(high)},'Reduzir stake e exigir validação manual para sinais novos.')]
        return [AgentFinding(self.name,'execution_readiness','info',0.55,'Execução em modo seguro','Sem alerta crítico, mas o sistema permanece paper/simulação por segurança.',{'mode':'paper'},'Manter execução automática desabilitada até governança live ser habilitada.')] 
