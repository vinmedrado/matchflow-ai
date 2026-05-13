from __future__ import annotations

from typing import Any

from .objective_manager import ObjectiveManager

class StrategyPlanner:
    version = '1.0.0-planning'

    def build_plan(self, snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
        evaluation = ObjectiveManager().evaluate(snapshot)
        objectives = evaluation['active_objectives'][:6]
        tasks = []
        dependencies = []
        seq = 1
        for obj in objectives:
            oid = obj['id']
            if oid == 'protect_bankroll':
                steps = ['diagnose_drawdown_sources','reduce_stake_profile','monitor_equity_recovery']
            elif oid == 'maximize_ev_quality':
                steps = ['segment_ev_by_market','raise_min_ev_filter_proposal','paper_validate_filtered_set']
            elif oid == 'reduce_exposure':
                steps = ['map_market_league_concentration','cap_correlated_exposure','review_after_next_cycle']
            elif oid == 'detect_degradation':
                steps = ['open_drift_investigation','compare_recent_vs_baseline','prepare_threshold_review']
            elif oid == 'improve_robustness':
                steps = ['run_segmented_backtest','check_overfitting_risk','promote_only_robust_edges']
            else:
                steps = ['collect_required_metrics','run_agentic_review','create_human_review_note']
            previous = None
            for step in steps:
                tid = f'T{seq:03d}'
                tasks.append({
                    'id': tid,
                    'objective_id': oid,
                    'title': step.replace('_',' ').title(),
                    'status': 'planned',
                    'priority': obj['priority'],
                    'owner': obj['owner'],
                    'requires_human_review': step in {'prepare_threshold_review','raise_min_ev_filter_proposal','reduce_stake_profile'},
                    'reasoning': obj['reasoning'],
                    'state': obj['state'],
                })
                if previous:
                    dependencies.append({'from': previous, 'to': tid, 'type': 'blocks'})
                previous = tid
                seq += 1
        return {
            'ok': True,
            'planner_version': self.version,
            'data_state': evaluation['data_state'],
            'objective_summary': evaluation['summary'],
            'plan': {
                'mode': 'advisory_auditable',
                'tasks_total': len(tasks),
                'tasks': tasks,
                'dependency_graph': dependencies,
                'decision_tree': self._decision_tree(evaluation),
            },
        }

    def _decision_tree(self, evaluation: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            {'if': 'data_state != real_data', 'then': 'hold_scaling_and_collect_data'},
            {'if': 'protect_bankroll priority >= high', 'then': 'activate_defensive_workflow'},
            {'if': 'degradation_score high', 'then': 'open_model_degradation_workflow'},
            {'if': 'ev_quality on_track and risk low', 'then': 'maintain_monitoring_or_paper_validate_edges'},
        ]
