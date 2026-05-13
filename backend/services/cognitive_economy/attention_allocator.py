from __future__ import annotations
class AttentionAllocator:
    def allocate(self, executive):
        gov=executive.get('governance') or {}; return {'attention_policy':'risk_first' if gov.get('safe_mode') else 'balanced', 'allocation': {'risk':.35,'strategy':.25,'learning':.2,'experimentation':.2}}
