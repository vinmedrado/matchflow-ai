from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from .common import MODE, project_root, safe_parquet, write_json


class DriftDetector:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or project_root()
        self.monitoring_dir = self.root / "data/monitoring"

    def detect(self) -> dict[str, Any]:
        features = safe_parquet(self.root / "data/features/team_dataset_advanced.parquet")
        decisions = safe_parquet(self.root / "data/decision_engine/decision_candidates.parquet")
        checks: list[dict[str, Any]] = []

        feature_drift = self._feature_drift(features)
        probability_drift = self._probability_drift(decisions)
        checks.extend(feature_drift)
        checks.extend(probability_drift)
        drift_detected = any(c.get("drift_detected") for c in checks)

        payload = {
            "ok": True,
            "mode": MODE,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "drift_detected": bool(drift_detected),
            "checks": checks,
            "note": "Drift heurístico para pesquisa. Não executa ação operacional real.",
        }
        write_json(self.monitoring_dir / "drift_report.json", payload)
        return payload

    @staticmethod
    def _feature_drift(df: pd.DataFrame) -> list[dict[str, Any]]:
        if df.empty or "date" not in df.columns:
            return [{"type": "features", "status": "NO_DATA", "drift_detected": False}]
        out: list[dict[str, Any]] = []
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"]).sort_values("date")
        if len(df) < 20:
            return [{"type": "features", "status": "LOW_SAMPLE", "drift_detected": False, "rows": len(df)}]
        numeric_cols = [c for c in df.select_dtypes(include="number").columns if not c.lower().endswith("id")][:20]
        split = max(1, int(len(df) * 0.7))
        base, recent = df.iloc[:split], df.iloc[split:]
        for col in numeric_cols:
            b_mean = float(base[col].mean()) if not base[col].dropna().empty else 0.0
            r_mean = float(recent[col].mean()) if not recent[col].dropna().empty else 0.0
            b_std = float(base[col].std()) if float(base[col].std() or 0) != 0 else 1.0
            z = abs(r_mean - b_mean) / b_std
            out.append({"type": "feature_distribution", "feature": col, "baseline_mean": b_mean, "recent_mean": r_mean, "z_shift": z, "drift_detected": z >= 2.0})
        return out

    @staticmethod
    def _probability_drift(df: pd.DataFrame) -> list[dict[str, Any]]:
        if df.empty:
            return [{"type": "probabilities", "status": "NO_DATA", "drift_detected": False}]
        cols = [c for c in ["ml_probability", "ensemble_probability"] if c in df.columns]
        if not cols:
            return [{"type": "probabilities", "status": "NO_PROBABILITY_COLUMNS", "drift_detected": False}]
        out: list[dict[str, Any]] = []
        for col in cols:
            s = pd.to_numeric(df[col], errors="coerce").dropna()
            if s.empty:
                out.append({"type": "probability_distribution", "column": col, "status": "EMPTY", "drift_detected": False})
                continue
            out.append({"type": "probability_distribution", "column": col, "mean": float(s.mean()), "std": float(s.std() or 0), "low_pct": float((s < 0.4).mean()), "high_pct": float((s > 0.7).mean()), "drift_detected": bool((s > 0.95).mean() > 0.50 or (s < 0.05).mean() > 0.50)})
        return out
