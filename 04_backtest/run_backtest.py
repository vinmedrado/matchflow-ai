from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path
from typing import Tuple

import pandas as pd
from backend.core.storage import safe_read_dataframe, safe_write_dataframe

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKTEST_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(BACKTEST_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKTEST_ROOT))

from backend.core.logging_config import configure_logging, get_logger
from engine.metrics import calculate_summary
from engine.signal_generator import generate_signals
from engine.simulation_engine import build_equity_curve, simulate_signals
from engine.strategy_engine import load_backtest_config, load_strategies

configure_logging()
logger = get_logger("matchflow.backtest.run_backtest")


REQUIRED_COLUMNS = [
    "date",
    "league",
    "season",
    "team_key",
    "team_name",
    "opponent_key",
    "opponent_name",
    "side",
    "goals_for_ft",
    "goals_against_ft",
    "total_goals_ft",
]


def resolve_path(path: str | Path) -> Path:
    path_obj = Path(path)
    return path_obj if path_obj.is_absolute() else PROJECT_ROOT / path_obj


def run_backtest(config_path: str | Path = BACKTEST_ROOT / "config" / "backtest_config.json") -> Tuple[pd.DataFrame, pd.DataFrame]:
    started = time.perf_counter()
    config = load_backtest_config(config_path)

    input_path = resolve_path(config.get("input_path", "data/features/team_dataset_advanced.parquet"))
    detailed_output = resolve_path(config["outputs"]["detailed_results_path"])
    summary_output = resolve_path(config["outputs"]["summary_results_path"])
    equity_output = resolve_path(config["outputs"].get("equity_curve_path", "data/backtest/results/equity_curve.csv"))

    logger.info("Iniciando backtest financeiro multi-mercado")
    logger.info("Dataset de entrada: %s", input_path)

    if not input_path.exists():
        raise FileNotFoundError(f"Advanced dataset not found: {input_path}")

    df = _read_parquet_safe(input_path)
    _validate_input(df)

    strategies = load_strategies(config)
    min_odds = float(config.get("simulation", {}).get("min_odds", 1.2))
    signals = generate_signals(df, strategies, min_odds=min_odds)
    detailed = simulate_signals(signals, config)
    summary = calculate_summary(detailed)
    equity_curve = build_equity_curve(detailed)

    detailed_output.parent.mkdir(parents=True, exist_ok=True)
    summary_output.parent.mkdir(parents=True, exist_ok=True)
    equity_output.parent.mkdir(parents=True, exist_ok=True)

    if detailed.empty:
        logger.warning("Backtest financeiro não gerou trades com odds válidas. Salvando arquivos vazios com schema mínimo.")

    _write_parquet_safe(detailed, detailed_output)
    summary.to_csv(summary_output, index=False)
    equity_curve.to_csv(equity_output, index=False)

    _write_legacy_copies(config, detailed_output, summary_output, equity_output)

    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    logger.info(
        "Backtest financeiro finalizado: trades=%s estratégias=%s equity_points=%s tempo_ms=%s",
        len(detailed),
        len(summary),
        len(equity_curve),
        elapsed_ms,
    )
    logger.info("Resultado detalhado salvo em: %s", detailed_output)
    logger.info("Resumo salvo em: %s", summary_output)
    logger.info("Curva de banca salva em: %s", equity_output)

    return detailed, summary



def _read_parquet_safe(path: Path) -> pd.DataFrame:
    return safe_read_dataframe(path, required=True)


def _validate_input(df: pd.DataFrame) -> None:
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"Advanced dataset missing required columns: {missing}")
    if df.empty:
        raise ValueError("Advanced dataset is empty.")
    logger.info("Dataset avançado validado: linhas=%s colunas=%s", len(df), len(df.columns))



def _write_parquet_safe(df: pd.DataFrame, path: Path) -> None:
    safe_write_dataframe(df, path, index=False, also_write_csv=True)


def _write_legacy_copies(config: dict, detailed_output: Path, summary_output: Path, equity_output: Path) -> None:
    detailed_dir = resolve_path(config["outputs"].get("legacy_detailed_dir", "04_backtest/results/detailed"))
    summary_dir = resolve_path(config["outputs"].get("legacy_summary_dir", "04_backtest/results/summary"))
    equity_dir = resolve_path(config["outputs"].get("legacy_equity_dir", "04_backtest/results/summary"))
    detailed_dir.mkdir(parents=True, exist_ok=True)
    summary_dir.mkdir(parents=True, exist_ok=True)
    equity_dir.mkdir(parents=True, exist_ok=True)

    shutil.copyfile(detailed_output, detailed_dir / detailed_output.name)
    shutil.copyfile(summary_output, summary_dir / summary_output.name)
    shutil.copyfile(equity_output, equity_dir / equity_output.name)


if __name__ == "__main__":
    run_backtest()
