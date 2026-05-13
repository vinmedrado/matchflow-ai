from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_backtest_lab_is_routed_in_frontend():
    app_jsx = (PROJECT_ROOT / "frontend/src/App.jsx").read_text(encoding="utf-8")
    assert "BacktestLab" in app_jsx
    assert "page === 'Backtest Lab'" in app_jsx


def test_backtest_lab_uses_existing_api_client():
    page = (PROJECT_ROOT / "frontend/src/pages/BacktestLab.jsx").read_text(encoding="utf-8")
    assert "apiRequest" in page
    assert "/api/backtest/summary" in page


def test_version_compatibility_markers_are_preserved():
    import json

    config = (PROJECT_ROOT / "config/app_config.json").read_text(encoding="utf-8")
    package = json.loads((PROJECT_ROOT / "frontend/package.json").read_text(encoding="utf-8"))
    assert '"version": "4.0.0"' in config
    assert package["version"] == "6.0.1"
    assert "4.0.0" in package.get("legacy_version_compat", [])
