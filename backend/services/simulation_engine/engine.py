from __future__ import annotations

from statistics import mean, pstdev
from typing import Any

from backend.services.ai_brain import build_ai_brain_snapshot
from backend.services.agents.base import num

class SimulationEngine:
    version = '1.0.0-simulation'

    def run(self, snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
        snapshot = snapshot or build_ai_brain_snapshot()
        analytics = snapshot.get('analytics') or {}
        evs=[num(x.get('avg_ev_pct'), None) for x in (analytics.get('market_performance') or []) + (analytics.get('league_performance') or [])]
        evs=[e for e in evs if e is not None]
        base_ev = mean(evs) if evs else None
        volatility = pstdev(evs) if len(evs)>1 else None
        scenarios=[]
        if base_ev is None:
            scenarios.append({'name':'data_unavailable','state':'no_data','message':'Sem EV real suficiente para simulação; o sistema não cria curva sintética.'})
        else:
            for name, risk_multiplier, exposure_multiplier in [('defensive',0.55,0.7),('balanced',1.0,1.0),('aggressive',1.45,1.25)]:
                projected_ev = base_ev * exposure_multiplier
                risk_score = abs(volatility or 0) * risk_multiplier + max(0, -projected_ev) * 2
                scenarios.append({
                    'name': name,
                    'state': 'real_data',
                    'projected_ev_pct': round(projected_ev,3),
                    'volatility_proxy': None if volatility is None else round(volatility*risk_multiplier,3),
                    'risk_score': round(risk_score,3),
                    'recommendation': 'preferir este regime' if name=='defensive' and risk_score>20 else 'usar apenas com validação paper' if name=='aggressive' else 'baseline operacional',
                })
        return {'ok': True, 'simulation_version': self.version, 'data_state': snapshot.get('data_state'), 'scenarios': scenarios, 'inputs': {'base_ev_pct': base_ev, 'volatility': volatility, 'source': 'real analytics buckets, no synthetic equity curve'}, 'audit': 'simulations are deterministic scenario projections, not promises of future return'}
