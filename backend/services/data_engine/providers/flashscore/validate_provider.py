from __future__ import annotations

import importlib.util
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .league_loader import load_leagues
from .config import get_flashscore_config, project_root

REPORT_RELATIVE_PATH = Path("data/reports/flashscore_live_validation_report.json")


def _playwright_available() -> bool:
    return importlib.util.find_spec("playwright") is not None


def _browser_available() -> tuple[bool, list[str]]:
    warnings: list[str] = []
    if not _playwright_available():
        return False, ["Playwright Python package is not installed. Run: pip install playwright"]
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        return True, warnings
    except Exception as exc:  # pragma: no cover - environment-specific
        warnings.append(f"Chromium browser is not available or cannot launch: {exc}")
        warnings.append("Install browser dependencies with: python -m playwright install chromium")
        return False, warnings


def _safe_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def validate_flashscore_provider(max_leagues: int = 1, attempt_live: bool | None = None) -> dict[str, Any]:
    """Validate the real FlashScore provider without running the full pipeline.

    The default is safe/offline-friendly: it verifies configuration, Playwright
    package, browser availability and league loading. A live network probe only
    runs when MATCHFLOW_FLASH_SCORE_VALIDATE_LIVE=1 or attempt_live=True.
    """
    root = project_root()
    cfg = get_flashscore_config()
    warnings: list[str] = []
    errors: list[str] = []
    leagues_payload = load_leagues(max_leagues=max_leagues, test_mode=True)
    leagues = leagues_payload.get("leagues", [])[:max_leagues]
    playwright_ok = _playwright_available()
    browser_ok, browser_warnings = _browser_available()
    warnings.extend(browser_warnings)
    network_responses = 0
    matches_found = 0
    dom_fallback_used = False

    if attempt_live is None:
        attempt_live = os.getenv("MATCHFLOW_FLASH_SCORE_VALIDATE_LIVE", "false").lower() in {"1", "true", "yes", "y", "on"}

    if attempt_live and browser_ok and leagues:
        try:  # pragma: no cover - external network/browser dependent
            from playwright.sync_api import sync_playwright  # type: ignore
            target = "https://www.flashscore.com/football/"
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=cfg.headless)
                page = browser.new_page()
                page.on("response", lambda response: None)
                captured: list[str] = []
                page.on("response", lambda response: captured.append(response.url) if "flashscore" in response.url.lower() or "x/feed" in response.url.lower() else None)
                page.goto(target, wait_until="domcontentloaded", timeout=max(10000, cfg.timeout_seconds * 1000))
                page.wait_for_timeout(1500)
                network_responses = len(captured)
                try:
                    matches_found = page.locator("[id^='g_1_'], .event__match").count()
                    dom_fallback_used = matches_found > 0 and network_responses == 0
                except Exception:
                    dom_fallback_used = True
                browser.close()
        except Exception as exc:
            errors.append(f"live_probe_failed:{exc}")
    elif not attempt_live:
        warnings.append("Live network probe skipped. Set MATCHFLOW_FLASH_SCORE_VALIDATE_LIVE=1 to test real FlashScore access.")
    elif not leagues:
        errors.append("No configured leagues available for validation.")

    offline_ready = bool(playwright_ok and leagues and not errors)
    live_probe_executed = bool(attempt_live and browser_ok and leagues and not errors)
    success = bool(offline_ready and (not attempt_live or live_probe_executed))
    provider_health = "live_probe_ok" if live_probe_executed and success else ("not_validated" if not attempt_live else "needs_attention")
    severity = "info" if live_probe_executed and success else ("warning" if not attempt_live else "error")
    report = {
        "success": success,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider": "flashscore",
        "provider_health": provider_health,
        "severity": severity,
        "offline_ready": offline_ready,
        "playwright_available": playwright_ok,
        "browser_available": browser_ok,
        "leagues_tested": len(leagues),
        "leagues_sample": leagues,
        "matches_found": matches_found,
        "network_responses_captured": network_responses,
        "dom_fallback_used": dom_fallback_used,
        "live_probe_attempted": bool(attempt_live),
        "live_probe_executed": live_probe_executed,
        "uses_external_repo": False,
        "errors": errors,
        "warnings": warnings + leagues_payload.get("warnings", []),
        "next_steps": [
            "Run: python -m playwright install chromium" if not browser_ok else "Browser check passed.",
            "Set MATCHFLOW_FLASH_SCORE_VALIDATE_LIVE=1 to perform a real network probe." if not attempt_live else "Review matches_found and network_responses_captured.",
            "Then run DATA_ENGINE_MODE=internal FLASHSCORE_USE_DEMO=false python run_full_decision_pipeline.py for full production validation.",
        ],
    }
    _safe_write_json(root / REPORT_RELATIVE_PATH, report)
    return report


def main() -> int:
    report = validate_flashscore_provider()
    import sys
    sys.stdout.write(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
