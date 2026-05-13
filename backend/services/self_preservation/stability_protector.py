class StabilityProtector:
    def protect(self, mode): return {'stability_actions':['pause recursive expansion','require approval for critical changes'] if mode.get('mode')!='normal_mode' else ['maintain guardrails'], 'circuit_breaker_active': mode.get('mode') in {'safe_mode','emergency_stabilization_mode'}}
