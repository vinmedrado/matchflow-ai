from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from backend.core.logging_config import get_logger

logger = get_logger("matchflow.paper.journal")


class PaperJournal:
    def __init__(self, project_root: Path) -> None:
        self.output_path = project_root / "data" / "paper_trading" / "paper_journal.md"
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, signals: pd.DataFrame, summary: Dict[str, Any], ignored: List[Dict[str, Any]]) -> Path:
        strategies = sorted(signals["strategy"].dropna().unique().tolist()) if not signals.empty and "strategy" in signals.columns else []
        ignored_lines = "\n".join(f"- {item.get('strategy', 'N/A')} / {item.get('market', 'N/A')}: {item.get('reasons', 'N/A')}" for item in ignored[:25]) or "- Nenhum item ignorado além das regras normais."
        content = f"""# MatchFlow Analytics — Paper Trading Journal

> Ambiente local/simulado. Este módulo não executa apostas, não acessa casas de aposta e não altera o backtest histórico.

## Execução incremental

- Data/hora: {pd.Timestamp.utcnow().isoformat()}
- Data simulada do ciclo: {summary.get('current_date', 'N/A')}
- Paper only: {summary.get('paper_only', True)}
- Novos sinais hoje: {summary.get('new_signals_today', 0)}
- Sinais resolvidos hoje: {summary.get('resolved_signals_today', 0)}
- PnL do dia: {summary.get('daily_pnl', 0.0)}
- Exposição ativa: {summary.get('active_exposure', 0.0)}

## Estado geral

- Total de sinais: {summary.get('total_signals', 0)}
- Sinais liquidados: {summary.get('settled_signals', 0)}
- Sinais pendentes: {summary.get('pending_signals', 0)}
- Arquivo de estado: {summary.get('state_path', 'data/paper_trading/paper_state.json')}

## Estratégias usadas

{chr(10).join(f'- {strategy}' for strategy in strategies) if strategies else '- Nenhuma estratégia KEEP elegível no ciclo atual.'}

## Sinais ignorados / riscos

{ignored_lines}

## Banca fictícia

- Banca inicial: {summary.get('initial_bankroll', 100.0)}
- Banca atual: {summary.get('current_bankroll', 100.0)}
- ROI paper: {summary.get('roi', 0.0)}
- Profit factor: {summary.get('profit_factor', 0.0)}
- Max drawdown: {summary.get('max_drawdown', 0.0)}

## Observações

- Novos sinais sempre entram como `PENDING`.
- Sinais só são resolvidos quando `current_date >= expected_resolution_date` e o resultado local está disponível.
- Rodar duas vezes não deve duplicar sinal para mesmo jogo + estratégia.
- Estratégias DISCARD não podem gerar sinal.
- Estratégias WATCH não são usadas enquanto `allow_watch_strategies=false`.
"""
        self.output_path.write_text(content, encoding="utf-8")
        logger.info("Journal paper salvo em %s", self.output_path)
        return self.output_path
