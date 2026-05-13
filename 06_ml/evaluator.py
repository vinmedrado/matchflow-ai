from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import numpy as np
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss, precision_score, recall_score, roc_auc_score

try:
    from backend.core.logging_config import get_logger
except Exception:  # pragma: no cover
    import logging
    logging.basicConfig(level=logging.INFO)
    def get_logger(name: str):
        return logging.getLogger(name)

logger = get_logger("matchflow.ml.evaluator")

class ModelEvaluator:
    def __init__(self, project_root: Path, config: Dict[str, Any]) -> None:
        self.project_root = project_root
        self.config = config
        self.evaluation_dir = self.project_root / config.get("evaluation_dir", "data/ml/evaluation")
        self.evaluation_dir.mkdir(parents=True, exist_ok=True)
        self.n_bins = int(config.get("calibration_bins", 10))

    def evaluate(self, market: str, model_name: str, y_true, probabilities, suffix: str | None = None) -> Dict[str, Any]:
        y_true = np.asarray(y_true).astype(int)
        probabilities = np.clip(np.asarray(probabilities, dtype=float), 0.0, 1.0)
        predictions = (probabilities >= 0.5).astype(int)
        metrics = {
            "market": market,
            "model_name": model_name,
            "rows": int(len(y_true)),
            "positive_rate": float(y_true.mean()) if len(y_true) else 0.0,
            "accuracy": self._safe_metric(lambda: accuracy_score(y_true, predictions)),
            "precision": self._safe_metric(lambda: precision_score(y_true, predictions, zero_division=0)),
            "recall": self._safe_metric(lambda: recall_score(y_true, predictions, zero_division=0)),
            "roc_auc": self._safe_metric(lambda: roc_auc_score(y_true, probabilities), default=None),
            "log_loss": self._safe_metric(lambda: log_loss(y_true, probabilities, labels=[0, 1]), default=None),
            "brier_score": self._safe_metric(lambda: brier_score_loss(y_true, probabilities), default=None),
            "calibration_error": self._expected_calibration_error(y_true, probabilities),
            "probability_distribution": self._probability_distribution(probabilities),
        }
        file_suffix = f"_{suffix}" if suffix else ""
        path = self.evaluation_dir / f"{market}_{model_name}{file_suffix}_metrics.json"
        path.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("Métricas ML salvas: market=%s model=%s path=%s", market, model_name, path)
        return metrics

    def _expected_calibration_error(self, y_true: np.ndarray, probabilities: np.ndarray) -> float | None:
        if len(y_true) == 0:
            return None
        bins = np.linspace(0.0, 1.0, self.n_bins + 1)
        ece = 0.0
        for i in range(self.n_bins):
            left, right = bins[i], bins[i + 1]
            mask = (probabilities >= left) & (probabilities < right if i < self.n_bins - 1 else probabilities <= right)
            if not mask.any():
                continue
            bin_conf = float(probabilities[mask].mean())
            bin_acc = float(y_true[mask].mean())
            ece += float(mask.mean()) * abs(bin_acc - bin_conf)
        return float(ece)

    def _probability_distribution(self, probabilities: np.ndarray) -> Dict[str, Any]:
        bins = np.linspace(0.0, 1.0, self.n_bins + 1)
        counts, edges = np.histogram(probabilities, bins=bins)
        return {
            "bins": [f"{edges[i]:.2f}-{edges[i+1]:.2f}" for i in range(len(edges) - 1)],
            "counts": [int(x) for x in counts.tolist()],
            "mean": float(probabilities.mean()) if len(probabilities) else None,
            "std": float(probabilities.std()) if len(probabilities) else None,
            "min": float(probabilities.min()) if len(probabilities) else None,
            "max": float(probabilities.max()) if len(probabilities) else None,
        }

    def _safe_metric(self, func, default: Any = 0.0) -> Any:
        try:
            value = func()
            if value is None:
                return default
            if isinstance(value, float) and (np.isnan(value) or np.isinf(value)):
                return default
            return float(value)
        except Exception:
            return default
