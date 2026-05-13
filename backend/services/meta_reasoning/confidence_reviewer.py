from __future__ import annotations
from typing import Any

class ConfidenceReviewer:
    def review(self, confidence: float, uncertainty: dict[str, Any], reasoning_audit: dict[str, Any]) -> dict[str, Any]:
        penalty = float(uncertainty.get('uncertainty_score',0))*0.35 + (1-float(reasoning_audit.get('reasoning_quality_score',1)))*0.3
        adjusted=max(0.05, min(0.99, confidence-penalty))
        return {'raw_confidence':round(confidence,3),'adjusted_confidence':round(adjusted,3),'penalty':round(penalty,3),'review':'confidence_adjusted_for_uncertainty_and_reasoning_quality'}
