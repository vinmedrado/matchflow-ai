from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

import pandas as pd

from backend.core.logging_config import get_logger
try:
    from paper_metrics import build_summary
except Exception:  # legacy importlib loading without package path
    import importlib.util as _importlib_util
    _metrics_path = Path(__file__).resolve().parent / "paper_metrics.py"
    _spec = _importlib_util.spec_from_file_location("paper_metrics_legacy", _metrics_path)
    _module = _importlib_util.module_from_spec(_spec)
    assert _spec and _spec.loader
    _spec.loader.exec_module(_module)
    build_summary = _module.build_summary

logger = get_logger("matchflow.paper.engine")

DEFAULT_STATE = {"last_processed_date": None, "active_signals": [], "resolved_signals_ids": []}


class PaperTradingEngine:
    """Incremental local-only paper trading ledger.

    New signals are always stored as PENDING. Settlement only happens in a later
    cycle when current_date >= expected_resolution_date and local outcome fields
    are available. Historical backtest files are never modified.
    """

    def __init__(self, project_root: Path, config: Dict[str, Any]) -> None:
        self.project_root = project_root
        self.config = config
        self.output_dir = project_root / "data" / "paper_trading"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.signals_path = self._resolve(config.get("signals_path", "data/paper_trading/paper_signals.csv"))
        self.results_path = self._resolve(config.get("results_path", "data/paper_trading/paper_results.csv"))
        self.equity_path = self._resolve(config.get("equity_curve_path", "data/paper_trading/paper_equity_curve.csv"))
        self.summary_path = self._resolve(config.get("summary_path", "data/paper_trading/paper_summary.json"))
        self.state_path = self._resolve(config.get("state_path", "data/paper_trading/paper_state.json"))
        for path in [self.signals_path, self.results_path, self.equity_path, self.summary_path, self.state_path]:
            path.parent.mkdir(parents=True, exist_ok=True)

    def _resolve(self, value: str | Path) -> Path:
        path = Path(value)
        return path if path.is_absolute() else self.project_root / path

    def load_state(self) -> Dict[str, Any]:
        if not self.state_path.exists():
            state = DEFAULT_STATE.copy()
            self.save_state(state)
            return state
        try:
            state = json.loads(self.state_path.read_text(encoding="utf-8"))
            for key, default in DEFAULT_STATE.items():
                state.setdefault(key, [] if isinstance(default, list) else default)
            return state
        except Exception as exc:
            logger.error("Falha ao ler estado paper; recriando estado seguro: %s", exc)
            state = DEFAULT_STATE.copy()
            self.save_state(state)
            return state

    def save_state(self, state: Dict[str, Any]) -> None:
        self.state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("Estado paper salvo em %s", self.state_path)

    def existing_signal_ids(self) -> Set[str]:
        ids: Set[str] = set()
        if self.signals_path.exists():
            try:
                signals = pd.read_csv(self.signals_path)
                if "signal_id" in signals.columns:
                    ids.update(signals["signal_id"].dropna().astype(str).tolist())
            except Exception as exc:
                logger.warning("Falha ao ler sinais existentes para dedupe: %s", exc)
        state = self.load_state()
        ids.update(str(x) for x in state.get("resolved_signals_ids", []) if x)
        ids.update(str(x.get("signal_id")) for x in state.get("active_signals", []) if isinstance(x, dict) and x.get("signal_id"))
        return ids

    def run(self, new_signals: pd.DataFrame, current_date: pd.Timestamp | None = None) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
        legacy_direct_settled = current_date is None and not new_signals.empty and 'status' in new_signals.columns and new_signals['status'].astype(str).str.upper().eq('SETTLED').any()
        if current_date is None:
            if not new_signals.empty and 'date' in new_signals.columns:
                _dates = pd.to_datetime(new_signals['date'], errors='coerce').dropna()
                current_date = _dates.max() if not _dates.empty else pd.Timestamp.utcnow().normalize()
            else:
                current_date = pd.Timestamp.utcnow().normalize()
        current_date = pd.to_datetime(current_date)
        state = self.load_state()
        existing_signals = self._read_csv(self.signals_path)
        existing_results = self._read_csv(self.results_path)

        if legacy_direct_settled and existing_signals.empty:
            results = new_signals.copy()
            rows = []
            pnl_today = 0.0
            for _, row in results.iterrows():
                odd = pd.to_numeric(row.get('odd'), errors='coerce')
                stake = pd.to_numeric(row.get('stake'), errors='coerce')
                odd = 2.0 if pd.isna(odd) else float(odd)
                stake = float(self.config.get('fixed_stake', 1.0)) if pd.isna(stake) else float(stake)
                is_win = self._evaluate_signal(row) if self._has_outcome(row) else False
                profit = stake * (odd - 1.0) if is_win else -stake
                rec = row.to_dict()
                rec.update({'status': 'SETTLED', 'is_win': bool(is_win), 'profit': round(float(profit), 6), 'settled_at': pd.Timestamp.utcnow().isoformat(), 'settled_on_date': current_date.date().isoformat()})
                rows.append(rec)
                pnl_today += profit
            results = pd.DataFrame(rows)
            signals = results.copy()
            equity = self._build_equity_curve(results)
            signals.to_csv(self.signals_path, index=False)
            results.to_csv(self.results_path, index=False)
            equity.to_csv(self.equity_path, index=False)
            state['last_processed_date'] = current_date.date().isoformat()
            state['resolved_signals_ids'] = sorted(set(results['signal_id'].dropna().astype(str).tolist())) if 'signal_id' in results.columns else []
            self.save_state(state)
            summary = build_summary(signals, results, equity, initial_bankroll=float(self.config.get('initial_bankroll', 100.0)))
            summary.update({'current_date': current_date.date().isoformat(), 'new_signals_today': 0, 'resolved_signals_today': int(len(results)), 'daily_pnl': round(float(pnl_today), 6), 'active_exposure': 0.0, 'state_path': str(self.state_path)})
            self.summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')
            return signals, results, equity, summary

        results, resolved_today, pnl_today = self.update_results(existing_signals, existing_results, current_date, state)
        signals, new_today = self.generate_signals(existing_signals, new_signals)
        equity = self._build_equity_curve(results)

        signals.to_csv(self.signals_path, index=False)
        results.to_csv(self.results_path, index=False)
        equity.to_csv(self.equity_path, index=False)

        state["last_processed_date"] = current_date.date().isoformat()
        state["active_signals"] = self._active_signal_records(signals)
        self.save_state(state)

        summary = build_summary(signals, results, equity, initial_bankroll=float(self.config.get("initial_bankroll", 100.0)))
        summary.update({
            "current_date": current_date.date().isoformat(),
            "new_signals_today": int(new_today),
            "resolved_signals_today": int(resolved_today),
            "daily_pnl": round(float(pnl_today), 6),
            "active_exposure": round(self._active_exposure(signals), 6),
            "state_path": str(self.state_path),
        })
        self.summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("Paper incremental concluído: new=%s resolved=%s pending=%s", new_today, resolved_today, summary.get("pending_signals", 0))
        return signals, results, equity, summary

    def generate_signals(self, existing_signals: pd.DataFrame, new_signals: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
        if new_signals.empty:
            logger.info("Nenhum sinal novo gerado no ciclo paper.")
            return existing_signals.copy(), 0
        df = new_signals.copy()
        df["status"] = "PENDING"
        if not existing_signals.empty and "signal_id" in existing_signals.columns:
            existing_ids = set(existing_signals["signal_id"].dropna().astype(str))
            df = df[~df["signal_id"].astype(str).isin(existing_ids)].copy()
        if df.empty:
            logger.info("Dedupe: nenhum sinal novo após remover duplicados.")
            return existing_signals.copy(), 0
        combined = pd.concat([existing_signals, df], ignore_index=True) if not existing_signals.empty else df
        combined = combined.drop_duplicates(subset=["signal_id"], keep="first").reset_index(drop=True)
        logger.info("Sinais PENDING adicionados: %s", len(df))
        return combined, int(len(df))

    def update_results(self, signals: pd.DataFrame, existing_results: pd.DataFrame, current_date: pd.Timestamp, state: Dict[str, Any]) -> Tuple[pd.DataFrame, int, float]:
        if signals.empty:
            return existing_results.copy(), 0, 0.0
        resolved_ids = set(str(x) for x in state.get("resolved_signals_ids", []) if x)
        if not existing_results.empty and "signal_id" in existing_results.columns:
            resolved_ids.update(existing_results["signal_id"].dropna().astype(str).tolist())
        rows: List[Dict[str, Any]] = []
        pnl_today = 0.0
        for idx, row in signals.iterrows():
            signal_id = str(row.get("signal_id", ""))
            if not signal_id or signal_id in resolved_ids:
                continue
            if str(row.get("status", "PENDING")).upper() != "PENDING":
                continue
            expected = pd.to_datetime(row.get("expected_resolution_date"), errors="coerce")
            if pd.isna(expected) or current_date < expected:
                continue
            if not self._has_outcome(row):
                logger.warning("Sinal ainda sem resultado disponível: %s", signal_id)
                continue
            odd = pd.to_numeric(row.get("odd"), errors="coerce")
            stake = pd.to_numeric(row.get("stake"), errors="coerce")
            if pd.isna(odd) or float(odd) < 1.2 or pd.isna(stake) or float(stake) <= 0:
                logger.warning("Sinal não liquidado por odd/stake inválido: %s", signal_id)
                continue
            is_win = self._evaluate_signal(row)
            profit = float(stake) * (float(odd) - 1.0) if is_win else -float(stake)
            result = row.to_dict()
            result.update({"status": "SETTLED", "is_win": bool(is_win), "profit": round(profit, 6), "settled_at": pd.Timestamp.utcnow().isoformat(), "settled_on_date": current_date.date().isoformat()})
            rows.append(result)
            signals.loc[idx, "status"] = "SETTLED"
            resolved_ids.add(signal_id)
            pnl_today += profit
        state["resolved_signals_ids"] = sorted(resolved_ids)
        if rows:
            new_results = pd.DataFrame(rows)
            combined = pd.concat([existing_results, new_results], ignore_index=True) if not existing_results.empty else new_results
            combined = combined.drop_duplicates(subset=["signal_id"], keep="first").reset_index(drop=True)
            logger.info("Sinais resolvidos no ciclo: %s", len(rows))
            return combined, int(len(rows)), float(pnl_today)
        logger.info("Nenhum sinal pendente atingiu data de resolução neste ciclo.")
        return existing_results.copy(), 0, 0.0

    def _read_csv(self, path: Path) -> pd.DataFrame:
        if not path.exists():
            return pd.DataFrame()
        try:
            return pd.read_csv(path)
        except Exception as exc:
            logger.warning("Falha ao ler %s; usando DataFrame vazio: %s", path, exc)
            return pd.DataFrame()

    def _has_outcome(self, row: pd.Series) -> bool:
        market = str(row.get("market", "")).lower()
        required = {"goals": ["total_goals_ft"], "corners": ["corners_for", "corners_against"], "shots": ["shots_for"], "btts": ["goals_for_ft", "goals_against_ft"]}.get(market, [])
        return all(col in row.index and pd.notna(row.get(col)) for col in required)

    def _evaluate_signal(self, row: pd.Series) -> bool:
        strategy = str(row.get("strategy", "")).lower()
        market = str(row.get("market", "")).lower()
        if market == "goals":
            total = float(pd.to_numeric(row.get("total_goals_ft"), errors="coerce"))
            threshold = 1.5 if "1.5" in strategy else 2.5
            return total > threshold
        if market == "corners":
            total = float(pd.to_numeric(row.get("corners_for"), errors="coerce")) + float(pd.to_numeric(row.get("corners_against"), errors="coerce"))
            threshold = 9.5 if "9.5" in strategy else 8.5
            return total > threshold
        if market == "shots":
            shots = float(pd.to_numeric(row.get("shots_for"), errors="coerce"))
            return shots >= 5.0
        if market == "btts":
            gf = float(pd.to_numeric(row.get("goals_for_ft"), errors="coerce"))
            ga = float(pd.to_numeric(row.get("goals_against_ft"), errors="coerce"))
            is_yes = "no" not in strategy
            both_score = gf > 0 and ga > 0
            return both_score if is_yes else not both_score
        return False

    def _build_equity_curve(self, results: pd.DataFrame) -> pd.DataFrame:
        bankroll = float(self.config.get("initial_bankroll", 100.0))
        rows = []
        if results.empty:
            return pd.DataFrame(columns=["step", "signal_id", "date", "strategy", "market", "profit", "bankroll"])
        df = results.copy().sort_values(["settled_on_date", "signal_id"] if "settled_on_date" in results.columns else ["signal_id"])
        for idx, (_, row) in enumerate(df.iterrows(), start=1):
            bankroll += float(row.get("profit", 0.0) or 0.0)
            rows.append({"step": idx, "signal_id": row.get("signal_id"), "date": row.get("settled_on_date", row.get("date")), "strategy": row.get("strategy"), "market": row.get("market"), "profit": round(float(row.get("profit", 0.0) or 0.0), 6), "bankroll": round(bankroll, 6)})
        return pd.DataFrame(rows)

    def _active_signal_records(self, signals: pd.DataFrame) -> List[Dict[str, Any]]:
        if signals.empty or "status" not in signals.columns:
            return []
        active = signals[signals["status"].astype(str).str.upper() == "PENDING"].copy()
        cols = ["signal_id", "signal_date", "expected_resolution_date", "strategy", "market", "stake", "odd"]
        cols = [col for col in cols if col in active.columns]
        return active[cols].to_dict(orient="records")

    def _active_exposure(self, signals: pd.DataFrame) -> float:
        if signals.empty or "status" not in signals.columns or "stake" not in signals.columns:
            return 0.0
        pending = signals[signals["status"].astype(str).str.upper() == "PENDING"]
        return float(pd.to_numeric(pending["stake"], errors="coerce").fillna(0).sum())
