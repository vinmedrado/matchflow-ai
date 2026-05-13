from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import joblib
import pandas as pd
from backend.core.storage import safe_read_dataframe, safe_write_dataframe

try:
    from backend.core.logging_config import get_logger
except Exception:  # pragma: no cover
    import logging
    logging.basicConfig(level=logging.INFO)
    def get_logger(name: str):
        return logging.getLogger(name)

logger = get_logger("matchflow.ml.predictor")

class ProbabilityPredictor:
    """Research-only probability generator. It does not create trading signals."""

    def __init__(self, project_root: Path, config: Dict[str, Any]) -> None:
        self.project_root = project_root
        self.config = config
        self.models_dir = self.project_root / config.get("models_dir", "data/ml/models")
        self.predictions_dir = self.project_root / config.get("predictions_dir", "data/ml/predictions")
        self.predictions_dir.mkdir(parents=True, exist_ok=True)

    def predict_market(self, market: str, df: pd.DataFrame) -> Path | None:
        model_path = self.models_dir / f"{market}_model.pkl"
        if not model_path.exists():
            logger.warning("Modelo ML não encontrado: %s", model_path)
            return None
        payload = joblib.load(model_path)
        model = payload["model"]
        features = payload["features"]
        missing = [col for col in features if col not in df.columns]
        if missing:
            logger.warning("Features ausentes para market=%s: %s", market, missing[:10])
            return None
        probabilities = model.predict_proba(df[features])[:, 1] if hasattr(model, "predict_proba") else model.predict(df[features])
        output = df[["date", "league", "team_key", "opponent_key", "side"]].copy()
        output["market"] = market
        output["probability"] = probabilities
        output["research_only"] = True
        output_path = self.predictions_dir / f"{market}_latest_probabilities.parquet"
        safe_write_dataframe(output, output_path, index=False)
        logger.info("Probabilidades ML salvas: market=%s path=%s", market, output_path)
        return output_path
