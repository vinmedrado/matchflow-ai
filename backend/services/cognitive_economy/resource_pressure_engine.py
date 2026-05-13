class ResourcePressureEngine:
    def pressure(self, recursive, meta):
        cost=(recursive.get('reasoning') or {}).get('reasoning_cost_score',.3); over=meta.get('over_adaptation_risk',False); return {'overload_risk_score': round(min(1,cost + (.2 if over else 0)),3), 'pressure_state':'elevated' if cost>.5 or over else 'normal'}
