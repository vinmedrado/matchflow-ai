from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from backend.services.ai_brain import build_ai_brain_snapshot
from backend.services.agents import IntelligenceCoordinator
from backend.services.autonomous_workflows import AutonomousWorkflowEngine
from backend.services.goal_engine import ObjectiveManager, StrategyPlanner, AdaptiveGoalRouter, GoalPriorityEngine
from backend.services.memory_graph import MemoryGraphEngine
from backend.services.simulation_engine import SimulationEngine
from backend.services.llm_orchestration import LLMRouter

router = APIRouter(prefix='/api/autonomous', tags=['goal-driven-autonomous-ai'])

class AutonomousAskRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=1000)


def _build_operating_system() -> dict[str, Any]:
    snapshot = build_ai_brain_snapshot()
    goals = ObjectiveManager().evaluate(snapshot)
    prioritized = GoalPriorityEngine().reprioritize(goals['objectives'])
    routes = AdaptiveGoalRouter().route(prioritized)
    plan = StrategyPlanner().build_plan(snapshot)
    workflows = AutonomousWorkflowEngine().evaluate(snapshot)
    agent_cycle = IntelligenceCoordinator().run('goal_driven_operating_cycle')
    graph = MemoryGraphEngine().build(snapshot, agent_cycle)
    simulations = SimulationEngine().run(snapshot)
    decision = _autonomous_decision(snapshot, goals, plan, workflows, agent_cycle, simulations)
    return {
        'ok': True,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'system_version': '1.0.0-goal-driven-autonomous-os',
        'data_state': snapshot.get('data_state'),
        'brain_summary': snapshot.get('summary'),
        'goals': goals,
        'goal_routes': routes,
        'planning': plan,
        'workflows': workflows,
        'agent_coordination': agent_cycle,
        'memory_graph': graph,
        'simulations': simulations,
        'autonomous_decision': decision,
        'observability': _observability(goals, plan, workflows, graph, agent_cycle),
    }


def _autonomous_decision(snapshot: dict[str, Any], goals: dict[str, Any], plan: dict[str, Any], workflows: dict[str, Any], agent_cycle: dict[str, Any], simulations: dict[str, Any]) -> dict[str, Any]:
    active = goals.get('active_objectives') or []
    critical = [o for o in active if o.get('severity') in {'critical','high'}]
    ready = [w for w in workflows.get('workflows', []) if w.get('status') == 'ready_for_review']
    agent_decision = agent_cycle.get('decision') or {}
    if snapshot.get('data_state') != 'real_data':
        action = 'COLLECT_DATA_BEFORE_AUTONOMY'
        confidence = 0.86
        reasoning = 'Estado de dados não é real_data; autonomia fica limitada a diagnóstico e coleta.'
    elif critical:
        action = 'ENTER_DEFENSIVE_GOAL_MODE'
        confidence = min(0.96, 0.7 + len(critical)*0.04)
        reasoning = f'{len(critical)} objetivo(s) críticos/altos exigem postura defensiva e workflows auditáveis.'
    elif ready:
        action = 'EXECUTE_ADVISORY_WORKFLOWS'
        confidence = 0.72
        reasoning = f'{len(ready)} workflow(s) prontos para revisão; executar coleta/diagnóstico sem mutação automática.'
    else:
        action = 'MAINTAIN_ADAPTIVE_MONITORING'
        confidence = 0.64
        reasoning = 'Objetivos principais em estado aceitável; manter monitoramento e simulação de cenários.'
    return {
        'action': action,
        'confidence_score': round(confidence, 3),
        'reasoning': reasoning,
        'recommended_execution': [w['id'] for w in ready[:5]],
        'agentic_action': agent_decision.get('action'),
        'plan_tasks': plan.get('plan', {}).get('tasks_total'),
        'simulation_preferred_regime': _preferred_regime(simulations),
        'requires_human_review': action != 'MAINTAIN_ADAPTIVE_MONITORING',
        'auditability': 'autonomous OS is advisory/read-only by default; recalibration proposals require review/versioning',
        'state': snapshot.get('data_state'),
    }


def _preferred_regime(simulations: dict[str, Any]) -> str | None:
    scenarios = [s for s in simulations.get('scenarios', []) if s.get('state') == 'real_data']
    if not scenarios:
        return None
    return sorted(scenarios, key=lambda s: (s.get('risk_score') or 999, -(s.get('projected_ev_pct') or 0)))[0].get('name')


def _observability(goals: dict[str, Any], plan: dict[str, Any], workflows: dict[str, Any], graph: dict[str, Any], agent_cycle: dict[str, Any]) -> dict[str, Any]:
    return {
        'trace_mode': 'deterministic_structured_reasoning',
        'goals_total': goals.get('summary', {}).get('total'),
        'active_goals': len(goals.get('active_objectives') or []),
        'plan_tasks': plan.get('plan', {}).get('tasks_total'),
        'workflows_total': workflows.get('summary', {}).get('total'),
        'memory_nodes': graph.get('summary', {}).get('nodes'),
        'memory_edges': graph.get('summary', {}).get('edges'),
        'agents_executed': agent_cycle.get('observability', {}).get('agents_executed'),
        'reasoning_latency_class': 'local_rule_based_fast',
        'loop_guard': 'single-cycle execution; no recursive autonomous loop',
    }

@router.get('/workspace')
def autonomous_workspace() -> dict[str, Any]:
    return _build_operating_system()

@router.get('/goals')
def goals() -> dict[str, Any]:
    snapshot = build_ai_brain_snapshot()
    evaluation = ObjectiveManager().evaluate(snapshot)
    prioritized = GoalPriorityEngine().reprioritize(evaluation['objectives'])
    return {**evaluation, 'objectives': prioritized, 'routes': AdaptiveGoalRouter().route(prioritized)}

@router.get('/planning')
def planning() -> dict[str, Any]:
    return StrategyPlanner().build_plan()

@router.get('/workflows')
def workflows() -> dict[str, Any]:
    return AutonomousWorkflowEngine().evaluate()

@router.get('/memory-graph')
def memory_graph() -> dict[str, Any]:
    return MemoryGraphEngine().build()

@router.get('/simulations')
def simulations() -> dict[str, Any]:
    return SimulationEngine().run()

@router.get('/decision')
def decision() -> dict[str, Any]:
    os = _build_operating_system()
    return {'ok': True, 'generated_at': os['generated_at'], 'data_state': os['data_state'], 'autonomous_decision': os['autonomous_decision'], 'observability': os['observability']}

@router.post('/ask')
def autonomous_ask(payload: AutonomousAskRequest) -> dict[str, Any]:
    os = _build_operating_system()
    route = LLMRouter().route(payload.question, os)
    answer_parts = [f"Pipeline: {route['pipeline']}."]
    q = payload.question.lower()
    if 'objetivo' in q or 'goal' in q:
        top = (os['goals'].get('active_objectives') or os['goals'].get('objectives') or [])[:3]
        answer_parts.append('Objetivos prioritários: ' + '; '.join([f"{o['title']} ({o['status']}, prioridade {o['priority']})" for o in top]))
    elif 'workflow' in q or 'plano' in q:
        answer_parts.append(f"Plano atual tem {os['planning']['plan']['tasks_total']} tarefas e {os['workflows']['summary']['total']} workflows auditáveis.")
    elif 'simula' in q or 'cenário' in q or 'cenario' in q:
        scenarios = os['simulations'].get('scenarios', [])[:3]
        answer_parts.append('Cenários: ' + '; '.join([f"{s.get('name')} risk={s.get('risk_score')} ev={s.get('projected_ev_pct')}" for s in scenarios]))
    else:
        d = os['autonomous_decision']
        answer_parts.append(f"Decisão autônoma: {d['action']} — {d['reasoning']}")
    return {'ok': True, 'mode': 'goal_driven_structured_reasoning', 'router': route, 'answer': '\n'.join(answer_parts), 'context': os}



@router.get("/status")
def status() -> dict[str, Any]:
    os = _build_operating_system()
    return {
        "ok": True,
        "endpoint": "/api/autonomous/status",
        "canonical_endpoint": "/api/autonomous/workspace",
        "generated_at": os.get("generated_at"),
        "system_version": os.get("system_version"),
        "data_state": os.get("data_state"),
        "decision": os.get("autonomous_decision"),
        "observability": os.get("observability"),
    }

@router.websocket('/stream')
async def autonomous_stream(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            os = _build_operating_system()
            await ws.send_text(json.dumps({
                'ok': True,
                'type': 'autonomous_os_tick',
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'decision': os['autonomous_decision'],
                'active_goals': (os['goals'].get('active_objectives') or [])[:5],
                'workflows': (os['workflows'].get('workflows') or [])[:5],
                'observability': os['observability'],
            }, default=str))
            await asyncio.sleep(7)
    except WebSocketDisconnect:
        return
