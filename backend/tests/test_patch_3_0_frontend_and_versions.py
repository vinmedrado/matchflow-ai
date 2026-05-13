from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_team_analytics_calls_advanced_summary():
    content = (PROJECT_ROOT / "frontend/src/pages/TeamAnalytics.jsx").read_text(encoding="utf-8")
    assert "/api/datasets/team-summary" in content
    assert "/api/datasets/advanced-summary" in content
    assert "apiRequest" in content
    assert "run_advanced_features_pipeline.py" in content


def test_patch_3_versions_are_updated():
    app_config = json.loads((PROJECT_ROOT / "config/app_config.json").read_text(encoding="utf-8"))
    package = json.loads((PROJECT_ROOT / "frontend/package.json").read_text(encoding="utf-8"))
    assert app_config["app"]["version"] == "3.0.0"
    assert package["version"] == "3.0.0"
