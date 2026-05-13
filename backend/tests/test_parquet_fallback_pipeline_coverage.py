from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

from backend.core import storage
from backend.core.storage import safe_read_dataframe, safe_write_dataframe

ROOT = Path(__file__).resolve().parents[2]


def test_decision_engine_writes_csv_fallback_without_parquet_engine(monkeypatch):
    monkeypatch.setenv("MATCHFLOW_DISABLE_PARQUET", "1")
    monkeypatch.setattr(storage, "get_parquet_engine", lambda: None)
    import importlib.util
    module_path = ROOT / "09_decision_engine" / "decision_engine.py"
    spec = importlib.util.spec_from_file_location("decision_engine_storage_fallback_test", module_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    summary = mod.run_decision_engine(ROOT)
    assert summary["ok"] is True
    assert summary["storage"]["fallback_used"] is True
    assert summary["storage"]["storage_format"] == "csv"
    assert (ROOT / "data/decision_engine/decision_candidates.csv").exists()


def test_full_pipeline_runs_with_forced_csv_fallback():
    env = __import__("os").environ.copy()
    env["MATCHFLOW_DISABLE_PARQUET"] = "1"
    completed = subprocess.run(
        [sys.executable, str(ROOT / "run_full_decision_pipeline.py")],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        env=env,
        timeout=120,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr[-2000:]
    summary = json.loads((ROOT / "data/reports/full_decision_pipeline_summary.json").read_text(encoding="utf-8"))
    assert summary["ok"] is True
    assert (ROOT / "data/decision_engine/decision_candidates.csv").exists()


def test_parquet_engine_preferred_when_available(monkeypatch, tmp_path):
    monkeypatch.delenv("MATCHFLOW_DISABLE_PARQUET", raising=False)
    if storage.get_parquet_engine() is None:
        return
    df = pd.DataFrame([{"a": 1}])
    meta = safe_write_dataframe(df, tmp_path / "preferred.parquet")
    assert meta["storage_format"] == "parquet"
    assert meta["fallback_used"] is False
    loaded = safe_read_dataframe(tmp_path / "preferred.parquet")
    assert int(loaded.iloc[0]["a"]) == 1
