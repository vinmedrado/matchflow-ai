from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.services.goal_engine import ObjectiveManager, StrategyPlanner

WORKFLOW_MAP = {
    'protect_bankroll': 'bankroll_protection_workflow',
    'detect_degradation': 'model_degradation_workflow',
    'reduce_exposure': 'exposure_reduction_workflow',
    'maximize_ev_quality': 'strategy_recalibration_workflow',
    'improve_robustness': 'drift_investigation_workflow',
    'reduce_volatility': 'market_instability_workflow',
}

class AutonomousWorkflowEngine:
    version = '1.0.0-workflows'

    def evaluate(self, snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
        goals = ObjectiveManager().evaluate(snapshot)
        plan = StrategyPlanner().build_plan(snapshot)
        workflows=[]
        for obj in goals['active_objectives']:
            name = WORKFLOW_MAP.get(obj['id'], 'anomaly_investigation_workflow')
            steps = [t for t in plan['plan']['tasks'] if t['objective_id'] == obj['id']]
            workflows.append({
                'id': f"wf_{obj['id']}",
                'name': name,
                'objective_id': obj['id'],
                'status': 'ready_for_review' if obj['status'] == 'needs_action' else 'waiting_for_data',
                'priority': obj['priority'],
                'severity': obj['severity'],
                'steps': steps,
                'autonomous_actions': [
                    {'action': 'collect_context', 'safe_to_execute': True},
                    {'action': 'generate_diagnostic_report', 'safe_to_execute': True},
                    {'action': 'propose_recalibration', 'safe_to_execute': False},
                ],
                'audit': {
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'mutation_policy': 'read-only/advisory; no automatic model or stake mutation',
                    'requires_human_approval': True,
                },
                'state': obj['state'],
            })
        return {
            'ok': True,
            'workflow_version': self.version,
            'data_state': goals['data_state'],
            'workflows': workflows,
            'summary': {'total': len(workflows), 'ready': len([w for w in workflows if w['status']=='ready_for_review'])},
        }
