from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.services.ml_reliability_service import (
    MODE,
    MODELS,
    apply_calibrator,
    apply_model_calibration,
    build_calibration_artifacts,
    ece_mce,
    reliability_bins,
    sync_settled_predictions,
)


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def calibrate_probability(p: float, method: str = "sigmoid", model_name: str | None = None, root: Path | None = None) -> float:
    """Backward-compatible probability calibration entrypoint.

    When a model name/root is provided, use the persisted settled-prediction
    calibrator. Otherwise keep the legacy conservative shrinkage behavior.
    """
    if model_name:
        return apply_model_calibration(root or project_root(), model_name, p)
    return apply_calibrator(float(p), None)


def build_calibration_report(root: Path | None = None) -> dict[str, Any]:
    return build_calibration_artifacts(Path(root) if root else project_root())


__all__ = [
    "MODE", "MODELS", "calibrate_probability", "build_calibration_report",
    "sync_settled_predictions", "reliability_bins", "ece_mce",
]
