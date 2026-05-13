from __future__ import annotations

from pathlib import Path

import pandas as pd

from backend.core import storage


def test_storage_prefers_declared_parquet_engine(monkeypatch):
    monkeypatch.delenv("MATCHFLOW_DISABLE_PARQUET", raising=False)
    def fake_find_spec(name):
        return object() if name == "pyarrow" else None
    monkeypatch.setattr(storage.importlib.util, "find_spec", fake_find_spec)
    assert storage.get_parquet_engine() == "pyarrow"
    assert storage.has_parquet_support() is True


def test_storage_uses_csv_fallback_without_parquet_engine(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "get_parquet_engine", lambda: None)
    df = pd.DataFrame([{"match_id": "m1", "value": 1.25}])
    parquet = tmp_path / "sample.parquet"

    meta = storage.safe_write_dataframe(df, parquet)

    assert meta["fallback_used"] is True
    assert meta["storage_format"] == "csv"
    assert (tmp_path / "sample.csv").exists()
    loaded = storage.safe_read_dataframe(parquet)
    assert loaded.to_dict(orient="records")[0]["match_id"] == "m1"


def test_storage_read_attempts_parquet_then_csv(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "get_parquet_engine", lambda: None)
    csv = tmp_path / "fallback.csv"
    pd.DataFrame([{"a": 1, "b": 2}]).to_csv(csv, index=False)

    loaded = storage.safe_read_parquet_or_csv(tmp_path / "fallback.parquet")

    assert loaded.shape == (1, 2)
    assert int(loaded.iloc[0]["a"]) == 1


def test_storage_status_contract(monkeypatch):
    monkeypatch.setattr(storage, "get_parquet_engine", lambda: "fastparquet")
    status = storage.storage_status()
    assert status["parquet_available"] is True
    assert status["parquet_engine"] == "fastparquet"
    assert status["storage_fallback_enabled"] is True
