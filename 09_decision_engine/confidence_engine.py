from __future__ import annotations


def confidence_band(score: float) -> str:
    """Return simulation-only confidence label for a 0-100 score."""
    score = max(0.0, min(100.0, float(score)))
    if score >= 80:
        return "HIGH_CONFIDENCE_SIMULATION"
    if score >= 60:
        return "MEDIUM_CONFIDENCE_SIMULATION"
    if score >= 40:
        return "WATCH_ONLY"
    return "REJECTED"
