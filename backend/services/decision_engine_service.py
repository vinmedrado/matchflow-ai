"""decision_engine_service.py v7.0 — expõe CLV, performance, action_required."""
from __future__ import annotations
import importlib.util, json, os
from pathlib import Path
import pandas as pd

def normalized_app_mode() -> str:
    raw = os.getenv("APP_MODE", "PAPER_TRADING_SIMULATION_ONLY").upper()
    if raw == "LIVE_RESEARCH":
        return "LIVE_RESEARCH"
    return "PAPER_TRADING_SIMULATION_ONLY"

MODE = normalized_app_mode()

def project_root() -> Path:
    return Path(__file__).resolve().parents[2]

def _json(path: Path, default=None) -> dict:
    if default is None: default = {}
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default
    except Exception:
        return default

def _csv(path: Path, limit: int = 200) -> list[dict]:
    if not path.exists() or path.stat().st_size == 0: return []
    try:
        df = pd.read_csv(path).head(limit).fillna("")
        return df.to_dict(orient="records")
    except Exception:
        return []


def _is_demo_presentation_mode() -> bool:
    mode = str(os.getenv("DATA_ENGINE_MODE", "")).strip().lower()
    return mode in {"demo", "presentation", "demo_presentation"} or os.getenv("FLASHSCORE_USE_DEMO", "false").strip().lower() in {"1", "true", "yes", "y", "on"} or os.getenv("MATCHFLOW_DEMO_PRESENTATION", "false").strip().lower() in {"1", "true", "yes", "y", "on"}


def _safe_float(value, default=0.0):
    try:
        if value is None or str(value).strip() == "":
            return default
        return float(value)
    except Exception:
        return default


def _sanitize_candidate_row(row: dict) -> dict:
    """Defensive API invariant for old CSV/parquet artifacts.

    Persisted artifacts from previous builds may contain rejected rows with
    positive sizing. The API must never expose those as actionable candidates.
    """
    if "suggested_allocation_pct" in row and "suggested_stake_pct" not in row:
        row["suggested_stake_pct"] = row.get("suggested_allocation_pct")
    if "suggested_allocation_amount" in row and "suggested_stake_amount" not in row:
        row["suggested_stake_amount"] = row.get("suggested_allocation_amount")
    if "suggested_stake_pct" in row and "suggested_allocation_pct" not in row:
        row["suggested_allocation_pct"] = row.get("suggested_stake_pct")
    if "suggested_stake_amount" in row and "suggested_allocation_amount" not in row:
        row["suggested_allocation_amount"] = row.get("suggested_stake_amount")
    if "kelly_allocation_pct" in row and "kelly_stake_pct" not in row:
        row["kelly_stake_pct"] = row.get("kelly_allocation_pct")

    status = str(row.get("decision_status") or row.get("confidence_band") or "").upper()
    band = str(row.get("confidence_band") or "").upper()
    rejected = status == "REJECTED" or band == "REJECTED"
    if rejected:
        for col in ("suggested_stake_pct", "suggested_stake_amount", "suggested_allocation_pct", "suggested_allocation_amount"):
            row[col] = 0.0
        row["decision_status"] = "REJECTED"
        row["confidence_band"] = "REJECTED"
        row["signal_label"] = "DEMO WATCHLIST" if _is_demo_presentation_mode() else "NO SIGNAL"
        row["action_required"] = False
        reason = "Rejected by Decision Engine safety gate; stake/allocation forced to zero."
        if row.get("why_selected"):
            if reason not in str(row.get("why_selected")):
                row["why_selected"] = f"{row.get('why_selected')} | {reason}"
        else:
            row["why_selected"] = reason
    if _is_demo_presentation_mode():
        row["app_mode"] = "PAPER_TRADING_SIMULATION_ONLY"
        row["is_demo_data"] = True
        row["demo_only"] = True
        row["action_required"] = False
        score = _safe_float(row.get("decision_score"), 0.0)
        visual_pct = min(max(score, 0.0), 100.0) / 10000.0
        row["demo_suggested_stake_pct"] = round(min(visual_pct, 0.005), 4)
        row["demo_suggested_stake_amount"] = round(row["demo_suggested_stake_pct"] * _safe_float(row.get("bankroll_reference"), 1000.0), 2)
        row["demo_signal_label"] = "DEMO WATCHLIST" if rejected else ("SIMULATION SIGNAL" if score >= 70 else "PAPER WATCHLIST")
        if rejected:
            row["signal_label"] = "DEMO WATCHLIST"
    return row

def run_decision_engine_service() -> dict:
    root = project_root()
    path = root / "09_decision_engine/decision_engine.py"
    spec = importlib.util.spec_from_file_location("mf_de", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.run_decision_engine(root)

def decision_summary() -> dict:
    root = project_root()
    summary = _json(root / "data/decision_engine/decision_summary.json")
    if not summary:
        summary = {"ok": True, "mode": MODE, "total_candidates": 0,
                   "warning": "Decision Engine ainda não executado."}
    summary["mode"] = MODE
    # Enriquecer com CLV e performance
    try:
        import sys
        sys.path.insert(0, str(root / "09_decision_engine"))
        from clv_tracker import get_clv_metrics
        summary["clv_metrics"] = get_clv_metrics(root)
    except Exception:
        pass
    try:
        perf = _json(root / "data/performance/performance_attribution.json")
        if perf:
            summary["performance"] = {
                "total_roi_pct": perf.get("total_roi_pct"),
                "win_rate": perf.get("win_rate"),
                "skill_roi_pct": perf.get("skill_component", {}).get("skill_roi_pct"),
                "edge_deteriorating": perf.get("edge_health", {}).get("edge_deteriorating"),
                "recommendation": perf.get("edge_health", {}).get("recommendation"),
            }
    except Exception:
        pass
    # Monte Carlo
    try:
        mc = _json(root / "data/performance/monte_carlo_report.json")
        if mc:
            summary["monte_carlo"] = {
                "median_6m": mc.get("projections", {}).get("p50_median"),
                "ruin_prob_pct": mc.get("risk", {}).get("ruin_probability_pct"),
                "prob_doubling_pct": round(mc.get("risk", {}).get("prob_doubling", 0) * 100, 1),
            }
    except Exception:
        pass
    return summary

def decision_candidates(limit: int = 100) -> dict:
    root = project_root()
    rows = _csv(root / "data/decision_engine/decision_candidates.csv", limit=limit)
    # CSV legacy fica sanitizado para testes antigos; API expõe aliases modernos.
    rows = [_sanitize_candidate_row(row) for row in rows]
    if rows and "kelly_stake_pct" in rows[0]:
        try:
            rows = sorted(rows, key=lambda r: float(r.get("kelly_stake_pct") or 0), reverse=True)
        except Exception:
            pass
    return {"ok": True, "mode": MODE, "total": len(rows), "candidates": rows}
