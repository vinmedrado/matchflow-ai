from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .common import MODE, project_root, safe_json, write_json


class SystemMonitor:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or project_root()
        self.monitoring_dir = self.root / "data/monitoring"

    def collect(self) -> dict[str, Any]:
        ops_state = safe_json(self.root / "data/ops/data_ops_state.json", {})
        paper_summary = safe_json(self.root / "data/paper_trading/paper_summary.json", {})
        decision_summary = safe_json(self.root / "data/decision_engine/decision_summary.json", {})
        calibration = safe_json(self.root / "data/ml/evaluation/calibration_report.json", {})

        engine_status = ops_state.get("engine_status", "UNKNOWN")
        future_status = ops_state.get("future_games_status", "UNKNOWN")
        paper_roi = float(paper_summary.get("ROI", paper_summary.get("roi", 0)) or 0)
        paper_drawdown = float(paper_summary.get("max_drawdown", 0) or 0)
        high_conf = int(decision_summary.get("high_confidence_count", decision_summary.get("HIGH_CONFIDENCE_SIMULATION", 0)) or 0)
        rejected = int(decision_summary.get("rejected_count", decision_summary.get("REJECTED", 0)) or 0)

        status = {
            "ok": True,
            "mode": MODE,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "overall_status": "HEALTHY",
            "risk_level": "LOW",
            "data_ops": {
                "engine_status": engine_status,
                "engine_files_count": int(ops_state.get("engine_files_count", 0) or 0),
                "future_games_status": future_status,
                "future_games_files_count": int(ops_state.get("future_games_files_count", 0) or 0),
                "last_sync": ops_state.get("last_engine_sync"),
            },
            "paper_trading": {
                "roi": paper_roi,
                "max_drawdown": paper_drawdown,
                "current_bankroll": paper_summary.get("current_bankroll"),
                "pending_signals": paper_summary.get("pending_signals", 0),
            },
            "ml": {
                "calibration_available": bool(calibration),
                "calibration_markets": list(calibration.keys()) if isinstance(calibration, dict) else [],
            },
            "decision_engine": {
                "high_confidence_candidates": high_conf,
                "rejected_candidates": rejected,
                "total_candidates": int(decision_summary.get("total_candidates", 0) or 0),
            },
        }

        if engine_status in {"ENGINE_MISSING", "ENGINE_OUTPUTS_EMPTY"}:
            status["overall_status"] = "ATTENTION_REQUIRED"
            status["risk_level"] = "HIGH"
        elif future_status in {"FUTURE_GAMES_EMPTY", "FUTURE_GAMES_NO_DATA_FILES"}:
            status["overall_status"] = "PARTIAL"
            status["risk_level"] = "MEDIUM"
        elif paper_drawdown < -20 or paper_roi < -0.10:
            status["overall_status"] = "PERFORMANCE_ATTENTION"
            status["risk_level"] = "MEDIUM"

        write_json(self.monitoring_dir / "monitoring_status.json", status)
        return status
