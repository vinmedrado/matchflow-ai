"""report_generator.py v7.0 — Relatório diário com CLV, True EV, Kelly e performance."""
from __future__ import annotations
import sys
from pathlib import Path
from typing import Any

import pandas as pd

from .automation_state import mark_report
from .common import MODE, automation_dir, load_json, save_json, utc_now


def _read_csv(path: Path, limit: int = 10) -> list[dict[str, Any]]:
    try:
        if not path.exists() or path.stat().st_size == 0:
            return []
        return pd.read_csv(path).head(limit).fillna("").to_dict(orient="records")
    except Exception:
        return []


def _clv_section(root: Path) -> list[str]:
    try:
        sys.path.insert(0, str(root / "09_decision_engine"))
        from clv_tracker import get_clv_metrics
        clv = get_clv_metrics(root)
        if not clv.get("ok"):
            return ["- CLV: aguardando dados (configure odds de fechamento)"]
        lines = [
            f"- CLV médio (todas): **{clv.get('mean_clv_all_time_pct', 0):.2f}%**",
            f"- CLV médio (30d): **{clv.get('mean_clv_last_30d_pct', 0):.2f}%**",
            f"- Batendo o mercado: **{'SIM ✓' if clv.get('is_beating_market') else 'NÃO (aguardar 50+ apostas)'}**",
            f"- CLV positivo: **{clv.get('positive_clv_rate', 0):.0%}** das apostas",
            f"- Total rastreadas: {clv.get('total_tracked', 0)} apostas",
        ]
        if clv.get("edge_deteriorating"):
            lines.append("- ⚠️ **EDGE DETERIORANDO** — reduzir stakes recomendado")
        return lines
    except Exception as exc:
        return [f"- CLV: erro ao calcular ({exc})"]


def _performance_section(root: Path) -> list[str]:
    try:
        perf = load_json(root / "data/performance/performance_attribution.json", {})
        if not perf.get("ok"):
            return ["- Performance: nenhum trade liquidado ainda"]
        skill = perf.get("skill_component", {})
        edge = perf.get("edge_health", {})
        return [
            f"- ROI total: **{perf.get('total_roi_pct', 0):.2f}%**",
            f"- Win rate: **{perf.get('win_rate', 0):.1%}**",
            f"- Trades: {perf.get('total_trades', 0)} (vitórias: {perf.get('wins', 0)})",
            f"- ROI por habilidade (CLV): {skill.get('skill_roi_pct', 'N/A')}%",
            f"- Recomendação: **{edge.get('recommendation', 'AGUARDAR_DADOS')}**",
        ]
    except Exception as exc:
        return [f"- Performance: erro ({exc})"]


def _monte_carlo_section(root: Path) -> list[str]:
    try:
        mc = load_json(root / "data/performance/monte_carlo_report.json", {})
        if not mc.get("ok"):
            return ["- Monte Carlo: não executado"]
        proj = mc.get("projections", {})
        risk = mc.get("risk", {})
        return [
            f"- Banca mediana 6m: **R$ {proj.get('p50_median', 0):.0f}**",
            f"- Pior cenário (P10): R$ {proj.get('p10', 0):.0f}",
            f"- Melhor cenário (P90): R$ {proj.get('p90', 0):.0f}",
            f"- Probabilidade de ruína: **{risk.get('ruin_probability_pct', 0):.1f}%**",
            f"- Probabilidade de dobrar: {risk.get('prob_doubling', 0)*100:.0f}%",
        ]
    except Exception as exc:
        return [f"- Monte Carlo: erro ({exc})"]


def generate_daily_report(root: Path | None = None) -> dict[str, Any]:
    root = root or Path.cwd()
    out_dir = automation_dir(root)

    state           = load_json(out_dir / "automation_state.json", {})
    data_ops        = load_json(root / "data/ops/data_ops_state.json", {})
    ml_registry     = load_json(root / "data/ml/models/registry.json", {})
    decision_summary = load_json(root / "data/decision_engine/decision_summary.json", {})
    monitoring      = load_json(root / "data/monitoring/monitoring_status.json", {})
    alerts          = load_json(root / "data/monitoring/alerts.json", {})
    paper_summary   = load_json(root / "data/paper_trading/paper_summary.json", {})
    candidates      = _read_csv(out_dir / "exported_candidates.csv", limit=10)
    telegram_log    = load_json(out_dir / "telegram_log.json", [])

    import os
    bankroll        = paper_summary.get("current_bankroll", os.getenv("INITIAL_BANKROLL", "1000"))
    high_conf       = decision_summary.get("high_confidence", 0)
    mean_ev         = decision_summary.get("mean_true_ev")
    mean_kelly      = decision_summary.get("mean_kelly_pct")
    beating_market  = decision_summary.get("beating_market", False)
    tg_sent         = len(telegram_log) if isinstance(telegram_log, list) else 0

    lines = [
        "# MatchFlow Analytics v7.0 — Relatório Diário",
        "",
        f"**Modo:** `{MODE}`  |  **Gerado:** `{utc_now()}`",
        "",
        "> Sistema de análise esportiva. Não executa apostas automáticas. Nenhuma ação real é executada.",
        "",
        "---",
        "",
        "## 📊 Resumo Executivo",
        f"- Status pipeline: **{state.get('overall_status', 'UNKNOWN')}**",
        f"- Última execução: {state.get('last_run_at', 'Nunca')}",
        f"- Banca atual: **R$ {float(bankroll or 0):.2f}**",
        f"- Batendo o mercado: **{'SIM ✓' if beating_market else 'NÃO'}**",
        f"- Alertas Telegram enviados: {tg_sent}",
        "",
        "## 🎯 Decision Engine",
        f"- Candidatos totais: {decision_summary.get('total_candidates', 0)}",
        f"- **HIGH CONFIDENCE: {high_conf}**",
        f"- Action Required: {decision_summary.get('action_required', 0)}",
        f"- True EV médio: {f'{mean_ev*100:.2f}%' if mean_ev else 'N/A (aguardar odds)'}",
        f"- Kelly médio: {f'{mean_kelly*100:.2f}%' if mean_kelly else 'N/A'}",
        "",
        "## 📈 CLV Analytics",
        *_clv_section(root),
        "",
        "## 🏆 Performance Attribution",
        *_performance_section(root),
        "",
        "## 🎲 Monte Carlo (projeção 6 meses)",
        *_monte_carlo_section(root),
        "",
        "## 🔧 Sistema",
        f"- Data Ops: {data_ops.get('engine_status', 'UNKNOWN')}",
        f"- ML modelos: {len(ml_registry.get('models', [])) if isinstance(ml_registry, dict) else 0}",
        f"- Monitoring: {monitoring.get('overall_status', 'UNKNOWN')}",
        f"- Alertas de risco: {alerts.get('total_alerts', 0)}",
        "",
        "## 🔔 Top Candidatos Exportados",
    ]

    if not candidates:
        lines.append("- Nenhum candidato exportado nesta execução.")
    else:
        for item in candidates:
            home = item.get('home_team', item.get('match', ''))
            away = item.get('away_team', '')
            match_str = f"{home} x {away}" if away else home
            score = item.get('decision_score', item.get('score', ''))
            ev = item.get('true_ev', '')
            kelly = item.get('kelly_stake_pct', '')
            steam = '🔥' if str(item.get('steam_detected', '')).lower() == 'true' else ''
            lines.append(
                f"- {steam} **{match_str}** | {item.get('market', '')} "
                f"| score={score} | ev={ev} | kelly={kelly}"
            )

    lines.extend([
        "",
        "---",
        "## ⚠️ Disclaimer",
        "- Este sistema NÃO executa apostas reais. Nenhuma ação real é executada.",
        "- Todas as recomendações requerem confirmação manual.",
        "- CLV e True EV são métricas analíticas, não garantias de lucro.",
        "- Edge em apostas esportivas é pequeno e pode variar. Aposte com responsabilidade.",
    ])

    path = out_dir / "daily_report.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    mark_report(root)

    summary = {
        "mode": MODE,
        "path": str(path),
        "generated_at": utc_now(),
        "candidates_in_report": len(candidates),
        "high_confidence": high_conf,
        "beating_market": beating_market,
        "telegram_sent": tg_sent,
    }
    save_json(out_dir / "last_report_summary.json", summary)
    return summary
