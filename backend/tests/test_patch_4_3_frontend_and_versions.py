
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_versions_are_4_3_0():
    config = json.loads((ROOT / "config" / "app_config.json").read_text(encoding="utf-8"))
    package = json.loads((ROOT / "frontend" / "package.json").read_text(encoding="utf-8"))
    assert config["app"]["version"] == "4.3.0"
    assert package["version"] == "4.3.0"


def test_backtest_lab_consumes_refinement_summary():
    content = (ROOT / "frontend" / "src" / "pages" / "BacktestLab.jsx").read_text(encoding="utf-8")
    assert "/api/backtest/refinement-summary" in content
    assert "Strategy Refinement" in content
    assert "refined_candidates_top_10" in content
