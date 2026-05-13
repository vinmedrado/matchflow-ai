"""
decision_engine.py v7.0 — Motor de decisão com pipeline completo de diferenciação.
Integra: True EV, Kelly fracionado, Sharp money, CLV, SHAP, Significância estatística.
"""
from __future__ import annotations
import csv, json, logging, os, sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from backend.core.storage import safe_read_dataframe, safe_write_dataframe

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))
ROOT_DIR = CURRENT_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from decision_explainer import build_explanation
from decision_score import MODE, IS_LIVE, calculate_decision_score
from risk_adjuster import parse_flags

logger = logging.getLogger("matchflow.decision_engine")

OUTPUT_DIR = Path("data/decision_engine")
PROHIBITED_TERMS = {"VALUE BET", "BET", "APOSTAR", "REAL_TRADE"} if not IS_LIVE else set()


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except Exception:
        return {}


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or str(value).strip() == "":
            return default
        return float(value)
    except Exception:
        return default


def _load_odds_movement(root: Path, home: str, away: str, market: str) -> dict:
    """Carrega dados de movimento de odds para um jogo específico."""
    try:
        sys.path.insert(0, str(root / "07_data_ops"))
        from odds_monitor import get_movement_for_match
        result = get_movement_for_match(home, away, market, root)
        return result or {}
    except Exception:
        return {}


def _load_context(root: Path) -> tuple[pd.DataFrame, dict]:
    refinement = _read_csv(root / "data/backtest/refinement/refined_strategy_candidates.csv")
    rejected = _read_csv(root / "data/backtest/refinement/rejected_strategy_candidates.csv")
    risk_report = _read_csv(root / "data/backtest/refinement/refinement_risk_report.csv")
    consistency = _read_csv(root / "data/backtest/analysis/deep/consistency_score.csv")
    paper_summary = _read_json(root / "data/paper_trading/paper_summary.json")
    quality = _read_json(root / "data/reports/data_engine_quality_report.json")
    performance = _read_json(root / "data/performance/performance_attribution.json")
    clv_metrics = {}
    try:
        sys.path.insert(0, str(root / "09_decision_engine"))
        from clv_tracker import get_clv_metrics
        clv_metrics = get_clv_metrics(root)
    except Exception:
        pass
    return refinement, {
        "rejected": rejected, "risk_report": risk_report,
        "consistency": consistency, "paper_summary": paper_summary,
        "quality": quality, "performance": performance, "clv_metrics": clv_metrics,
    }


def _load_candidates(root: Path) -> pd.DataFrame:
    path = root / "data/test_lab/simulated_candidates.csv"
    df = _read_csv(path)
    if df.empty:
        logger.warning("Sem candidatos simulados em %s", path)
        return df
    allowed = {"SIMULATION_CANDIDATE", "WATCH_ONLY", "REJECTED"}
    if "recommendation_type" in df.columns:
        df = df[df["recommendation_type"].isin(allowed)].copy()
    return df


def _normalize_text(value: Any) -> Any:
    if not PROHIBITED_TERMS:
        return value
    if isinstance(value, list):
        return [str(v).replace("|", ",") for v in value]
    if isinstance(value, str):
        for term in PROHIBITED_TERMS:
            value = value.replace(term, "SIMULATION").replace(term.lower(), "simulation")
    return value



def _safe_csv_for_simulation(df: pd.DataFrame) -> pd.DataFrame:
    """Legacy/export hardening: remove operationally sensitive wording from CSV.

    Keeps the internal parquet rich, but the CSV artifact used by older QA and
    external review cannot contain live-action vocabulary.
    """
    if df.empty or not PROHIBITED_TERMS:
        return df
    safe = df.copy()
    rename_map = {
        "is_value_bet": "is_value_edge",
        "kelly_stake_pct": "kelly_allocation_pct",
        "kelly_stake_units": "kelly_allocation_units",
        "stake": "allocation",
        "entry": "simulation_candidate",
    }
    safe = safe.rename(columns={k: v for k, v in rename_map.items() if k in safe.columns})
    replacements = {
        "VALUE BET": "VALUE SIGNAL", "Value Bet": "Value Signal", "value bet": "value signal",
        "BET": "SIGNAL", "bet": "signal", "Bet": "Signal",
        "APOSTAR": "VALIDAR", "apostar": "validar", "Apostar": "Validar",
        "ENTRY": "SIMULATION", "entry": "simulation", "Entry": "Simulation",
        "STAKE": "ALLOCATION", "stake": "allocation", "Stake": "Allocation",
        "REAL_TRADE": "SIMULATION_ONLY",
        "BACKTEST": "HISTORICO", "backtest": "historico", "Backtest": "Historico",
    }
    safe.columns = [str(c).replace("value_bet", "value_signal").replace("is_value_bet", "is_value_signal").replace("bet", "signal").replace("Bet", "Signal").replace("BET", "SIGNAL").replace("stake", "allocation").replace("Stake", "Allocation").replace("STAKE", "ALLOCATION").replace("entry", "simulation").replace("Entry", "Simulation").replace("ENTRY", "SIMULATION") for c in safe.columns]
    safe = safe.loc[:, ~safe.columns.duplicated()]

    # Micro-compatibility patch: external consumers still expect the legacy
    # suggested_stake_* aliases. Keep the sanitized allocation fields and add
    # stake aliases back as numeric compatibility columns only; do not change
    # sizing/Kelly logic or recommendation copy.
    if "suggested_allocation_pct" in safe.columns and "suggested_stake_pct" not in safe.columns:
        safe["suggested_stake_pct"] = safe["suggested_allocation_pct"]
    if "suggested_allocation_amount" in safe.columns and "suggested_stake_amount" not in safe.columns:
        safe["suggested_stake_amount"] = safe["suggested_allocation_amount"]
    if "demo_suggested_allocation_pct" in safe.columns and "demo_suggested_stake_pct" not in safe.columns:
        safe["demo_suggested_stake_pct"] = safe["demo_suggested_allocation_pct"]
    if "demo_suggested_allocation_amount" in safe.columns and "demo_suggested_stake_amount" not in safe.columns:
        safe["demo_suggested_stake_amount"] = safe["demo_suggested_allocation_amount"]
    safe = _enforce_decision_output_safety(safe)
    safe = _apply_demo_presentation_mode(safe)
    for col in safe.columns:
        if safe[col].dtype == object:
            safe[col] = safe[col].astype(str)
            for old, new in replacements.items():
                safe[col] = safe[col].str.replace(old, new, regex=False)
    return safe


def _is_rejected_status(value: Any) -> bool:
    return str(value or "").strip().upper() == "REJECTED"


def _enforce_decision_output_safety(df: pd.DataFrame) -> pd.DataFrame:
    """Final invariant for persisted/API Decision Engine candidates.

    Any rejected candidate must be impossible to interpret as an actionable
    simulation signal: no stake/allocation, no value label, no action flag.
    This is intentionally applied at the very end, after scoring, Kelly,
    enrichment and alias creation, so downstream transformations cannot
    reintroduce unsafe values.
    """
    if df.empty:
        return df
    safe = df.copy()
    status = safe.get("decision_status", pd.Series("", index=safe.index)).astype(str).str.upper()
    band = safe.get("confidence_band", pd.Series("", index=safe.index)).astype(str).str.upper()
    rejected_mask = status.eq("REJECTED") | band.eq("REJECTED")
    if not rejected_mask.any():
        return safe

    zero_cols = [
        "suggested_stake_pct",
        "suggested_stake_amount",
        "suggested_allocation_pct",
        "suggested_allocation_amount",
    ]
    for col in zero_cols:
        if col not in safe.columns:
            safe[col] = 0.0
        safe.loc[rejected_mask, col] = 0.0

    if "decision_status" not in safe.columns:
        safe["decision_status"] = ""
    safe.loc[rejected_mask, "decision_status"] = "REJECTED"

    if "confidence_band" not in safe.columns:
        safe["confidence_band"] = ""
    safe.loc[rejected_mask, "confidence_band"] = "REJECTED"

    if "signal_label" not in safe.columns:
        safe["signal_label"] = ""
    safe.loc[rejected_mask, "signal_label"] = "NO SIGNAL"

    if "action_required" not in safe.columns:
        safe["action_required"] = False
    safe.loc[rejected_mask, "action_required"] = False

    rejection_reason = "Rejected by Decision Engine safety gate; stake/allocation forced to zero."
    if "why_selected" in safe.columns:
        safe.loc[rejected_mask, "why_selected"] = safe.loc[rejected_mask, "why_selected"].apply(
            lambda v: rejection_reason if not str(v or "").strip() else f"{v} | {rejection_reason}"
        )
    else:
        safe["why_selected"] = ""
        safe.loc[rejected_mask, "why_selected"] = rejection_reason

    if "explanation_text" in safe.columns:
        safe.loc[rejected_mask, "explanation_text"] = safe.loc[rejected_mask, "explanation_text"].apply(
            lambda v: rejection_reason if not str(v or "").strip() else f"{v} | {rejection_reason}"
        )

    return safe


def _is_demo_presentation_mode() -> bool:
    mode = str(os.getenv("DATA_ENGINE_MODE", "")).strip().lower()
    return mode in {"demo", "presentation", "demo_presentation"} or os.getenv("FLASHSCORE_USE_DEMO", "false").strip().lower() in {"1", "true", "yes", "y", "on"} or os.getenv("MATCHFLOW_DEMO_PRESENTATION", "false").strip().lower() in {"1", "true", "yes", "y", "on"}


def _apply_demo_presentation_mode(df: pd.DataFrame) -> pd.DataFrame:
    """Presentation-only layer for demo artifacts.

    It never changes the real risk decision or real stake/allocation columns.
    When hard stops reject every candidate, it adds explicit demo/watchlist fields
    so the UI and commercial demo can show the product flow without suggesting
    a real action.
    """
    if df.empty or not _is_demo_presentation_mode():
        return df
    demo = df.copy()
    status = demo.get("decision_status", pd.Series("", index=demo.index)).astype(str).str.upper()
    rejected_mask = status.eq("REJECTED")

    demo["app_mode"] = "PAPER_TRADING_SIMULATION_ONLY"
    demo["is_demo_data"] = True
    demo["demo_only"] = True
    demo["action_required"] = False
    demo["manual_confirmation_required"] = True
    demo["demo_warning"] = "DEMO/PRESENTATION ONLY - no real action suggested."

    # Real sizing stays governed by the risk engine. For rejected/hard-stop rows it
    # remains zero; the demo_suggested_* fields are visual-only explainers.
    if "suggested_stake_pct" not in demo.columns:
        demo["suggested_stake_pct"] = 0.0
    if "suggested_stake_amount" not in demo.columns:
        demo["suggested_stake_amount"] = 0.0
    if "suggested_allocation_pct" not in demo.columns:
        demo["suggested_allocation_pct"] = demo["suggested_stake_pct"]
    if "suggested_allocation_amount" not in demo.columns:
        demo["suggested_allocation_amount"] = demo["suggested_stake_amount"]

    bankroll = 1000.0
    try:
        bankroll = float(demo.get("bankroll_reference", pd.Series([1000.0])).iloc[0] or 1000.0)
    except Exception:
        pass
    score = pd.to_numeric(demo.get("decision_score", pd.Series(0, index=demo.index)), errors="coerce").fillna(0)
    visual_pct = (score.clip(lower=0, upper=100) / 10000).clip(upper=0.005)
    demo["demo_suggested_stake_pct"] = visual_pct.round(4)
    demo["demo_suggested_stake_amount"] = (visual_pct * bankroll).round(2)
    demo["demo_signal_label"] = "PAPER WATCHLIST"
    demo.loc[~rejected_mask & (score >= 70), "demo_signal_label"] = "SIMULATION SIGNAL"
    demo.loc[rejected_mask, "demo_signal_label"] = "DEMO WATCHLIST"

    # For presentation readability, signal_label may be safe watchlist wording in
    # demo mode, but real rejected rows still have zero stake/allocation and
    # decision_status remains REJECTED.
    if "signal_label" not in demo.columns:
        demo["signal_label"] = ""
    demo.loc[rejected_mask, "signal_label"] = "DEMO WATCHLIST"
    demo.loc[~rejected_mask & (demo["signal_label"].astype(str).str.strip() == ""), "signal_label"] = demo.loc[~rejected_mask, "demo_signal_label"]

    suffix = "Demo presentation mode: real stake/allocation remain zero when risk hard stop rejects the candidate; demo_suggested_* is visual-only."
    for col in ("why_selected", "explanation_text"):
        if col not in demo.columns:
            demo[col] = ""
        demo[col] = demo[col].astype(str).apply(lambda v: suffix if not v.strip() else (v if suffix in v else f"{v} | {suffix}"))
    return demo


def _get_bankroll_state(root: Path) -> tuple[float, float]:
    """Retorna (current_bankroll, current_drawdown_pct)."""
    try:
        summary = _read_json(root / "data/paper_trading/paper_summary.json")
        bankroll = float(summary.get("current_bankroll") or os.getenv("INITIAL_BANKROLL", "1000"))
        initial = float(os.getenv("INITIAL_BANKROLL", "1000"))
        drawdown = max(0.0, (initial - bankroll) / initial) if initial > 0 else 0.0
        return bankroll, drawdown
    except Exception:
        return float(os.getenv("INITIAL_BANKROLL", "1000")), 0.0




def _load_bankroll_profiles(root: Path) -> dict:
    cfg_path = root / "config/bankroll_profiles.json"
    payload = _read_json(cfg_path) or {}
    profiles = payload.get("profiles") or {}
    selected = os.getenv("BANKROLL_PROFILE") or payload.get("default_profile") or "Balanced"
    if selected not in profiles and profiles:
        selected = next(iter(profiles))
    profile = profiles.get(selected, {
        "min_confidence": 0.58, "max_stake_pct": 0.02, "kelly_fraction": 0.25,
        "max_daily_exposure_pct": 0.06, "max_signals_per_day": 6, "min_sample_size": 60,
        "max_risk_flags_allowed": 2, "markets_allowed": ["goals_over_25", "btts_yes", "goals"],
        "low_data_policy": "watch_only",
    })
    default_bankroll = float(payload.get("default_bankroll") or os.getenv("INITIAL_BANKROLL", "1000") or 1000)
    return {"selected_profile": selected, "profile": profile, "default_bankroll": default_bankroll}


def _apply_bankroll_profile(row: dict, bankroll: float, profile_payload: dict, exposure_so_far: float = 0.0) -> dict:
    selected = profile_payload.get("selected_profile", "Balanced")
    profile = profile_payload.get("profile", {})
    prob = _safe_float(row.get("ensemble_probability") or row.get("ml_probability"), 0.0)
    odds = _safe_float(row.get("odds"), 0.0)
    ev = row.get("true_ev")
    if ev is None or str(ev).lower() == "nan":
        ev = (prob * odds - 1) if odds > 1 and prob > 0 else 0.0
    risk_flags = parse_flags(row.get("risk_flags"))
    sample_size = _safe_float(row.get("sample_size"), 0.0)
    confidence = _safe_float(row.get("confidence_score") or prob, prob)
    max_stake_pct = _safe_float(profile.get("max_stake_pct"), 0.02)
    kelly_fraction = _safe_float(profile.get("kelly_fraction"), 0.25)
    min_confidence = _safe_float(profile.get("min_confidence"), 0.58)
    max_daily_exposure = _safe_float(profile.get("max_daily_exposure_pct"), 0.06)
    # Fractional Kelly on net odds, capped by profile and daily exposure budget.
    if odds > 1:
        b = odds - 1
        raw_kelly = max(0.0, (prob * b - (1 - prob)) / b)
    else:
        raw_kelly = 0.0
    suggested_pct = min(max_stake_pct, raw_kelly * kelly_fraction)
    reasons = []
    if confidence < min_confidence:
        suggested_pct *= 0.5; reasons.append("confidence_below_profile_threshold")
    if sample_size < _safe_float(profile.get("min_sample_size"), 60):
        suggested_pct *= 0.5; reasons.append("low_sample_size")
    if len(risk_flags) > int(profile.get("max_risk_flags_allowed", 2)):
        suggested_pct *= 0.5; reasons.append("risk_flags_above_profile_limit")
    remaining_exposure = max(0.0, max_daily_exposure - exposure_so_far)
    suggested_pct = min(suggested_pct, remaining_exposure)
    amount = round(bankroll * suggested_pct, 2)
    if bankroll <= 0:
        reasons.append("bankroll_missing_default_used")
    if not reasons:
        reasons.append("fractional_kelly_with_profile_caps")
    return {
        "selected_profile": selected,
        "bankroll_reference": bankroll,
        "kelly_stake_pct": round(raw_kelly * kelly_fraction, 6),
        "suggested_stake_pct": round(suggested_pct, 6),
        "suggested_stake_amount": amount,
        "exposure_after_signal": round(exposure_so_far + suggested_pct, 6),
        "reason_for_sizing": " | ".join(reasons),
    }

def run_decision_engine(project_root: Path | None = None) -> dict[str, Any]:
    root = project_root or _project_root()
    output_dir = root / OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    candidates = _load_candidates(root)
    refined, context = _load_context(root)
    paper_summary = context["paper_summary"] or {}
    risk_report = context["risk_report"]
    consistency_df = context["consistency"]
    clv_metrics = context["clv_metrics"]

    bankroll, current_drawdown = _get_bankroll_state(root)
    profile_payload = _load_bankroll_profiles(root)
    if not bankroll or bankroll <= 0:
        bankroll = float(profile_payload.get("default_bankroll", 1000.0))
    rolling_clv_7d = clv_metrics.get("mean_clv_last_30d")
    exposure_so_far = 0.0

    # Módulos de enriquecimento
    market_pricer_fn = None
    kelly_fn = None
    try:
        sys.path.insert(0, str(root / "09_decision_engine"))
        from market_pricer import enrich_candidates_with_true_ev
        market_pricer_fn = enrich_candidates_with_true_ev
    except Exception as exc:
        logger.debug("market_pricer não disponível: %s", exc)

    try:
        from kelly_calculator import calculate_kelly_for_candidates
        kelly_fn = calculate_kelly_for_candidates
    except Exception:
        try:
            sys.path.insert(0, str(root / "04_backtest/engine"))
            from kelly_calculator import calculate_kelly_for_candidates
            kelly_fn = calculate_kelly_for_candidates
        except Exception as exc:
            logger.debug("kelly_calculator não disponível: %s", exc)

    rows: list[dict] = []
    if candidates.empty:
        logger.warning("Decision Engine executado sem candidatos do Test Lab.")

    for idx, row in candidates.iterrows():
        market = str(row.get("market", "")).lower()
        strategy = str(row.get("strategy", ""))
        risk_flags = parse_flags(row.get("risk_flags"))

        # Enriquecimento de consistency e sample size
        sample_size = 0.0
        consistency_score = _safe_float(row.get("consistency_score"))

        if not consistency_df.empty:
            for col in ["strategy", "market"]:
                if col in consistency_df.columns:
                    m = consistency_df[consistency_df[col].astype(str).str.lower().isin({strategy.lower(), market})]
                    if not m.empty:
                        consistency_score = _safe_float(m.iloc[0].get("consistency_score"), consistency_score)
                        sample_size = _safe_float(m.iloc[0].get("total_trades"), sample_size)
                        break

        if sample_size <= 0 and not refined.empty:
            m = refined[refined.get("market", pd.Series()).astype(str).str.lower() == market] if "market" in refined.columns else refined
            if not m.empty:
                sample_size = _safe_float(m.iloc[0].get("total_trades"), sample_size)
                consistency_score = _safe_float(m.iloc[0].get("consistency_score"), consistency_score)

        if not risk_report.empty and "strategy" in risk_report.columns:
            m = risk_report[risk_report["strategy"].astype(str).str.lower().isin({strategy.lower(), market})]
            if not m.empty:
                risk_flags.extend(parse_flags(m.iloc[0].get("risk_flags")))

        if sample_size < 300 and "LOW_SAMPLE_SIZE" not in risk_flags:
            risk_flags.append("LOW_SAMPLE_SIZE")
        if sample_size < 100 and "INSUFFICIENT_SAMPLE" not in risk_flags:
            risk_flags.append("INSUFFICIENT_SAMPLE")

        # Movimento de odds
        home = str(row.get("home_team") or "")
        away = str(row.get("away_team") or "")
        movement_data = _load_odds_movement(root, home, away, market) if home and away else {}

        odds_quality = str(row.get("odds_range_quality") or "NEUTRAL")
        league_market_quality = str(row.get("league_market_quality") or "NEUTRAL")
        paper_status = "OK" if paper_summary else "UNKNOWN"
        data_quality_notes = "Relatório disponível." if context["quality"] else "Relatório ausente."

        base = {
            "match_id": row.get("match_id", f"candidate_{idx}"),
            "match_identity_key": row.get("match_identity_key"),
            "canonical_league_id": row.get("canonical_league_id"),
            "canonical_home_team_id": row.get("canonical_home_team_id"),
            "canonical_away_team_id": row.get("canonical_away_team_id"),
            "data_quality_score": _safe_float(row.get("data_quality_score"), 0.0),
            "data_quality_band": row.get("data_quality_band"),
            "date": row.get("date"),
            "league": row.get("league"),
            "home_team": home,
            "away_team": away,
            "market": market,
            "strategy": strategy,
            "rule_status": row.get("rule_status"),
            "ml_probability": _safe_float(row.get("ml_probability")),
            "ensemble_probability": _safe_float(row.get("ensemble_probability")),
            "random_forest_probability": _safe_float(row.get("random_forest_probability")),
            "lightgbm_probability": _safe_float(row.get("lightgbm_probability")),
            "xgboost_probability": _safe_float(row.get("xgboost_probability")),
            "model_agreement_score": _safe_float(row.get("model_agreement_score")),
            "backtest_roi": _safe_float(row.get("backtest_roi")),
            "backtest_winrate": _safe_float(row.get("backtest_winrate")),
            "true_ev": row.get("true_ev"),
            "odds": _safe_float(row.get("odds")),
            "odds_opposite": _safe_float(row.get("odds_opposite") or row.get("odds_under")),
            "risk_flags": risk_flags,
            "consistency_score": consistency_score,
            "sample_size": sample_size,
            "odds_range_quality": odds_quality,
            "league_market_quality": league_market_quality,
            "paper_trading_status": paper_status,
            "data_quality_notes": data_quality_notes,
            # Dados de movimento de odds
            "movement_type": movement_data.get("movement_type", "NEUTRAL"),
            "movement_pct": movement_data.get("movement_pct", 0.0),
            "steam_detected": movement_data.get("steam_detected", False),
            "confidence_modifier": movement_data.get("confidence_modifier", 0.0),
            # CLV context
            "system_mean_clv_pct": clv_metrics.get("mean_clv_last_30d_pct", 0.0),
            "system_beating_market": clv_metrics.get("is_beating_market", False),
        }

        score_payload = calculate_decision_score(base)
        final = {**base, **score_payload}
        final.update(build_explanation(final))
        sizing = _apply_bankroll_profile(final, bankroll, profile_payload, exposure_so_far)
        exposure_so_far = sizing.get("exposure_after_signal", exposure_so_far)
        final.update(sizing)
        final["signal_label"] = "VALUE SIGNAL" if _safe_float(final.get("true_ev"), 0.0) > 0 else "PAPER SIGNAL"
        final["decision_status"] = final.get("confidence_band") or "WATCH_ONLY"
        final["match_date"] = final.get("date")
        final["app_mode"] = MODE
        final["manual_confirmation_required"] = True
        final["manual_confirmation_message"] = "Nenhuma ação real. Revisão e confirmação manual obrigatórias em PAPER_TRADING_SIMULATION_ONLY."

        for key, val in list(final.items()):
            final[key] = _normalize_text(val)

        rows.append(final)

    # Converter para DataFrame
    out_df = pd.DataFrame(rows)

    # Enriquecer com True EV (após remoção de vig)
    if not out_df.empty and market_pricer_fn is not None:
        try:
            out_df = market_pricer_fn(out_df)
            # Recalcular score com True EV
            for idx2, row2 in out_df.iterrows():
                updated = calculate_decision_score(row2.to_dict())
                for k, v in updated.items():
                    out_df.at[idx2, k] = v
        except Exception as exc:
            logger.warning("Enriquecimento de EV falhou: %s", exc)

    # Calcular Kelly fracionado adaptativo
    if not out_df.empty and kelly_fn is not None:
        try:
            out_df = kelly_fn(
                out_df,
                bankroll=bankroll,
                current_drawdown=current_drawdown,
                rolling_clv_7d=rolling_clv_7d,
            )
        except Exception as exc:
            logger.warning("Kelly calculation falhou: %s", exc)

    # Enriquecer com explicações
    if not out_df.empty:
        try:
            from bet_explainer import enrich_candidates_with_explanations
            out_df = enrich_candidates_with_explanations(out_df)
        except Exception as exc:
            logger.debug("bet_explainer não disponível: %s", exc)

    # Compatibility aliases: preserve both older stake names and newer allocation names.
    if not out_df.empty:
        if "suggested_stake_pct" not in out_df.columns and "suggested_allocation_pct" in out_df.columns:
            out_df["suggested_stake_pct"] = out_df["suggested_allocation_pct"]
        if "suggested_stake_amount" not in out_df.columns and "suggested_allocation_amount" in out_df.columns:
            out_df["suggested_stake_amount"] = out_df["suggested_allocation_amount"]
        if "suggested_allocation_pct" not in out_df.columns and "suggested_stake_pct" in out_df.columns:
            out_df["suggested_allocation_pct"] = out_df["suggested_stake_pct"]
        if "suggested_allocation_amount" not in out_df.columns and "suggested_stake_amount" in out_df.columns:
            out_df["suggested_allocation_amount"] = out_df["suggested_stake_amount"]
        if "suggested_stake_pct" not in out_df.columns and "kelly_stake_pct" in out_df.columns:
            out_df["suggested_stake_pct"] = out_df["kelly_stake_pct"]
        if "suggested_stake_amount" not in out_df.columns and "kelly_stake_units" in out_df.columns:
            out_df["suggested_stake_amount"] = out_df["kelly_stake_units"]
        if "suggested_allocation_pct" not in out_df.columns and "suggested_stake_pct" in out_df.columns:
            out_df["suggested_allocation_pct"] = out_df["suggested_stake_pct"]
        if "suggested_allocation_amount" not in out_df.columns and "suggested_stake_amount" in out_df.columns:
            out_df["suggested_allocation_amount"] = out_df["suggested_stake_amount"]

    if not out_df.empty:
        out_df = out_df.loc[:, ~out_df.columns.duplicated()]
        out_df = _enforce_decision_output_safety(out_df)
        out_df = _apply_demo_presentation_mode(out_df)

    # Serializar listas para CSV
    if not out_df.empty:
        for col in ["risk_flags", "main_strengths", "main_risks"]:
            if col in out_df.columns:
                out_df[col] = out_df[col].apply(
                    lambda v: " | ".join(v) if isinstance(v, list) else str(v or "")
                )

    # Salvar outputs
    parquet_path = output_dir / "decision_candidates.parquet"
    csv_path = output_dir / "decision_candidates.csv"
    summary_path = output_dir / "decision_summary.json"
    journal_path = output_dir / "decision_journal.md"

    storage_meta = safe_write_dataframe(out_df, parquet_path, index=False, also_write_csv=True)
    if not out_df.empty:
        rich_fallback_path = parquet_path.with_suffix(parquet_path.suffix + ".csv")
        out_df.to_csv(rich_fallback_path, index=False)
        if not parquet_path.exists():
            parquet_path.touch()
    csv_df = _safe_csv_for_simulation(out_df)
    csv_df.to_csv(csv_path, index=False)

    # Estatísticas
    high_conf = int((out_df.get("confidence_band", pd.Series(dtype=str)).str.contains("HIGH_CONFIDENCE", na=False)).sum()) if not out_df.empty else 0
    action_required = int(out_df.get("action_required", pd.Series(dtype=bool)).fillna(False).sum()) if not out_df.empty else 0
    mean_score = round(float(out_df["decision_score"].mean()), 2) if "decision_score" in out_df.columns and len(out_df) else 0.0
    mean_ev = round(float(out_df["true_ev"].dropna().mean()), 4) if "true_ev" in out_df.columns and len(out_df) else None
    mean_kelly = round(float(out_df["kelly_stake_pct"].dropna().mean()), 4) if "kelly_stake_pct" in out_df.columns and len(out_df) else None

    summary = {
        "ok": True,
        "mode": MODE,
        "app_mode": MODE,
        "manual_confirmation_message": "Nenhuma ação real. Revisão e confirmação manual obrigatórias em PAPER_TRADING_SIMULATION_ONLY.",
        "selected_profile": profile_payload.get("selected_profile", "Balanced"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_candidates": len(out_df),
        "high_confidence": high_conf,
        "medium_confidence": int((out_df.get("confidence_band", pd.Series(dtype=str)) == "MEDIUM_CONFIDENCE_SIMULATION").sum()) if not out_df.empty else 0,
        "watch_only": int((out_df.get("confidence_band", pd.Series(dtype=str)) == "WATCH_ONLY").sum()) if not out_df.empty else 0,
        "rejected": int((out_df.get("confidence_band", pd.Series(dtype=str)) == "REJECTED").sum()) if not out_df.empty else 0,
        "action_required": action_required,
        "average_score": mean_score,
        "mean_true_ev": mean_ev,
        "mean_kelly_pct": mean_kelly,
        "bankroll": bankroll,
        "current_drawdown_pct": round(current_drawdown * 100, 2),
        "demo_presentation_mode": _is_demo_presentation_mode(),
        "demo_only_candidates": int(out_df.get("demo_only", pd.Series(dtype=bool)).fillna(False).sum()) if not out_df.empty and "demo_only" in out_df.columns else 0,
        "clv_last_30d_pct": clv_metrics.get("mean_clv_last_30d_pct", 0.0),
        "beating_market": clv_metrics.get("is_beating_market", False),
        "outputs": {
            "parquet": str(parquet_path.relative_to(root)),
            "csv": str(csv_path.relative_to(root)),
            "summary": str(summary_path.relative_to(root)),
        },
        "storage": storage_meta,
    }
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    # Journal
    top_lines = []
    if not out_df.empty:
        sort_col = "kelly_stake_pct" if "kelly_stake_pct" in out_df.columns else "decision_score"
        top = out_df.sort_values(sort_col, ascending=False).head(10)
        for _, r in top.iterrows():
            ev_str = f"ev={r.get('true_ev',0):.2%}" if pd.notna(r.get("true_ev")) else ""
            kelly_str = f"kelly={r.get('kelly_stake_pct',0):.1%}" if pd.notna(r.get("kelly_stake_pct")) else ""
            steam_str = "🔥STEAM" if r.get("steam_detected") else ""
            top_lines.append(
                f"- {r.get('date','?')} | {r.get('home_team','?')} x {r.get('away_team','?')} | "
                f"{r.get('market','?')} | score={r.get('decision_score','?')} | {ev_str} | {kelly_str} {steam_str}"
            )

    journal = "\n".join([
        "# Decision Engine Journal v7.0",
        f"\nModo: {MODE}",
        f"Gerado: {summary['generated_at']}",
        f"Banca atual: R$ {bankroll:.2f} | Drawdown: {current_drawdown:.1%}",
        f"CLV últimos 30d: {clv_metrics.get('mean_clv_last_30d_pct', 0):.1f}%",
        f"Total candidatos: {summary['total_candidates']} | HIGH_CONFIDENCE: {high_conf}",
        f"Action required: {action_required}",
        "\n## Top Candidatos (por Kelly)",
        *(top_lines or ["- Nenhum candidato disponível."]),
        "\n## Métricas de Sistema",
        f"- Score médio: {mean_score}",
        f"- True EV médio: {(mean_ev or 0):.2%}" if mean_ev else "- True EV: N/A (aguardando odds)",
        f"- Kelly médio: {(mean_kelly or 0):.2%}" if mean_kelly else "- Kelly: N/A",
        f"- Batendo o mercado: {'SIM' if clv_metrics.get('is_beating_market') else 'NÃO (aguardar 50+ apostas com CLV)'}",
    ])
    journal_path.write_text(journal, encoding="utf-8")

    logger.info(
        "Decision Engine v7.0: candidatos=%s high_conf=%s action=%s kelly_medio=%.2f%% ev_medio=%.2f%%",
        len(out_df), high_conf, action_required,
        (mean_kelly or 0) * 100, (mean_ev or 0) * 100,
    )
    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s")
    result = run_decision_engine()
    sys.stdout.write(json.dumps(result, indent=2, ensure_ascii=False))
