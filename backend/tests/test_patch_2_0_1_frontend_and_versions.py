from __future__ import annotations

import json
from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_team_analytics_is_routed_in_app():
    root = project_root()
    app = (root / "frontend/src/App.jsx").read_text(encoding="utf-8")
    assert "import TeamAnalytics" in app
    assert "page === 'Team Analytics'" in app
    assert "Content = TeamAnalytics" in app
    assert "'Backtest Lab', 'ML Lab'" in app


def test_team_analytics_uses_existing_api_request_client():
    root = project_root()
    page = (root / "frontend/src/pages/TeamAnalytics.jsx").read_text(encoding="utf-8")
    client = (root / "frontend/src/api/client.js").read_text(encoding="utf-8")
    assert "import { apiRequest }" in page
    assert "apiRequest('/api/datasets/team-summary')" in page
    assert "export async function apiRequest" in client
    assert "apiClient" not in page


def test_versions_are_2_0_1():
    root = project_root()
    config = json.loads((root / "config/app_config.json").read_text(encoding="utf-8"))
    package = json.loads((root / "frontend/package.json").read_text(encoding="utf-8"))
    main = (root / "backend/main.py").read_text(encoding="utf-8")
    assert config["app"]["version"] == "2.0.1"
    assert package["version"] == "2.0.1"
    assert "2.0.1" in main
