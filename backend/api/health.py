from __future__ import annotations

from fastapi import APIRouter

from backend.core.logging_config import get_logger

logger = get_logger("matchflow.api.health")
router = APIRouter()


@router.get("/health")
def health() -> dict:
    logger.info("Healthcheck executado")
    return {"ok": True, "status": "healthy", "service": "MatchFlow Analytics API"}


@router.get("/ready")
def readiness() -> dict:
    from backend.core.storage import storage_status
    return {"ok": True, "status": "ready", "service": "MatchFlow Analytics API", "storage": storage_status()}


@router.get("/api/health/status")
def health_status() -> dict:
    return {"ok": True, "status": "healthy", "readiness": "ready", "version": "6.0.1"}


@router.get("/metrics")
def metrics() -> dict:
    from pathlib import Path
    import json
    root = Path(__file__).resolve().parents[2]
    def read(path, default):
        try:
            p = root / path
            return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default
        except Exception:
            return default
    drift = read("data/monitoring/drift_report.json", {})
    coverage = read("data/reports/flashscore_coverage_report.json", {})
    return {
        "ok": True,
        "service": "matchflow",
        "mode": "PAPER_TRADING_SIMULATION_ONLY",
        "metrics": {
            "drift_score": drift.get("drift_score", 0),
            "flashscore_odds_coverage_pct": coverage.get("odds_coverage_pct", 0),
            "flashscore_stats_coverage_pct": coverage.get("stats_coverage_pct", 0),
            "flashscore_total_matches": coverage.get("total_matches", 0),
        },
    }
