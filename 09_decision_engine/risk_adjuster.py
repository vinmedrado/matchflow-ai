from __future__ import annotations

from typing import Iterable, Tuple

CRITICAL_RISK_FLAGS = {
    "LOW_SAMPLE_SIZE",
    "POSSIBLE_OVERFITTING",
}
RISK_PENALTIES = {
    "LOW_SAMPLE_SIZE": 25,
    "HIGH_DRAWDOWN": 18,
    "UNSTABLE_ROI": 15,
    "ODDS_RANGE_DEPENDENCY": 10,
    "LEAGUE_DEPENDENCY": 10,
    "NEGATIVE_ROLLING_ROI": 15,
    "POSSIBLE_OVERFITTING": 20,
}


def parse_flags(value: object) -> list[str]:
    if value is None:
        return []
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "[]"}:
        return []
    raw = text.replace("[", "").replace("]", "").replace("'", "").replace('"', "")
    parts = []
    for token in raw.replace(";", ",").replace("|", ",").split(","):
        flag = token.strip().upper()
        if flag:
            parts.append(flag)
    return list(dict.fromkeys(parts))


def adjust_score(score: float, risk_flags: Iterable[str]) -> Tuple[float, list[str]]:
    flags = [str(flag).upper() for flag in risk_flags if str(flag).strip()]
    penalty = sum(RISK_PENALTIES.get(flag, 5) for flag in flags)
    adjusted = max(0.0, min(100.0, float(score) - penalty))
    if "LOW_SAMPLE_SIZE" in flags:
        adjusted = min(adjusted, 59.0)
    if "POSSIBLE_OVERFITTING" in flags:
        adjusted = min(adjusted, 59.0)
    if "HIGH_DRAWDOWN" in flags and "UNSTABLE_ROI" in flags:
        adjusted = min(adjusted, 49.0)
    return adjusted, flags
