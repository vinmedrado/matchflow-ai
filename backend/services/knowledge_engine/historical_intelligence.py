from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

class HistoricalIntelligenceEngine:
    version='1.0.0-knowledge-evolution'
    def evolve(self, snapshot: dict[str, Any], world_model: dict[str, Any], memory_graph: dict[str, Any] | None = None) -> dict[str, Any]:
        alerts=snapshot.get('alerts') or []
        regime=world_model.get('regime')
        concepts=[]; patterns=[]
        if regime in {'defensive','conservative'}:
            concepts.append({'id':'risk_first_posture','label':'Postura risk-first','description':'Quando risco/alertas sobem, o sistema prioriza preservação de banca.'})
        for a in alerts[:5]:
            patterns.append({'id':f"pattern_{a.get('id','alert')}", 'source':a.get('type'), 'claim':a.get('title'), 'confidence':0.62 if a.get('state')=='real_data' else 0.42})
        if not patterns:
            patterns.append({'id':'pattern_stable_monitoring','source':'world_model','claim':'Sem cluster crítico; manter observação temporal.', 'confidence':0.55})
        abstractions=[{'id':'liquidity_risk_abstraction','statement':'Mercados/ligas com EV fraco e alertas recorrentes devem receber filtros mais rígidos.'}]
        return {'ok':True,'version':self.version,'generated_at':datetime.now(timezone.utc).isoformat(),'concepts':concepts,'patterns':patterns,'abstractions':abstractions,'strategic_memory_state':'evolving','trace':'alerts + regime + memory graph -> concepts/patterns/abstractions'}
