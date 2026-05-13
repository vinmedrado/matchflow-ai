from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from statistics import mean
from typing import Any

from backend.services.ai_brain import OperationalMemoryStore, build_ai_brain_snapshot
from .alert_agent import AlertAgent
from .anomaly_agent import AnomalyAgent
from .bankroll_agent import BankrollAgent
from .execution_agent import ExecutionAgent
from .market_agent import MarketAgent
from .performance_agent import PerformanceAgent
from .research_agent import ResearchAgent
from .risk_agent import RiskAgent
from .strategy_agent import StrategyAgent
from .base import num


class IntelligenceCoordinator:
    """Central multi-agent coordinator.

    Rules-only and auditable by design: agents do not mutate models or thresholds.
    They produce findings, then the coordinator builds consensus, conflicts, a decision
    and optimization proposals that require explicit review before execution.
    """

    version = '1.0.0-agentic'

    def __init__(self) -> None:
        self.agents = [
            RiskAgent(), StrategyAgent(), MarketAgent(), BankrollAgent(),
            AnomalyAgent(), PerformanceAgent(), ResearchAgent(), AlertAgent(), ExecutionAgent(),
        ]
        self.memory = OperationalMemoryStore()

    def run(self, task: str | None = None) -> dict[str, Any]:
        snapshot = build_ai_brain_snapshot()
        agent_outputs = [agent.analyze(snapshot) for agent in self.agents]
        findings = [f for out in agent_outputs for f in out.get('findings', [])]
        consensus = self._consensus(findings, snapshot)
        conflicts = self._conflicts(findings)
        decision = self._decision(consensus, conflicts, findings, snapshot)
        research = self._auto_research(snapshot, findings)
        optimization = self._self_optimization(snapshot, findings, decision)
        events = self._event_stream(agent_outputs, consensus, decision)
        diagnostics = self._diagnostics(agent_outputs, findings, conflicts)
        payload = {
            'ok': True,
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'coordinator_version': self.version,
            'task': task or 'continuous_operational_review',
            'data_state': snapshot.get('data_state', 'unavailable_data'),
            'brain_summary': snapshot.get('summary', {}),
            'agents': agent_outputs,
            'findings': findings,
            'consensus': consensus,
            'conflicts': conflicts,
            'decision': decision,
            'auto_research': research,
            'self_optimization': optimization,
            'event_stream': events,
            'observability': diagnostics,
            'source_meta': snapshot.get('source_meta', {}),
        }
        self.memory.append('agentic_cycle', {
            'task': payload['task'],
            'decision': decision,
            'consensus': consensus[:5],
            'data_state': payload['data_state'],
        })
        return payload

    def _consensus(self, findings: list[dict[str, Any]], snapshot: dict[str, Any]) -> list[dict[str, Any]]:
        if not findings:
            return [{'topic':'stable','severity':'info','agreement':1.0,'reasoning':'Nenhum agente encontrou risco crítico.', 'recommendation':'Manter monitoramento.'}]
        by_type: dict[str, list[dict[str, Any]]] = {}
        for f in findings:
            by_type.setdefault(str(f.get('type')), []).append(f)
        items = []
        for typ, group in by_type.items():
            avg_conf = mean([num(g.get('confidence'), 0.5) or 0.5 for g in group])
            sev_counts = Counter(g.get('severity','info') for g in group)
            severity = max(sev_counts, key=lambda s: {'info':1,'medium':2,'high':3,'critical':4}.get(s,0))
            items.append({
                'topic': typ,
                'agents': sorted({g.get('agent') for g in group}),
                'agreement': round(min(1.0, len(group) / max(1, len(self.agents) * 0.35)), 3),
                'confidence': round(avg_conf, 3),
                'severity': severity,
                'reasoning': ' | '.join([g.get('title','') for g in group[:3]]),
                'recommendation': group[0].get('recommendation'),
                'state': 'real_data' if snapshot.get('data_state') == 'real_data' else snapshot.get('data_state'),
            })
        return sorted(items, key=lambda x: ({'critical':4,'high':3,'medium':2,'info':1}.get(x['severity'],0), x['confidence'], x['agreement']), reverse=True)[:12]

    def _conflicts(self, findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
        conflicts=[]
        has_edge=any(f.get('type') in {'edge_candidate','research_hypothesis','combo_research'} for f in findings)
        has_guard=any(f.get('type') in {'execution_guardrail','drawdown','portfolio_risk'} and f.get('severity') in {'medium','high','critical'} for f in findings)
        if has_edge and has_guard:
            conflicts.append({
                'topic':'edge_vs_risk',
                'severity':'medium',
                'reasoning':'Agentes detectaram oportunidades, mas agentes de risco/execution recomendaram cautela.',
                'resolution':'Priorizar preservação de banca: pesquisar edge em modo paper antes de aumentar stake.',
            })
        return conflicts

    def _decision(self, consensus: list[dict[str, Any]], conflicts: list[dict[str, Any]], findings: list[dict[str, Any]], snapshot: dict[str, Any]) -> dict[str, Any]:
        high = [f for f in findings if f.get('severity') in {'high','critical'}]
        data_state = snapshot.get('data_state','unavailable_data')
        if data_state != 'real_data':
            action = 'HOLD_AND_COLLECT_DATA'
            confidence = 0.82
            reasoning = 'Dados insuficientes ou parciais; sistema não deve agir com métricas incompletas.'
        elif high:
            action = 'REDUCE_EXPOSURE_AND_REVIEW'
            confidence = min(0.95, 0.65 + len(high)*0.05)
            reasoning = f'{len(high)} achado(s) alto/crítico detectados pelos agentes.'
        elif conflicts:
            action = 'PAPER_VALIDATE_BEFORE_SCALE'
            confidence = 0.74
            reasoning = conflicts[0]['resolution']
        else:
            action = 'MAINTAIN_MONITORING'
            confidence = 0.61
            reasoning = 'Nenhum consenso crítico encontrado; manter operação em modo seguro.'
        return {
            'action': action,
            'confidence_score': round(confidence, 3),
            'reasoning': reasoning,
            'recommendation_summary': consensus[0].get('recommendation') if consensus else 'Monitorar.',
            'requires_human_review': action != 'MAINTAIN_MONITORING',
            'auditability': 'no automatic model mutation; proposals are advisory and persisted in operational memory',
            'state': data_state,
        }

    def _auto_research(self, snapshot: dict[str, Any], findings: list[dict[str, Any]]) -> dict[str, Any]:
        hypotheses=[]
        for f in findings:
            if f.get('agent') == 'research_agent':
                hypotheses.append({
                    'title': f.get('title'),
                    'hypothesis': f.get('reasoning'),
                    'validation_plan': 'Backtest segmentado por liga/mercado/odds range, checando robustez e risco de overfitting.',
                    'evidence': f.get('evidence'),
                    'state': f.get('state','real_data'),
                })
        if not hypotheses:
            hypotheses.append({'title':'Aguardar amostra maior','hypothesis':'Sem padrões robustos para pesquisa automática.', 'validation_plan':'Coletar mais sinais e resultados antes de testar combinações.', 'state': snapshot.get('data_state','no_data')})
        return {'state': snapshot.get('data_state','unavailable_data'), 'hypotheses': hypotheses[:8], 'overfitting_guardrails':['amostra mínima por bucket','validação temporal','comparação fora da amostra','sem promoção automática para live']}

    def _self_optimization(self, snapshot: dict[str, Any], findings: list[dict[str, Any]], decision: dict[str, Any]) -> dict[str, Any]:
        proposals=[]
        if decision['action'] == 'REDUCE_EXPOSURE_AND_REVIEW':
            proposals.append({'type':'risk_adjustment','proposal':'reduzir exposição/stake em 10% a 25% até alertas altos desaparecerem','requires_review':True})
        if any(f.get('type') == 'strategy_filter' for f in findings):
            proposals.append({'type':'threshold_adjustment','proposal':'aumentar confidence threshold apenas nos mercados negativos identificados','requires_review':True})
        if snapshot.get('data_state') != 'real_data':
            proposals.append({'type':'data_quality','proposal':'bloquear recomendações de escala enquanto estado for no_data/partial_data','requires_review':False})
        if not proposals:
            proposals.append({'type':'monitoring','proposal':'sem ajuste automático recomendado; manter baseline versionado','requires_review':False})
        return {'state': snapshot.get('data_state','unavailable_data'), 'mode':'advisory_auditable', 'proposals': proposals, 'versioning':'threshold/model changes must be reviewed and versioned outside this endpoint'}

    def _event_stream(self, agent_outputs: list[dict[str, Any]], consensus: list[dict[str, Any]], decision: dict[str, Any]) -> list[dict[str, Any]]:
        events=[]
        seq=1
        for out in agent_outputs:
            events.append({'seq':seq,'event_type':'agent_completed','agent':out['agent'],'summary':out['summary'],'state':out.get('state'),'ts':datetime.now(timezone.utc).isoformat()}); seq+=1
        for c in consensus[:5]:
            events.append({'seq':seq,'event_type':'consensus','topic':c['topic'],'severity':c['severity'],'summary':c['reasoning'],'ts':datetime.now(timezone.utc).isoformat()}); seq+=1
        events.append({'seq':seq,'event_type':'decision','action':decision['action'],'confidence':decision['confidence_score'],'summary':decision['reasoning'],'ts':datetime.now(timezone.utc).isoformat()})
        return events

    def _diagnostics(self, agent_outputs: list[dict[str, Any]], findings: list[dict[str, Any]], conflicts: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            'agents_executed': len(agent_outputs),
            'findings_total': len(findings),
            'conflicts_total': len(conflicts),
            'severity_distribution': dict(Counter(f.get('severity','info') for f in findings)),
            'state_distribution': dict(Counter(f.get('state','real_data') for f in findings)),
            'trace_mode': 'deterministic_rule_based_reasoning',
        }
