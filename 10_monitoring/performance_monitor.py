from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .common import MODE, project_root, safe_csv, safe_json, write_json


class PerformanceMonitor:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or project_root()

    def collect(self) -> dict[str, Any]:
        paper = safe_json(self.root / "data/paper_trading/paper_summary.json", {})
        summary = safe_csv(self.root / "data/backtest/results/summary_results.csv")
        refinement = safe_csv(self.root / "data/backtest/refinement/refinement_risk_report.csv")
        payload = {
            "ok": True,
            "mode": MODE,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "paper_roi": float(paper.get("ROI", paper.get("roi", 0)) or 0),
            "paper_max_drawdown": float(paper.get("max_drawdown", 0) or 0),
            "strategies_count": int(len(summary)),
            "high_risk_strategies": int((refinement.astype(str).apply(lambda r: r.str.contains("HIGH|DISCARD|OVERFITTING", case=False, regex=True).any(), axis=1)).sum()) if not refinement.empty else 0,
        }
        return payload
