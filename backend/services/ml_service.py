from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import pandas as pd
from backend.core.storage import safe_read_dataframe, safe_write_dataframe

from backend.core.logging_config import get_logger

logger = get_logger("matchflow.ml_service")

def project_root() -> Path:
    return Path(__file__).resolve().parents[2]

def _safe_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.error("Falha ao ler JSON ML %s: %s", path, exc)
        return {}

def _safe_csv_preview(path: Path, limit: int = 20) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        return pd.read_csv(path).head(limit).to_dict(orient="records")
    except Exception as exc:
        logger.error("Falha ao ler CSV ML %s: %s", path, exc)
        return []

def ml_summary() -> Dict[str, Any]:
    root = project_root()
    dataset_path = root / "data/ml/datasets/ml_dataset.parquet"
    registry_path = root / "data/ml/models/registry.json"
    evaluation_dir = root / "data/ml/evaluation"
    predictions_dir = root / "data/ml/predictions"
    comparison_path = evaluation_dir / "ml_vs_rules_comparison.csv"

    dataset_rows = 0
    dataset_available = dataset_path.exists()
    date_range = None
    target_policy = "X(t)->y(t+1)"
    if dataset_available:
        try:
            df = safe_read_dataframe(dataset_path, columns=["date"])
            dataset_rows = int(len(df))
            dates = pd.to_datetime(df["date"], errors="coerce").dropna()
            if not dates.empty:
                date_range = {"min": str(dates.min().date()), "max": str(dates.max().date())}
        except Exception as exc:
            logger.error("Falha ao ler dataset ML: %s", exc)
            dataset_available = False

    registry = _safe_json(registry_path)
    models = registry.get("models", []) if isinstance(registry, dict) else []
    latest_by_market: Dict[str, Dict[str, Any]] = {}
    for record in models:
        market = record.get("market")
        if market:
            latest_by_market[market] = record

    metrics_by_market: Dict[str, Any] = {}
    calibration_by_market: Dict[str, Any] = {}
    feature_importance_files: Dict[str, list[str]] = {}
    if evaluation_dir.exists():
        for path in evaluation_dir.glob("*_metrics.json"):
            data = _safe_json(path)
            market = data.get("market") or path.name.split("_")[0]
            model_name = data.get("model_name", "model")
            metrics_by_market.setdefault(market, {})[model_name] = data
            calibration_by_market.setdefault(market, {})[model_name] = {
                "brier_score": data.get("brier_score"),
                "calibration_error": data.get("calibration_error"),
                "probability_distribution": data.get("probability_distribution"),
            }
        for path in evaluation_dir.glob("*_feature_importance.csv"):
            market = path.name.split("_")[0]
            feature_importance_files.setdefault(market, []).append(path.name)

    predictions = sorted([p.name for p in predictions_dir.glob("*.parquet")]) if predictions_dir.exists() else []
    comparison = _safe_csv_preview(comparison_path)
    logger.info("Resumo ML calculado: dataset=%s modelos=%s comparison_rows=%s", dataset_available, len(models), len(comparison))
    return {
        "dataset_available": dataset_available,
        "dataset_rows": dataset_rows,
        "date_range": date_range,
        "target_policy": target_policy,
        "validation": "walk_forward",
        "trained_models_count": len(models),
        "markets": sorted(latest_by_market.keys()),
        "models": latest_by_market,
        "metrics": metrics_by_market,
        "calibration": calibration_by_market,
        "feature_importance_files": feature_importance_files,
        "ml_vs_rules_comparison": comparison,
        "predictions_count": len(predictions),
        "predictions_files": predictions[:20],
        "research_only": True,
        "message": "ML Foundation is research-only and does not generate operational signals.",
    }
