from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pandas as pd

def project_root() -> Path:
    return Path(__file__).resolve().parents[2]

def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def test_ml_dataset_and_targets_exist():
    root = project_root()
    module = load_module(root / "06_ml/dataset_builder.py", "ml_dataset_builder_test")
    config = json.loads((root / "config/ml_config.json").read_text(encoding="utf-8"))
    df = module.MLDatasetBuilder(root, config).build()
    assert not df.empty
    for col in ["target_goals", "target_corners", "target_shots", "target_btts"]:
        assert col in df.columns
        assert df[col].notna().sum() > 0
    assert (root / "data/ml/datasets/ml_dataset.parquet").exists()

def test_temporal_split_does_not_use_future_in_train():
    root = project_root()
    config = json.loads((root / "config/ml_config.json").read_text(encoding="utf-8"))
    df = pd.read_parquet(root / "data/ml/datasets/ml_dataset.parquet")
    module = load_module(root / "06_ml/model_trainer.py", "ml_model_trainer_test")
    trainer = module.ModelTrainer(root, config)
    data = df[df["target_goals"].notna()].copy()
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data = data.sort_values("date").reset_index(drop=True)
    train_df, test_df = trainer._time_split(data)
    assert train_df["date"].max() <= test_df["date"].min()

def test_models_evaluation_and_predictions_are_generated():
    root = project_root()
    module = load_module(root / "06_ml/run_ml_pipeline.py", "ml_pipeline_test")
    module.run()
    assert (root / "data/ml/models/registry.json").exists()
    registry = json.loads((root / "data/ml/models/registry.json").read_text(encoding="utf-8"))
    assert len(registry.get("models", [])) > 0
    assert any((root / "data/ml/evaluation").glob("*_metrics.json"))
    assert any((root / "data/ml/predictions").glob("*_predictions.parquet"))

def test_ml_summary_endpoint(client, auth_headers):
    response = client.get("/api/ml/summary", headers=auth_headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    data = payload["data"]
    assert data["research_only"] is True
    assert "trained_models_count" in data
    assert "metrics" in data
