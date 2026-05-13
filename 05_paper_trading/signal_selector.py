from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict, List, Set

import pandas as pd
from backend.core.storage import safe_read_dataframe, safe_write_dataframe

from backend.core.logging_config import get_logger

logger = get_logger("matchflow.paper.signal_selector")

CRITICAL_RISK_FLAGS: Set[str] = {
    "LOW_SAMPLE_SIZE",
    "HIGH_DRAWDOWN",
    "UNSTABLE_ROI",
    "NEGATIVE_ROLLING_ROI",
    "POSSIBLE_OVERFITTING",
}

OUTCOME_COLUMNS = ["goals_for_ft", "goals_against_ft", "total_goals_ft", "corners_for", "corners_against", "shots_for", "shots_against"]


def _safe_read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        logger.warning("Arquivo não encontrado para paper trading: %s", path)
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception as exc:
        logger.error("Falha ao ler CSV %s: %s", path, exc)
        return pd.DataFrame()


def _safe_read_parquet(path: Path) -> pd.DataFrame:
    if not path.exists():
        logger.warning("Dataset avançado não encontrado para paper trading: %s", path)
        return pd.DataFrame()
    try:
        return safe_read_dataframe(path)
    except Exception as exc:
        logger.error("Falha ao ler parquet %s: %s", path, exc)
        return pd.DataFrame()


def _split_flags(value: Any) -> Set[str]:
    if pd.isna(value) or value is None:
        return set()
    return {part.strip() for part in str(value).replace(",", "|").split("|") if part.strip()}


def stable_signal_id(row: pd.Series | Dict[str, Any], strategy: str, market: str) -> str:
    raw = "|".join([str(row.get("match_key", "")), str(row.get("team_key", "")), str(strategy), str(market)])
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


class PaperSignalSelector:
    """Selects local simulated paper signals only from KEEP candidates."""

    def __init__(self, project_root: Path, config: Dict[str, Any]) -> None:
        self.project_root = project_root
        self.config = config
        self.refinement_dir = project_root / "data" / "backtest" / "refinement"
        self.features_path = project_root / "data" / "features" / "team_dataset_advanced.parquet"
        self.ignored_reasons: List[Dict[str, Any]] = []

    def load_keep_candidates(self) -> pd.DataFrame:
        refined = _safe_read_csv(self.refinement_dir / "refined_strategy_candidates.csv")
        risk = _safe_read_csv(self.refinement_dir / "refinement_risk_report.csv")
        if refined.empty:
            logger.warning("Nenhuma estratégia KEEP disponível para paper trading.")
            return pd.DataFrame()

        allowed = set(self.config.get("allowed_recommendations", ["KEEP"]))
        min_score = float(self.config.get("min_consistency_score", 60))
        min_sample = int(self.config.get("min_sample_size", 100))
        df = refined.copy()
        if "recommendation" not in df.columns:
            df["recommendation"] = "KEEP"
        if not risk.empty and {"strategy", "market", "risk_flags", "final_recommendation"}.issubset(risk.columns):
            df = df.merge(risk[["strategy", "market", "risk_flags", "final_recommendation"]], on=["strategy", "market"], how="left", suffixes=("", "_risk"))

        valid_rows = []
        for _, row in df.iterrows():
            reasons = []
            recommendation = str(row.get("recommendation", "")).upper()
            final_recommendation = str(row.get("final_recommendation", recommendation)).upper()
            flags = _split_flags(row.get("risk_flags", ""))
            total_trades = int(float(row.get("total_trades", 0) or 0))
            consistency = float(row.get("consistency_score", 0) or 0)
            if recommendation not in allowed or final_recommendation not in allowed:
                reasons.append("NOT_KEEP")
            if total_trades < min_sample:
                reasons.append("BELOW_MIN_SAMPLE")
            if consistency < min_score:
                reasons.append("BELOW_MIN_CONSISTENCY")
            if flags.intersection(CRITICAL_RISK_FLAGS):
                reasons.append("CRITICAL_RISK_FLAGS")
            if reasons:
                self.ignored_reasons.append({"strategy": row.get("strategy"), "market": row.get("market"), "reasons": "|".join(reasons)})
                continue
            valid_rows.append(row.to_dict())
        result = pd.DataFrame(valid_rows)
        logger.info("Estratégias KEEP elegíveis para paper trading: %s", len(result))
        return result

    def select_signals(self, current_date: pd.Timestamp | None = None, last_processed_date: pd.Timestamp | None = None, existing_signal_ids: Set[str] | None = None) -> pd.DataFrame:
        candidates = self.load_keep_candidates()
        dataset = _safe_read_parquet(self.features_path)
        existing_signal_ids = existing_signal_ids or set()
        if current_date is None:
            if not dataset.empty and 'date' in dataset.columns:
                _dates = pd.to_datetime(dataset['date'], errors='coerce').dropna()
                current_date = _dates.max() if not _dates.empty else pd.Timestamp.utcnow().normalize()
            else:
                current_date = pd.Timestamp.utcnow().normalize()
        current_date = pd.to_datetime(current_date)
        if candidates.empty or dataset.empty:
            logger.warning("Paper trading sem sinais: candidates=%s dataset_rows=%s", len(candidates), len(dataset))
            return self._empty_signals()
        if "date" not in dataset.columns:
            logger.error("Dataset avançado sem coluna date; sinais paper não serão gerados.")
            return self._empty_signals()

        df = dataset.copy()
        df["_date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df[df["_date"].notna() & (df["_date"] <= current_date)]
        if last_processed_date is not None and pd.notna(last_processed_date):
            df = df[df["_date"] > last_processed_date]
        df = df.sort_values("_date")
        if df.empty:
            logger.info("Nenhum jogo novo para paper trading até %s", current_date.date())
            return self._empty_signals()

        max_signals = int(self.config.get("max_signals_per_day", 10))
        delay_days = int(self.config.get("resolution_delay_days", 1))
        signals: List[Dict[str, Any]] = []
        for _, candidate in candidates.iterrows():
            strategy = str(candidate.get("strategy"))
            market = str(candidate.get("market"))
            pool = self._filter_pool_for_market(df, market)
            for _, row in pool.iterrows():
                odd = self._extract_odd(row, market)
                if odd is None or odd < 1.2:
                    self.ignored_reasons.append({"strategy": strategy, "market": market, "reasons": "MISSING_OR_INVALID_ODD"})
                    continue
                signal_id = stable_signal_id(row, strategy, market)
                if signal_id in existing_signal_ids:
                    self.ignored_reasons.append({"strategy": strategy, "market": market, "reasons": "DUPLICATE_SIGNAL"})
                    continue
                signal_date = pd.to_datetime(row.get("date"), errors="coerce")
                signal: Dict[str, Any] = {
                    "signal_id": signal_id,
                    "created_at": pd.Timestamp.utcnow().isoformat(),
                    "paper_only": True,
                    "status": "PENDING",
                    "signal_date": signal_date.date().isoformat(),
                    "expected_resolution_date": (signal_date + pd.Timedelta(days=delay_days)).date().isoformat(),
                    "strategy": strategy,
                    "market": market,
                    "recommendation": "KEEP",
                    "team_key": row.get("team_key"),
                    "team_name": row.get("team_name"),
                    "opponent_key": row.get("opponent_key"),
                    "opponent_name": row.get("opponent_name"),
                    "league": row.get("league"),
                    "season": row.get("season"),
                    "date": row.get("date"),
                    "match_key": row.get("match_key"),
                    "side": row.get("side"),
                    "odd": float(odd),
                    "stake": float(self.config.get("fixed_stake", 1.0)),
                    "consistency_score": float(candidate.get("consistency_score", 0) or 0),
                    "supporting_sample_size": int(float(candidate.get("total_trades", 0) or 0)),
                    "risk_flags": candidate.get("risk_flags", ""),
                    "source": "refined_strategy_candidates.csv",
                }
                for col in OUTCOME_COLUMNS:
                    if col in row.index:
                        signal[col] = row.get(col)
                signals.append(signal)
                existing_signal_ids.add(signal_id)
                if len(signals) >= max_signals:
                    logger.info("Limite de sinais paper atingido: %s", max_signals)
                    return pd.DataFrame(signals)
        logger.info("Novos sinais paper selecionados: %s", len(signals))
        return pd.DataFrame(signals) if signals else self._empty_signals()

    def _filter_pool_for_market(self, pool: pd.DataFrame, market: str) -> pd.DataFrame:
        required_by_market = {
            "goals": ["goal_trend", "expected_goals_proxy"],
            "corners": ["corners_trend", "pressure_avg_last_5"],
            "shots": ["shots_avg_last_5", "shots_on_target_rate_avg_last_5"],
            "btts": ["goals_for_ft_avg_last_5", "goals_against_ft_avg_last_5"],
        }
        required = required_by_market.get(market, [])
        available = [col for col in required if col in pool.columns]
        return pool.dropna(subset=available, how="all") if available else pool.head(0)

    def _extract_odd(self, row: pd.Series, market: str) -> float | None:
        aliases = {
            "goals": ["odds_over_2_5", "Odd_Over25_FT", "odd_over_2_5", "odds_goals"],
            "corners": ["odds_corners", "Odd_Corners_Over85", "Odd_Corners_Over95"],
            "shots": ["odds_shots", "odd_shots"],
            "btts": ["odds_btts", "Odd_BTTS_Yes", "odd_btts_yes"],
        }
        for col in aliases.get(market, []):
            if col in row.index:
                value = pd.to_numeric(row.get(col), errors="coerce")
                if pd.notna(value) and float(value) > 0:
                    return float(value)
        return None

    def _empty_signals(self) -> pd.DataFrame:
        return pd.DataFrame(columns=["signal_id", "created_at", "paper_only", "status", "signal_date", "expected_resolution_date", "strategy", "market", "recommendation", "team_key", "team_name", "opponent_key", "opponent_name", "league", "season", "date", "match_key", "side", "odd", "stake", "consistency_score", "supporting_sample_size", "risk_flags", "source", *OUTCOME_COLUMNS])
