class OverloadDetector:
    def detect(self, pressure):
        return {'overload_detected': pressure.get('overload_risk_score',0)>.65, 'risk_score': pressure.get('overload_risk_score',0)}
