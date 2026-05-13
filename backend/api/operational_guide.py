from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/operational-guide", tags=["operational-guide"])


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _exists(rel: str) -> bool:
    return (_root() / rel).exists()


def _safe_json(rel: str) -> dict[str, Any]:
    path = _root() / rel
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except Exception:
        return {}


PIPELINE_STEPS = [
    {
        "id": "data_engine",
        "name": "Data Engine",
        "title": "Coletar e normalizar jogos",
        "business_label": "Central de Dados",
        "description": "Motor responsável por buscar jogos, odds e estatísticas, sem o usuário precisar abrir uma pasta técnica.",
        "command": "python run_data_engine_pipeline.py",
        "primary_endpoint": "POST /api/data-ops/engine-run?mode=incremental&days_back=7",
        "status_endpoint": "GET /api/data-ops/engine-status",
        "output": "data/processed/base_data_engine.parquet",
        "owner": "backend/services + data_ops",
        "ui_page": "Data Operations",
        "sellable_goal": "Virar worker interno online com histórico de jobs, logs e botão de atualização.",
    },
    {
        "id": "competitions",
        "name": "Campeonatos",
        "title": "Organizar ligas, times e próximos jogos",
        "business_label": "Competições",
        "description": "Camada visual para selecionar campeonato, ver tabela, jogos, recorte por time e cobertura de dados.",
        "command": "python run_team_dataset_pipeline.py",
        "primary_endpoint": "GET /api/competitions/overview",
        "status_endpoint": "GET /api/competitions/detail?league=...",
        "output": "data/features/team_dataset.parquet",
        "owner": "backend/api/competitions.py",
        "ui_page": "Competitions",
        "sellable_goal": "Deixar o cliente operar por campeonato/time, não por arquivo ou script.",
    },
    {
        "id": "backtest",
        "name": "Backtest",
        "title": "Validar estratégia por liga, time e mercado",
        "business_label": "Laboratório de Estratégia",
        "description": "Antes do ML, o sistema mede amostra, ROI, hit rate, EV e consistência por liga/time/mercado.",
        "command": "python run_backtest_pipeline.py",
        "primary_endpoint": "GET /api/backtest/analysis-summary",
        "status_endpoint": "GET /api/product/backtest-health",
        "output": "data/backtest/results/",
        "owner": "backend/services/backtest_service.py",
        "ui_page": "Backtest Lab",
        "sellable_goal": "Evoluir para backtest segmentado por time + liga + mercado com thresholds próprios.",
    },
    {
        "id": "ml",
        "name": "Machine Learning",
        "title": "Treinar modelos apenas depois da validação estatística",
        "business_label": "Inteligência Preditiva",
        "description": "O ML usa features e histórico validado pelo backtest para reduzir ruído e evitar modelo bonito sem edge real.",
        "command": "python run_ml_pipeline.py",
        "primary_endpoint": "GET /api/ml/ensemble-summary",
        "status_endpoint": "GET /api/ml/calibration-summary",
        "output": "data/ml/",
        "owner": "06_ml + backend/api/ml.py",
        "ui_page": "ML Lab",
        "sellable_goal": "Mostrar calibração, confiança, drift e explicação simples para usuário final.",
    },
    {
        "id": "decision_engine",
        "name": "Decision Engine",
        "title": "Transformar dados em candidatos auditáveis",
        "business_label": "Motor de Decisão",
        "description": "Cruza odds, backtest, ML, risco e qualidade da amostra para indicar candidatos de paper trading.",
        "command": "python run_decision_engine_pipeline.py",
        "primary_endpoint": "POST /api/decision-engine/run",
        "status_endpoint": "GET /api/decision-engine/summary",
        "output": "data/decision_engine/decision_candidates.csv",
        "owner": "09_decision_engine + backend/api/decision_engine.py",
        "ui_page": "Decision Engine",
        "sellable_goal": "Cada decisão precisa explicar motivo, risco, amostra, edge e limite de exposição.",
    },
    {
        "id": "bankroll",
        "name": "Banca",
        "title": "Escolher método de stake conforme perfil e qualidade do edge",
        "business_label": "Gestão de Capital",
        "description": "A banca deve decidir entre stake fixa, Kelly fracionado ou bloqueio conforme banca, drawdown, amostra e confiança.",
        "command": "python run_paper_trading_pipeline.py",
        "primary_endpoint": "GET /api/product/bankroll-policy?bankroll=1000&risk_profile=balanced",
        "status_endpoint": "GET /api/paper-trading/summary",
        "output": "data/paper_trading/",
        "owner": "paper_trading + product policy",
        "ui_page": "Bankroll Projection",
        "sellable_goal": "Virar uma carteira por usuário com regras automáticas e limites de segurança.",
    },
]

API_GROUPS = [
    {"group": "Autenticação", "purpose": "Login, sessão e permissões.", "endpoints": ["POST /api/auth/login", "GET /api/auth/me"]},
    {"group": "Dados", "purpose": "Data Engine, bridge e status dos arquivos processados.", "endpoints": ["GET /api/data-ops/status", "GET /api/data-ops/engine-status", "POST /api/data-ops/engine-run", "GET /api/data-ops/bridge-status"]},
    {"group": "Campeonatos", "purpose": "Exploração de ligas, times, próximos jogos e tabela operacional.", "endpoints": ["GET /api/competitions/overview", "GET /api/competitions/detail"]},
    {"group": "Backtest", "purpose": "Resumo, análise profunda e saúde estatística da estratégia.", "endpoints": ["GET /api/backtest/summary", "GET /api/backtest/analysis-summary", "GET /api/product/backtest-health"]},
    {"group": "ML", "purpose": "Calibração, ensemble e leitura dos modelos.", "endpoints": ["GET /api/ml/calibration-summary", "GET /api/ml/ensemble-summary"]},
    {"group": "Decisão", "purpose": "Candidatos, ranking e explicação da decisão.", "endpoints": ["GET /api/decision-engine/summary", "GET /api/decision-engine/candidates", "POST /api/decision-engine/run"]},
    {"group": "Banca e Performance", "purpose": "Paper trading, CLV, Monte Carlo, liquidação e política de stake.", "endpoints": ["GET /api/paper-trading/summary", "GET /api/paper-trading/signals", "POST /api/performance/monte-carlo", "GET /api/product/bankroll-policy"]},
    {"group": "Operação", "purpose": "Scheduler, automação, monitoramento, drift e alertas.", "endpoints": ["GET /api/automation/status", "POST /api/automation/run", "GET /api/monitoring/status", "POST /api/monitoring/run"]},
]

SELLABLE_ROADMAP = [
    {"phase": "Fase 1", "title": "Motor interno online", "goal": "O Data Engine deixa de parecer pasta externa e vira serviço acionado pela interface.", "done_when": "Usuário clica em Atualizar Dados, vê logs/status e os dados entram no banco."},
    {"phase": "Fase 2", "title": "Banco central e jobs", "goal": "PostgreSQL com ligas, times, jogos, odds, jobs, usuários, banca e sinais.", "done_when": "Nada crítico depende de CSV solto para a experiência do usuário."},
    {"phase": "Fase 3", "title": "Backtest por contexto", "goal": "Thresholds e métricas por liga + time + mercado + janela temporal.", "done_when": "O sistema mostra onde existe amostra suficiente e onde deve bloquear decisão."},
    {"phase": "Fase 4", "title": "ML pós-backtest", "goal": "ML consome apenas features/contextos aprovados pela camada estatística.", "done_when": "Cada previsão tem confiança, calibração, explicação e qualidade da amostra."},
    {"phase": "Fase 5", "title": "Multiusuário vendável", "goal": "Organizações, usuários, preferências, banca, limites e histórico isolados.", "done_when": "Dois usuários podem usar o mesmo sistema com carteiras e regras separadas."},
]


@router.get("/blueprint")
def blueprint() -> dict[str, Any]:
    root = _root()
    health = {
        "data_engine_script": _exists("run_data_engine_pipeline.py"),
        "scheduler_script": _exists("start_scheduler.py"),
        "processed_dataset": _exists("data/processed/base_data_engine.parquet"),
        "team_dataset": _exists("data/features/team_dataset.parquet"),
        "backtest_results": _exists("data/backtest/results"),
        "ml_folder": _exists("data/ml"),
        "decision_candidates": _exists("data/decision_engine/decision_candidates.csv"),
        "last_engine_state": _safe_json("data/automation/engine_run_state.json"),
    }
    return {
        "ok": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data": {
            "product_positioning": "MatchFlow deve operar como um ERP analítico esportivo: dados, competições, backtest, ML, decisão e banca no mesmo fluxo.",
            "current_state": "base autoral/local forte, em transição para SaaS vendável",
            "target_state": "produto online multiusuário onde o Data Engine é motor interno e invisível para o cliente final",
            "pipeline_steps": PIPELINE_STEPS,
            "api_groups": API_GROUPS,
            "sellable_roadmap": SELLABLE_ROADMAP,
            "health": health,
        },
    }


@router.get("/step/{step_id}")
def step_detail(step_id: str) -> dict[str, Any]:
    step = next((s for s in PIPELINE_STEPS if s["id"] == step_id), None)
    if not step:
        return {"ok": False, "error": {"code": "STEP_NOT_FOUND", "message": "Etapa operacional não encontrada."}}
    return {"ok": True, "data": step}
