
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_backtest_lab_consumes_analysis_summary():
    content = (ROOT / "frontend/src/pages/BacktestLab.jsx").read_text(encoding="utf-8")

    assert "/api/backtest/analysis-summary" in content
    assert "Ranking de Mercados" in content
    assert "Ranking de Estratégias" in content
    assert "Insights automáticos" in content


def test_versions_are_4_1():
    import json

    app_config = json.loads((ROOT / "config/app_config.json").read_text(encoding="utf-8"))
    package = json.loads((ROOT / "frontend/package.json").read_text(encoding="utf-8"))

    assert app_config["app"]["version"] == "4.1.0"
    assert package["version"] == "4.1.0"
