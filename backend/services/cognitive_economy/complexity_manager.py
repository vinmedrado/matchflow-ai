class ComplexityManager:
    def manage(self, pressure):
        high=pressure.get('overload_risk_score',0)>.6; return {'complexity_mode':'simplified' if high else 'full_bounded', 'throttling':'adaptive' if high else 'standard', 'batching':'safe_batching_enabled'}
