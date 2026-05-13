from __future__ import annotations

from typing import Any

class LLMRouter:
    version = '1.0.0-llm-router'

    def route(self, question: str, context: dict[str, Any]) -> dict[str, Any]:
        q=(question or '').lower()
        if any(t in q for t in ['objetivo','goal','plano','workflow']):
            pipeline='planning_aware_reasoning'
        elif any(t in q for t in ['risco','drawdown','banca','exposure']):
            pipeline='risk_reasoning'
        elif any(t in q for t in ['liga','mercado','edge','estratégia']):
            pipeline='market_strategy_reasoning'
        else:
            pipeline='operational_context_reasoning'
        return {'ok': True, 'router_version': self.version, 'pipeline': pipeline, 'context_keys': sorted(list(context.keys()))[:20], 'mode': 'structured_context_router'}
