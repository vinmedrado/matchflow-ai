from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from .common import MODE, project_root, safe_csv, safe_json, write_json


class AnomalyDetector:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or project_root()
        self.monitoring_dir = self.root / "data/monitoring"

    def detect(self) -> dict[str, Any]:
        anomalies: list[dict[str, Any]] = []
        equity = safe_csv(self.root / "data/paper_trading/paper_equity_curve.csv")
        decisions = safe_csv(self.root / "data/decision_engine/decision_candidates.csv")

        if not equity.empty:
            numeric = None
            for col in ["bankroll", "equity", "current_bankroll"]:
                if col in equity.columns:
                    numeric = pd.to_numeric(equity[col], errors="coerce").dropna()
                    break
            if numeric is not None and len(numeric) >= 3:
                changes = numeric.diff().dropna()
                std = float(changes.std() or 0)
                if std > 0:
                    spikes = changes[changes.abs() > 3 * std]
                    if len(spikes):
                        anomalies.append({"type": "PERFORMANCE_SPIKE", "count": int(len(spikes)), "severity": "MEDIUM"})

        if not decisions.empty:
            risk_col = "risk_flags" if "risk_flags" in decisions.columns else None
            if risk_col:
                risk_rate = float(decisions[risk_col].astype(str).str.len().gt(0).mean())
                if risk_rate > 0.70:
                    anomalies.append({"type": "RISK_FLAGS_SPIKE", "risk_rate": risk_rate, "severity": "MEDIUM"})
            score_col = "decision_score" if "decision_score" in decisions.columns else None
            if score_col:
                scores = pd.to_numeric(decisions[score_col], errors="coerce").dropna()
                if not scores.empty and float(scores.mean()) < 30:
                    anomalies.append({"type": "LOW_DECISION_SCORE_AVERAGE", "average_score": float(scores.mean()), "severity": "LOW"})

        payload = {
            "ok": True,
            "mode": MODE,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "anomalies_detected": bool(anomalies),
            "anomalies": anomalies,
            "note": "Anomalias são alertas de pesquisa para simulação, sem ação real.",
        }
        write_json(self.monitoring_dir / "anomaly_report.json", payload)
        return payload
