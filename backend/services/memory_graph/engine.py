from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

from backend.services.ai_brain import build_ai_brain_snapshot
from backend.services.agents import IntelligenceCoordinator

class MemoryGraphEngine:
    version = '1.0.0-memory-graph'

    def build(self, snapshot: dict[str, Any] | None = None, agent_cycle: dict[str, Any] | None = None) -> dict[str, Any]:
        snapshot = snapshot or build_ai_brain_snapshot()
        agent_cycle = agent_cycle or IntelligenceCoordinator().run('memory_graph_context')
        nodes=[]; edges=[]
        def add_node(node_id, node_type, label, **attrs):
            nodes.append({'id': node_id, 'type': node_type, 'label': label, **attrs})
        def add_edge(src, dst, rel, weight=1.0, **attrs):
            edges.append({'source': src, 'target': dst, 'relationship': rel, 'weight': round(float(weight),3), **attrs})
        add_node('bankroll','bankroll','Bankroll', state=snapshot.get('data_state'))
        add_node('risk','risk','Risk Layer')
        add_node('decision','decision','Autonomous Decision')
        for alert in snapshot.get('alerts', [])[:12]:
            aid=f"alert:{alert.get('id')}"; add_node(aid,'alert',alert.get('title'),severity=alert.get('severity'),state=alert.get('state'))
            add_edge(aid,'risk','contributes_to', alert.get('priority') or 1)
        for item in (snapshot.get('analytics') or {}).get('league_performance', [])[:8]:
            lid=f"league:{item.get('name')}"; add_node(lid,'league',item.get('name'),ev=item.get('avg_ev_pct'),signals=item.get('signals'),state=item.get('state'))
            add_edge(lid,'decision','influences', abs(float(item.get('avg_ev_pct') or 0))+1)
        for item in (snapshot.get('analytics') or {}).get('market_performance', [])[:8]:
            mid=f"market:{item.get('name')}"; add_node(mid,'market',item.get('name'),ev=item.get('avg_ev_pct'),signals=item.get('signals'),state=item.get('state'))
            add_edge(mid,'decision','influences', abs(float(item.get('avg_ev_pct') or 0))+1)
        for f in agent_cycle.get('findings', [])[:15]:
            fid=f"finding:{f.get('agent')}:{f.get('type')}"; add_node(fid,'finding',f.get('title'),agent=f.get('agent'),severity=f.get('severity'))
            add_edge(fid, 'decision', 'supports_decision', f.get('confidence') or 0.5)
        cycles = self._detect_cycles(nodes, edges)
        return {'ok': True, 'graph_version': self.version, 'generated_at': datetime.now(timezone.utc).isoformat(), 'data_state': snapshot.get('data_state'), 'nodes': nodes, 'edges': edges, 'patterns': cycles, 'summary': {'nodes': len(nodes), 'edges': len(edges), 'repeated_entities': len(cycles)}}

    def _detect_cycles(self, nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
        by_type=Counter(n['type'] for n in nodes)
        patterns=[]
        for typ,count in by_type.items():
            if count >= 3:
                patterns.append({'type':'repeated_entity_cluster','entity_type':typ,'count':count,'interpretation':f'{count} nós do tipo {typ} conectados ao contexto operacional.'})
        return patterns
