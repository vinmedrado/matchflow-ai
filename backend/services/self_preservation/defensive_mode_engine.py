class DefensiveModeEngine:
    def mode(self, guard, overload, executive):
        gov=executive.get('governance') or {}; low=guard.get('self_preservation_score',1)<.55
        if overload.get('overload_detected'): mode='emergency_stabilization_mode'
        elif gov.get('safe_mode'): mode='safe_mode'
        elif low: mode='defensive_mode'
        elif ((executive.get('executive_observability') or {}).get('uncertainty_score') or 0)>.55: mode='low_confidence_mode'
        else: mode='normal_mode'
        return {'mode':mode, 'available_modes':['safe_mode','defensive_mode','degraded_mode','low_confidence_mode','emergency_stabilization_mode'], 'critical_actions_allowed': mode=='normal_mode'}
