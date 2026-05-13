from __future__ import annotations

from statistics import mean, pstdev
from typing import Any

from backend.services.ai_brain import build_ai_brain_snapshot
from backend.services.agents.base import num, severity
from .operational_objectives import DEFAULT_OBJECTIVES


def _drawdown_from_snapshot(snapshot: dict[str, Any]) -> float | None:
    # equity curve may exist in source-backed premium paper data; never synthesize it.
    paper = (snapshot.get('source_meta') or {}).get('paper_trading') or {}
    if paper.get('state') in {'no_data','unavailable_data'}:
        return None
    return None


def _metric_context(snapshot: dict[str, Any]) -> dict[str, Any]:
    summary = snapshot.get('summary') or {}
    analytics = snapshot.get('analytics') or {}
    alerts = snapshot.get('alerts') or []
    evs = []
    for bucket in (analytics.get('market_performance') or []) + (analytics.get('league_performance') or []):
        ev = num(bucket.get('avg_ev_pct'), None)
        if ev is not None:
            evs.append(ev)
    risk_alerts = [a for a in alerts if a.get('type') in {'RISK','EXPOSURE','BANKROLL'}]
    degradation_alerts = [a for a in alerts if a.get('type') in {'DEGRADATION','LEAGUE'}]
    return {
        'avg_ev_pct': summary.get('avg_ev_pct'),
        'avg_score': summary.get('avg_score'),
        'roi_volatility': round(pstdev(evs), 3) if len(evs) > 1 else None,
        'exposure_score': max([num(a.get('priority'), 0) or 0 for a in risk_alerts], default=None),
        'degradation_score': max([num(a.get('priority'), 0) or 0 for a in degradation_alerts], default=None),
        'volatility_score': round(pstdev(evs) * 5, 3) if len(evs) > 1 else None,
        'robustness_score': round(min(100, (summary.get('signals') or 0) * 2), 3) if snapshot.get('data_state') == 'real_data' else None,
        'drawdown_pct': _drawdown_from_snapshot(snapshot),
    }


class ObjectiveManager:
    version = '1.0.0-goal-driven'

    def evaluate(self, snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
        snapshot = snapshot or build_ai_brain_snapshot()
        metrics = _metric_context(snapshot)
        objectives = []
        for obj in DEFAULT_OBJECTIVES:
            value = metrics.get(obj.target_metric)
            state = snapshot.get('data_state', 'unavailable_data')
            if value is None:
                progress = None
                status = 'unavailable_data'
                priority = 40 if state != 'real_data' else 25
                reasoning = f'Métrica {obj.target_metric} indisponível; objetivo fica em monitoramento sem ação automática.'
            else:
                val = float(value)
                if obj.desired_direction == 'up':
                    gap = obj.baseline_threshold - val
                    progress = max(0, min(100, (val / obj.baseline_threshold) * 100)) if obj.baseline_threshold else 100
                    needs_action = gap > 0
                    priority = min(100, max(10, gap * 2)) if needs_action else 15
                elif obj.desired_direction == 'up_to_zero':
                    gap = abs(min(0, val - obj.baseline_threshold)) if val < obj.baseline_threshold else 0
                    progress = 100 if val >= obj.baseline_threshold else max(0, 100 - gap * 8)
                    needs_action = val < obj.baseline_threshold
                    priority = min(100, 60 + gap * 5) if needs_action else 20
                else:
                    gap = val - obj.baseline_threshold
                    progress = max(0, min(100, 100 - max(0, gap) * 3))
                    needs_action = gap > 0
                    priority = min(100, max(10, gap * 3)) if needs_action else 15
                status = 'needs_action' if needs_action else 'on_track'
                reasoning = f'{obj.target_metric}={val}; limite={obj.baseline_threshold}; status={status}.'
            objectives.append({
                **obj.__dict__,
                'current_value': value,
                'progress_pct': None if progress is None else round(float(progress), 2),
                'status': status,
                'priority': round(float(priority), 2),
                'severity': severity(float(priority)),
                'reasoning': reasoning,
                'state': state if status != 'unavailable_data' else 'unavailable_data',
            })
        active = sorted(objectives, key=lambda x: x['priority'], reverse=True)
        return {
            'ok': True,
            'engine_version': self.version,
            'data_state': snapshot.get('data_state', 'unavailable_data'),
            'objectives': active,
            'active_objectives': [o for o in active if o['status'] in {'needs_action','unavailable_data'}],
            'metrics': metrics,
            'summary': {
                'total': len(objectives),
                'needs_action': len([o for o in objectives if o['status'] == 'needs_action']),
                'on_track': len([o for o in objectives if o['status'] == 'on_track']),
                'unavailable': len([o for o in objectives if o['status'] == 'unavailable_data']),
            },
        }
