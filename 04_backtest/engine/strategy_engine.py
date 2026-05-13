from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from backend.core.logging_config import get_logger

from strategies import btts_strategy, corners_strategy, goals_strategy, shots_strategy

logger = get_logger("matchflow.backtest.strategy_engine")


def load_backtest_config(config_path: str | Path) -> Dict[str, Any]:
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Backtest config not found: {path}")
    with path.open("r", encoding="utf-8") as file:
        config = json.load(file)
    logger.info("Configuração de backtest carregada: %s", path)
    return config


def load_strategies(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    strategies: List[Dict[str, Any]] = []
    strategies.extend(goals_strategy.get_strategies(config))
    strategies.extend(corners_strategy.get_strategies(config))
    strategies.extend(shots_strategy.get_strategies(config))
    strategies.extend(btts_strategy.get_strategies(config))

    logger.info("Estratégias carregadas: %s", len(strategies))
    return strategies
