from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from backend.core.storage import safe_read_dataframe, safe_write_dataframe

from .automation_state import mark_export
from .common import MODE, automation_dir, load_config, sanitize_text


def _read_candidates(root: Path) -> pd.DataFrame:
    csv_path = root / "data/decision_engine/decision_candidates.csv"
    parquet_path = root / "data/decision_engine/decision_candidates.parquet"
    if csv_path.exists() and csv_path.stat().st_size > 0:
        return pd.read_csv(csv_path)
    if parquet_path.exists() and parquet_path.stat().st_size > 0:
        return safe_read_dataframe(parquet_path)
    return pd.DataFrame()


def export_candidates(root: Path | None = None) -> dict[str, Any]:
    root = root or Path.cwd()
    config = load_config(root)
    allowed = set(config.get("export", {}).get("allowed_confidence_bands", ["HIGH_CONFIDENCE_SIMULATION", "MEDIUM_CONFIDENCE_SIMULATION"]))
    df = _read_candidates(root)
    if df.empty:
        out = pd.DataFrame(columns=["match", "market", "score", "probability", "risks", "explanation", "mode"])
    else:
        band_col = "confidence_band" if "confidence_band" in df.columns else "simulation_label"
        if band_col in df.columns:
            df = df[df[band_col].isin(allowed)].copy()
        rows = []
        for _, row in df.iterrows():
            match = row.get("match") or f"{row.get('home_team','')} vs {row.get('away_team','')}"
            probability = row.get("ensemble_probability", row.get("ml_probability", ""))
            risks = row.get("risk_flags", row.get("main_risks", ""))
            explanation = row.get("why_selected", row.get("explanation", ""))
            rows.append({
                "match": sanitize_text(match),
                "market": sanitize_text(row.get("market", "")),
                "score": row.get("decision_score", row.get("score", "")),
                "probability": probability,
                "risks": sanitize_text(risks),
                "explanation": sanitize_text(explanation),
                "mode": MODE,
            })
        out = pd.DataFrame(rows)
    path = automation_dir(root) / "exported_candidates.csv"
    out.to_csv(path, index=False)
    mark_export(root)
    return {"mode": MODE, "exported_count": int(len(out)), "path": str(path), "allowed_confidence_bands": sorted(allowed)}
