class PhilosophyAdaptationEngine:
    def adapt(self, strategic): return {'risk_philosophy':'capital_preservation_first' if strategic.get('macro_behavior')=='protective' else 'balanced_ev_with_guardrails'}
