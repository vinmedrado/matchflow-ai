from __future__ import annotations
from typing import Any
import pandas as pd
from .config import get_flashscore_config, project_root
from .league_loader import load_leagues
from .scraper import scrape_league_matches
from .parser import parse_matches
from .quality_adapter import adapt_flashscore_quality
from .output_writer import write_outputs
from .state_manager import update_after_sync
from .coverage_report import build_flashscore_coverage_report


def run_flashscore_sync(project_root_arg=None, *, max_leagues: int | None = None, test_mode: bool | None = None) -> dict[str, Any]:
    cfg = get_flashscore_config()
    if not cfg.enabled:
        return {"ok": False, "provider": "flashscore", "status": "disabled", "warnings": ["FLASHSCORE_ENABLED=false"]}
    test = cfg.test_mode if test_mode is None else test_mode
    loaded = load_leagues(max_leagues=max_leagues if max_leagues is not None else cfg.max_leagues, test_mode=test)
    rows: list[dict[str, Any]] = []
    failed: list[str] = []
    failed_matches: list[str] = []
    network_capture_count = 0
    dom_fallback_count = 0
    parser_warning_count = 0
    endpoints_captured: list[dict[str, Any]] = []
    failed_urls: list[str] = []
    processed: list[str] = []
    warnings: list[str] = []
    for league in loaded["leagues"]:
        try:
            raw, scrape_warnings = scrape_league_matches(
                league,
                headless=cfg.headless,
                sleep_seconds=cfg.sleep_seconds,
                timeout_seconds=cfg.timeout_seconds,
                test_mode=test,
                use_demo=cfg.use_demo,
            )
            warnings.extend(scrape_warnings)
            rows.extend(parse_matches(raw))
            network_capture_count += sum(1 for w in scrape_warnings if "network_capture" in str(w))
            dom_fallback_count += sum(1 for r in raw if "dom_scrape" in str(r.get("provider_warnings", "")) or "text_parser" in str(r.get("provider_warnings", "")))
            parser_warning_count += sum(1 for r in raw if "missing" in str(r.get("provider_warnings", "")) or "fallback" in str(r.get("provider_warnings", "")))
            processed.append(league["league_slug"])
            if not raw and cfg.real_provider_enabled:
                failed.append(league.get("league_slug", "unknown"))
        except Exception as exc:
            failed.append(league.get("league_slug", "unknown"))
            warnings.append(f"flashscore_provider_exception:{type(exc).__name__}:{exc}")
    df = pd.DataFrame(rows)
    if not df.empty:
        from backend.services.data_engine.consolidation import canonicalize_matches
        df, consolidation = canonicalize_matches(df, project_root())
        df = adapt_flashscore_quality(df)
        if "final_data_quality_score" not in df.columns:
            df["final_data_quality_score"] = df.get("data_quality_score", 0.78)
        if "duplicate_status" not in df.columns:
            df["duplicate_status"] = "canonical"
        provider_status = "success"
        last_error = None
    else:
        consolidation = {"total_input": 0, "total_output": 0, "duplicates_removed": 0, "reason": "no_rows_from_real_provider" if cfg.real_provider_enabled else "no_rows"}
        provider_status = "empty_success" if cfg.use_demo else "real_provider_unavailable"
        last_error = None if cfg.use_demo else "Real FlashScore provider returned no rows; demo fallback is disabled by default. Set FLASHSCORE_USE_DEMO=true or DATA_ENGINE_MODE=demo for demo data."
        if last_error:
            warnings.append(last_error)
    report_payload = {
        "leagues": loaded,
        "consolidation": consolidation,
        "failed_leagues": failed,
        "real_provider_enabled": cfg.real_provider_enabled,
        "demo_enabled": cfg.use_demo,
        "field_availability": {},
        "leagues_requested": loaded["total"],
        "leagues_processed": len(processed),
        "leagues_failed": len(failed),
        "matches_found": len(rows),
        "matches_saved": int(len(df)) if not df.empty else 0,
        "matches_with_odds": int(df[[c for c in df.columns if c.startswith("odds_")]].notna().any(axis=1).sum()) if not df.empty and any(c.startswith("odds_") for c in df.columns) else 0,
        "matches_with_stats": int(df[[c for c in ["corners_home","shots_home","shots_on_target_home","xg_home"] if c in df.columns]].notna().any(axis=1).sum()) if not df.empty and any(c in df.columns for c in ["corners_home","shots_home","shots_on_target_home","xg_home"]) else 0,
        "matches_with_events": int(df[[c for c in ["goal_minutes_home","goal_minutes_away"] if c in df.columns]].notna().any(axis=1).sum()) if not df.empty and any(c in df.columns for c in ["goal_minutes_home","goal_minutes_away"]) else 0,
        "missing_match_id_count": int(df["flashscore_match_id"].astype(str).str.startswith("fallback_").sum()) if not df.empty and "flashscore_match_id" in df.columns else 0,
        "dom_fallback_count": dom_fallback_count,
        "network_capture_count": network_capture_count,
        "parser_warning_count": parser_warning_count,
        "low_quality_count": int((df.get("final_data_quality_score", df.get("data_quality_score", 1.0)).fillna(0) < 0.6).sum()) if not df.empty else 0,
        "provider_health": "healthy" if not failed and rows else ("demo" if cfg.use_demo else "degraded" if warnings else "unavailable"),
        "fallback_used": "demo" if cfg.use_demo else None,
        "endpoints_captured": endpoints_captured,
        "failed_urls": failed_urls,
        "retry_summary": {"failed_leagues": failed, "failed_matches": failed_matches},
    }
    if not df.empty:
        tracked = ["odds_home", "odds_over_25", "odds_btts_yes", "corners_home", "shots_home", "shots_on_target_home", "xg_home"]
        report_payload["field_availability"] = {col: int(df[col].notna().sum()) if col in df.columns else 0 for col in tracked}
        report_payload["missing_fields"] = {col: int(df[col].isna().sum()) if col in df.columns else int(len(df)) for col in tracked}
    output = write_outputs(df, report_payload)
    coverage = build_flashscore_coverage_report(project_root())
    output["coverage_report"] = coverage
    state = update_after_sync(
        processed_leagues=processed,
        processed_matches=df.get("match_id", pd.Series(dtype=str)).astype(str).tolist() if not df.empty else [],
        failed_leagues=failed,
        test_mode=test,
        batch_size=cfg.batch_size,
        start_date=cfg.start_date,
        end_date=cfg.end_date,
        mode="demo" if cfg.use_demo else cfg.data_engine_mode,
        provider_status=provider_status,
        last_error=last_error,
        failed_matches=failed_matches,
        provider_health=report_payload.get("provider_health"),
    )
    output.update({
        "state": state,
        "configured_leagues_count": loaded["total"],
        "internal_mode": cfg.data_engine_mode == "internal",
        "real_provider_enabled": cfg.real_provider_enabled,
        "demo_enabled": cfg.use_demo,
        "is_using_external_repo": False,
        "warnings": loaded.get("warnings", []) + sorted(set(warnings)),
    })
    return output
