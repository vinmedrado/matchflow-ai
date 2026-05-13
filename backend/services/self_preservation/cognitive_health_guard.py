class CognitiveHealthGuard:
    def evaluate(self, pressure, executive):
        health=((executive.get('cognitive_digital_twin') or {}).get('cognitive_health_score') or .5); return {'self_preservation_score': round(min(1, max(0, health - pressure.get('overload_risk_score',0)*.2)),3), 'health':health}
