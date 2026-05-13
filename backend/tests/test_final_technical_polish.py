from __future__ import annotations

import importlib
import importlib.util
from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

from backend.main import app

def _admin_headers_for_protected_data_engine(client):
    res = client.post("/api/auth/login", json={"email": "admin@matchflow.local", "password": "admin123"})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}

from backend.services.data_engine.providers.flashscore.validate_provider import validate_flashscore_provider


def root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_module(rel: str, name: str):
    path = root() / rel
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_main_flow_status_never_uses_external_football_data_engine(monkeypatch):
    client = TestClient(app)
    for path in [
        "/api/data-engine/status",
        "/api/data-engine/providers/status",
        "/api/data-engine/providers/flashscore/status",
    ]:
        resp = client.get(path, headers=_admin_headers_for_protected_data_engine(client))
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["ok"] is True
        text = str(payload).lower()
        assert "uses_external_repo': true" not in text
        assert "is_using_external_repo': true" not in text


def test_legacy_modules_are_explicitly_deprecated_headers():
    for rel in [
        "01_scripts/data_engine_loader.py",
        "07_data_ops/data_engine_runner.py",
        "07_data_ops/flashscore_bridge.py",
        "07_data_ops/engine_discovery.py",
    ]:
        content = (root() / rel).read_text(encoding="utf-8")[:500]
        assert "DEPRECATED LEGACY COMPATIBILITY" in content
        assert "backend/services/data_engine/providers/flashscore" in content


def test_demo_presentation_mode_adds_visual_only_fields(monkeypatch):
    monkeypatch.setenv("DATA_ENGINE_MODE", "demo")
    module = load_module("09_decision_engine/decision_engine.py", "decision_engine_demo_polish")
    df = pd.DataFrame([
        {
            "decision_status": "REJECTED",
            "confidence_band": "REJECTED",
            "signal_label": "VALUE SIGNAL",
            "decision_score": 84,
            "suggested_stake_pct": 0.02,
            "suggested_stake_amount": 20,
            "suggested_allocation_pct": 0.02,
            "suggested_allocation_amount": 20,
            "action_required": True,
            "bankroll_reference": 1000,
        }
    ])
    safe = module._enforce_decision_output_safety(df)
    demo = module._apply_demo_presentation_mode(safe)
    row = demo.iloc[0]
    assert row["decision_status"] == "REJECTED"
    assert row["suggested_stake_pct"] == 0
    assert row["suggested_stake_amount"] == 0
    assert row["suggested_allocation_pct"] == 0
    assert row["suggested_allocation_amount"] == 0
    assert row["action_required"] is False or str(row["action_required"]).lower() == "false"
    assert bool(row["demo_only"]) is True
    assert bool(row["is_demo_data"]) is True
    assert row["signal_label"] == "DEMO WATCHLIST"
    assert row["demo_signal_label"] == "DEMO WATCHLIST"
    assert row["demo_suggested_stake_pct"] > 0


def test_api_sanitizer_applies_demo_watchlist_without_real_stake(monkeypatch):
    monkeypatch.setenv("DATA_ENGINE_MODE", "demo")
    service = load_module("backend/services/decision_engine_service.py", "decision_service_demo_polish")
    row = service._sanitize_candidate_row({
        "decision_status": "REJECTED",
        "confidence_band": "REJECTED",
        "signal_label": "VALUE SIGNAL",
        "decision_score": 90,
        "suggested_allocation_pct": 0.05,
        "suggested_allocation_amount": 50,
        "action_required": True,
    })
    assert row["suggested_stake_pct"] == 0
    assert row["suggested_allocation_pct"] == 0
    assert row["action_required"] is False
    assert bool(row["demo_only"]) is True
    assert row["signal_label"] == "DEMO WATCHLIST"
    assert row["demo_suggested_stake_pct"] > 0


def test_flashscore_validation_report_generated_offline_safe():
    report = validate_flashscore_provider(max_leagues=1, attempt_live=False)
    assert "success" in report
    assert report["uses_external_repo"] is False
    assert "playwright_available" in report
    assert "browser_available" in report
    assert report["leagues_tested"] >= 1
    assert (root() / "data/reports/flashscore_live_validation_report.json").exists()


def test_flashscore_validation_endpoint_reads_last_report():
    validate_flashscore_provider(max_leagues=1, attempt_live=False)
    client = TestClient(app)
    resp = client.get("/api/data-engine/providers/flashscore/validation", headers=_admin_headers_for_protected_data_engine(client))
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["ok"] is True
    assert payload["data"]["provider"] == "flashscore"
    assert payload["data"]["uses_external_repo"] is False
