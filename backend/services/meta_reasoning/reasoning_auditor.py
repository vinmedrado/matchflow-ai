from __future__ import annotations
from typing import Any

class ReasoningAuditor:
    version='1.0.0-meta-reasoning'
    def audit(self, decision: dict[str, Any], world_model: dict[str, Any], agent_cycle: dict[str, Any] | None = None) -> dict[str, Any]:
        issues=[]; contradictions=[]
        confidence=float(decision.get('confidence_score') or decision.get('confidence') or 0)
        data_state=world_model.get('data_state')
        regime=world_model.get('regime')
        if data_state != 'real_data' and confidence > 0.75:
            issues.append({'type':'overconfidence','severity':'high','message':'Confiança alta com dados não reais/insuficientes.'})
        if regime in {'defensive','diagnostic'} and 'MAINTAIN' in str(decision.get('action','')):
            contradictions.append({'type':'posture_conflict','message':'Decisão neutra conflita com regime defensivo/diagnóstico.'})
        consensus=(agent_cycle or {}).get('consensus') or {}
        conflict_count = len((agent_cycle or {}).get('conflicts') or [])
        if isinstance(consensus, dict):
            conflict_count = max(conflict_count, int(consensus.get('conflict_count') or 0))
        elif isinstance(consensus, list):
            conflict_count = max(conflict_count, len([c for c in consensus if isinstance(c, dict) and c.get('status') == 'conflict']))
        if conflict_count > 0:
            issues.append({'type':'agent_conflict','severity':'medium','message':f"{conflict_count} conflito(s) entre agentes exigem revisão."})
        quality = max(0.2, min(0.98, 0.86 - 0.12*len(issues) - 0.15*len(contradictions)))
        return {'ok':True,'version':self.version,'reasoning_quality_score':round(quality,3),'issues':issues,'contradictions':contradictions,'verdict':'review_required' if issues or contradictions else 'reasoning_consistent','audit_policy':'no autonomous mutation without traceable review'}
