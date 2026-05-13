from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKTEST_ROOT = PROJECT_ROOT / "04_backtest"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(BACKTEST_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKTEST_ROOT))


def test_backtest_config_uses_financial_simulation():
    config_path = PROJECT_ROOT / "04_backtest" / "config" / "backtest_config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))

    assert config["version"] == "4.0.1"
    assert "initial_bankroll" in config["simulation"]
    assert "stake" in config["simulation"]
    assert "min_odds" in config["simulation"]
    assert "equity_curve_path" in config["outputs"]

    for market_config in config["markets"].values():
        if market_config.get("enabled"):
            assert market_config.get("odds_aliases"), market_config
