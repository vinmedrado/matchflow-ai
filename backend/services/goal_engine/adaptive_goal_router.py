from __future__ import annotations
from typing import Any

class AdaptiveGoalRouter:
    def route(self, objectives: list[dict[str, Any]]) -> list[dict[str, Any]]:
        routes=[]
        for obj in objectives:
            owner = obj.get('owner','intelligence_coordinator')
            lane = 'defensive' if obj.get('id') in {'protect_bankroll','reduce_exposure','reduce_volatility'} else 'research' if obj.get('id') in {'improve_robustness','maximize_ev_quality'} else 'monitoring'
            routes.append({'objective_id': obj['id'], 'route_to': owner, 'lane': lane, 'priority': obj.get('priority'), 'state': obj.get('state')})
        return routes
