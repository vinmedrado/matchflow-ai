"""
simulation_engine.py v7.0 — Engine de simulação com Kelly Fracional.
Substitui flat stake por gestão de banca dinâmica baseada em probabilidade ML vs odds.
"""
from __future__ import annotations
from typing import Any, Dict
import pandas as pd

try:
    from backend.core.logging_config import get_logger
    logger = get_logger("matchflow.backtest.simulation_engine")
except Exception:
    import logging
    logger = logging.getLogger("matchflow.backtest.simulation_engine")

OUTPUT_COLS = [
    "strategy", "market", "selection", "line", "odd",
    "stake", "stake_pct", "kelly_stake", "is_win", "result", "profit",
    "cumulative_profit", "bankroll_before", "bankroll_after", "equity_curve",
    "ml_probability", "true_ev", "kelly_stake_pct",
]


def _kelly_fraction(prob: float, odds: float, fraction: float = 0.25,
                    max_pct: float = 0.05) -> float:
    """Kelly Criterion fracionado."""
    if prob <= 0 or prob >= 1 or odds <= 1.0:
        return 0.0
    b = odds - 1.0
    q = 1.0 - prob
    kelly_full = (b * prob - q) / b
    if kelly_full <= 0:
        return 0.0
    return max(0.005, min(max_pct, kelly_full * fraction))


def simulate_signals(signals: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
    """
    Simula sinais com Kelly Fracional adaptativo.
    Usa ml_probability quando disponível; fallback para flat stake configurado.
    """
    if signals.empty:
        logger.warning("Nenhum sinal recebido para simulação.")
        return pd.DataFrame(columns=OUTPUT_COLS)

    sim_cfg = config.get("simulation", {})
    initial_bankroll = float(sim_cfg.get("initial_bankroll", 1000.0))
    flat_stake = float(sim_cfg.get("stake", 1.0))
    use_kelly = bool(sim_cfg.get("use_kelly", True))
    kelly_fraction_cfg = float(sim_cfg.get("kelly_fraction", 0.25))
    max_stake_pct = float(sim_cfg.get("max_stake_pct", 0.05))
    min_odds = float(sim_cfg.get("min_odds", 1.2))
    sort_cols = [c for c in sim_cfg.get("sort_columns", ["date", "event_id", "strategy"]) if c in signals.columns]

    df = signals.copy()

    if "odd" not in df.columns:
        logger.warning("Coluna 'odd' ausente — nenhum trade financeiro.")
        return df.iloc[0:0].copy()

    df["odd"] = pd.to_numeric(df["odd"], errors="coerce")
    before = len(df)
    df = df[(df["odd"].notna()) & (df["odd"] >= min_odds)].copy()
    if before - len(df):
        logger.warning("Trades ignorados (odds inválidas): %s", before - len(df))

    if df.empty:
        return df

    if sort_cols:
        df = df.sort_values(sort_cols).reset_index(drop=True)
    else:
        df = df.reset_index(drop=True)

    # ── Calcular stake por aposta ──────────────────────────────────────────
    bankroll = initial_bankroll
    stakes = []
    stake_pcts = []
    kelly_stakes_pct = []

    for _, row in df.iterrows():
        odd = float(row["odd"])
        ml_prob = None

        # Tentar obter probabilidade ML
        for col in ["ensemble_probability", "ml_probability"]:
            val = row.get(col)
            if val is not None and pd.notna(val):
                try:
                    p = float(val)
                    if 0 < p < 1:
                        ml_prob = p
                        break
                except Exception:
                    pass

        # True EV para filtrar apostas sem edge
        true_ev = None
        try:
            ev = row.get("true_ev")
            if ev is not None and pd.notna(ev):
                true_ev = float(ev)
        except Exception:
            pass

        if use_kelly and ml_prob is not None:
            # Não apostar se true_ev <= 0 (sem edge real)
            if true_ev is not None and true_ev <= 0:
                kelly_pct = 0.0
            else:
                kelly_pct = _kelly_fraction(ml_prob, odd, kelly_fraction_cfg, max_stake_pct)
            stake = bankroll * kelly_pct
        else:
            # Flat stake como % da banca
            stake = flat_stake
            kelly_pct = flat_stake / bankroll if bankroll > 0 else 0.0

        stakes.append(round(stake, 4))
        stake_pcts.append(round(kelly_pct, 4))
        kelly_stakes_pct.append(round(kelly_pct, 4))

        # Atualizar banca para próxima aposta (Kelly dinâmico)
        is_win = _evaluate_signal(row)
        if is_win:
            bankroll += stake * (odd - 1.0)
        else:
            bankroll -= stake

    df["stake"] = stakes
    df["stake_pct"] = stake_pcts
    df["kelly_stake"] = stakes
    df["kelly_stake_pct"] = kelly_stakes_pct

    # Resetar banca para calcular curva de equity
    bankroll = initial_bankroll
    profits = []
    is_wins = []

    for i, row in df.iterrows():
        odd = float(row["odd"])
        stake = float(row["stake"])
        is_win = _evaluate_signal(row)
        profit = stake * (odd - 1.0) if is_win else -stake
        is_wins.append(is_win)
        profits.append(round(profit, 4))

    df["is_win"] = is_wins
    df["result"] = [("win" if w else "loss") for w in is_wins]
    df["profit"] = profits
    df["return"] = df["profit"]
    df["cumulative_profit"] = df["profit"].cumsum()
    df["bankroll_before"] = initial_bankroll + df["cumulative_profit"].shift(1).fillna(0.0)
    df["bankroll_after"] = initial_bankroll + df["cumulative_profit"]
    df["equity_curve"] = df["bankroll_after"]

    total = len(df)
    wins = int(df["is_win"].sum())
    final_bk = float(df["bankroll_after"].iloc[-1]) if total else initial_bankroll
    avg_kelly = float(df["kelly_stake_pct"].mean()) if total else 0.0

    logger.info(
        "Simulação Kelly v7.0: trades=%s wins=%s losses=%s kelly_médio=%.2f%% "
        "lucro=%.4f bankroll_final=%.2f",
        total, wins, total - wins, avg_kelly * 100,
        float(df["profit"].sum()), final_bk,
    )
    return df


def build_equity_curve(simulated: pd.DataFrame) -> pd.DataFrame:
    if simulated.empty:
        return pd.DataFrame(columns=["trade_number", "date", "strategy", "market",
                                      "stake", "odd", "profit", "cumulative_profit",
                                      "bankroll_after", "drawdown", "kelly_stake_pct"])
    curve = simulated.copy().reset_index(drop=True)
    curve["trade_number"] = curve.index + 1
    equity = curve["bankroll_after"].astype(float)
    peak = equity.cummax()
    curve["drawdown"] = equity - peak
    curve["drawdown_pct"] = (equity - peak) / peak.where(peak > 0, 1)

    cols = ["trade_number", "date", "strategy", "market", "stake", "kelly_stake_pct",
            "odd", "profit", "cumulative_profit", "bankroll_after", "drawdown", "drawdown_pct"]
    return curve[[c for c in cols if c in curve.columns]]


def _evaluate_signal(row: pd.Series) -> bool:
    market = row.get("market")
    line = row.get("line")
    selection = str(row.get("selection") or "").lower()

    def _f(v):
        if pd.isna(v) if hasattr(pd, 'isna') else v is None:
            return None
        try:
            return float(v)
        except Exception:
            return None

    if market == "goals":
        total = _f(row.get("total_goals_ft"))
        return total is not None and line is not None and total > float(line)

    if market == "corners":
        cf = _f(row.get("corners_for")) or 0.0
        ca = _f(row.get("corners_against")) or 0.0
        return line is not None and (cf + ca) > float(line)

    if market == "shots":
        shots = _f(row.get("shots_for"))
        return shots is not None and line is not None and shots > float(line)

    if market == "btts":
        gf = _f(row.get("goals_for_ft"))
        ga = _f(row.get("goals_against_ft"))
        if gf is None or ga is None:
            return False
        both = gf > 0 and ga > 0
        return bool(both) if "yes" in selection else not bool(both)

    return False
