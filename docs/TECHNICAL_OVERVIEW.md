# MatchFlow — AI Sports Intelligence Platform

MatchFlow é uma plataforma de inteligência esportiva AI-native para transformar dados de futebol em pipelines de dados, backtests, modelos de ML, decision engine, paper trading, analytics e camadas executivas/cognitivas de apoio à decisão.

> Modo seguro padrão: `PAPER_TRADING_SIMULATION_ONLY`. O sistema não executa apostas reais automaticamente.

## Proposta de valor

- Centralizar coleta, validação e enriquecimento de dados de futebol.
- Testar mercados com backtest e métricas de risco antes de qualquer decisão.
- Usar ML/AI Brain/Copilot para explicar sinais, risco, confiança e contexto operacional.
- Apresentar uma experiência premium para portfólio, demo técnica, clientes e recrutadores.

## Arquitetura geral

- **Backend:** FastAPI com routers modulares em `backend/api`.
- **Frontend:** React + Vite em `frontend/`.
- **Data Engine Ops:** orquestra o provider interno FlashScore e alimenta os parquets/CSVs operacionais.
- **ML Pipeline:** features, treino, calibração, predictions e registry.
- **Decision Engine:** candidatos, EV, confidence, thresholds e explicabilidade.
- **Paper Trading:** simulação, banca, métricas e relatórios.
- **AI Brain / Agents / Cognitive / Executive / Evolution:** camadas auditáveis de análise, governança, raciocínio, memória e evolução.

## Módulos principais

- Dashboard
- Data Operations
- Team Analytics
- Backtest Lab
- ML Lab / ML Intelligence
- Decision Engine
- Paper Trading Premium
- AI Copilot Premium
- Live Center
- Executive Cockpit
- Cognitive Workspace
- Evolution Cockpit

## Data Engine

O Data Engine principal é interno em `backend/services/data_engine/providers/flashscore/` e não depende de repositório externo.

Status operacional:

- `GET /api/data-engine/status`
- `GET /api/data-ops/status`
- `GET /api/data-ops/engine-status`

Leia: [`docs/DATA_ENGINE_OPS.md`](docs/DATA_ENGINE_OPS.md).

## APIs principais

Health/readiness:

- `GET /health`
- `GET /ready`
- `GET /api/health/status`

Workspaces AI:

- `GET /api/autonomous/workspace`
- `GET /api/cognitive/workspace`
- `GET /api/executive/workspace`
- `GET /api/evolution/workspace`

Status aliases:

- `GET /api/autonomous/status`
- `GET /api/cognitive/status`
- `GET /api/executive/status`
- `GET /api/evolution/status`

Demo:

- `GET /api/demo/status`
- `GET /api/platform/demo-mode`

## Setup local

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements-backend.txt
cp .env.example .env
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Frontend:

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

## Produção

```bash
cp .env.production.example .env.production
docker compose -f docker-compose.prod.yml up --build
```

Produção usa uvicorn sem `--reload` e workers configuráveis por `UVICORN_WORKERS`. Leia [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

## Demo

```bash
# .env
DEMO_MODE=true
APP_MODE=PAPER_TRADING_SIMULATION_ONLY
```

Usuário local: `admin@matchflow.local` / `admin123`. Leia [`docs/DEMO_GUIDE.md`](docs/DEMO_GUIDE.md).

## Testes e build

```bash
pytest backend/tests
python -m compileall backend 01_scripts 02_validation 03_features 04_backtest 05_paper_trading 06_ml 07_data_ops 08_test_lab 09_decision_engine 10_monitoring 11_automation
cd frontend && npm install && npm run build
```

## Troubleshooting

- **401 no frontend:** faça login com usuário local ou configure `AUTH_ENABLED=false` apenas em ambiente controlado.
- **API offline:** confira `VITE_API_BASE` e `GET /health`.
- **Sem dados:** confira `GET /api/data-engine/status` e rode `python run_data_ops_pipeline.py`.
- **CORS:** ajuste `CORS_ORIGINS` no `.env`.
- **Parquet:** garanta `pyarrow` ou `fastparquet` instalados.

## Roadmap realista

- Persistência PostgreSQL para jobs, usuários e histórico operacional.
- Worker dedicado para Data Engine e filas.
- Multi-tenant/RBAC real.
- Observabilidade externa com tracing e error tracking.
- Demo pública hospedada com dataset demo versionado.


## Operational Core Pipeline

The operational flow is documented in `docs/OPERATIONAL_CORE_PIPELINE.md`.

Quick run:

```bash
python run_full_decision_pipeline.py
```

Core endpoints:

- `/api/future-matches/snapshot`
- `/api/ml/future-predictions`
- `/api/decision-engine/candidates`
- `/api/decision-engine/summary`
- `/api/data-engine/providers/status`
- `/api/bankroll/profiles`

Supported provider configuration is available in `.env.example`: Football-Data.org, The Odds API, internal FlashScore provider, local parquet files and demo fallback. All final candidates remain `PAPER_TRADING_SIMULATION_ONLY` and require manual confirmation. No real action is automated.

## Data Engine Consolidation

O MatchFlow agora possui uma camada interna de consolidação de providers. FlashScore interno é tratado como fonte primária/canônica para campos ricos. Football-Data.org e The Odds API enriquecem somente campos vazios, ausentes ou de baixa qualidade, sem sobrescrever dados confiáveis do FlashScore.

Principais garantias:

- resolução canônica de times e ligas com RapidFuzz;
- Groq opcional apenas para casos ambíguos e cacheados;
- `match_identity_key` para deduplicar partidas entre fontes;
- relatórios de conflitos, deduplicação, entidades não resolvidas e data quality;
- ML/backtest/Decision Engine usam registros canônicos e bloqueiam dados `blocked`;
- endpoints operacionais em `/api/data-engine/*`.

Documentação completa: `docs/DATA_ENGINE_CONSOLIDATION.md`.


## Internal FlashScore Data Engine

O MatchFlow agora roda com Data Engine interno (`DATA_ENGINE_MODE=internal`) em `backend/services/data_engine/providers/flashscore/`. O repo/pasta `internal FlashScore provider` externo virou legado opcional e não é necessário para instalar, vender ou demonstrar o produto. Consulte `docs/DATA_ENGINE_INTERNAL_FLASHSCORE.md`.

## Internal FlashScore Provider (Release Update)

The MatchFlow Data Engine is now self-contained. The main provider lives at:

`backend/services/data_engine/providers/flashscore/`

The external `internal FlashScore provider` repository/folder is no longer required for the main operational flow. `internal provider setting` remains only as a deprecated legacy compatibility option and is ignored unless `internal provider setting=true`.

Default behavior:

- `DATA_ENGINE_MODE=internal`
- `DATA_ENGINE_PRIMARY_PROVIDER=flashscore`
- `FLASHSCORE_USE_DEMO=false`
- real Playwright scraping is attempted when available;
- demo data is only produced with `DATA_ENGINE_MODE=demo` or `FLASHSCORE_USE_DEMO=true`;
- if Playwright/browser is unavailable, the provider returns explicit warnings and does not silently mark demo data as real.

Operational commands:

```bash
python -m playwright install chromium   # optional for real browser scraping
python run_full_decision_pipeline.py
```

Data Engine endpoints:

- `GET /api/data-engine/status`
- `GET /api/data-engine/providers/status`
- `GET /api/data-engine/providers/flashscore/status`
- `POST /api/data-engine/providers/flashscore/sync`
- `GET /api/data-engine/providers/flashscore/report`

Outputs:

- `data/raw/flashscore_matches.parquet`
- `data/raw/flashscore_matches.csv`
- `data/raw/flashscore_odds.parquet`
- `data/raw/flashscore_stats.parquet`
- `data/reports/flashscore_sync_report.json`


## FlashScore Scraper Production Hardening

MatchFlow now uses an internal FlashScore provider as the primary Data Engine source. The provider is located at `backend/services/data_engine/providers/flashscore/` and does not require an external `internal FlashScore provider` repository.

Production behavior:

- Network/XHR capture is preferred for structured fixtures, odds, stats and events.
- DOM/text parsing is only a conservative fallback.
- Demo data is not the main flow and only runs with `DATA_ENGINE_MODE=demo` or `FLASHSCORE_USE_DEMO=true`.
- Missing fields remain null and are tracked through provider warnings and data-quality reports.
- Outputs feed mapping, deduplication, data quality, future features, ML predictions, Test Lab and Decision Engine.

Useful commands:

```bash
python -m playwright install chromium
python run_full_decision_pipeline.py
pytest backend/tests
cd frontend && npm install && npm run build
```

Operational docs: `docs/DATA_ENGINE_OPS.md`.


## Production Maturity Patch

This release adds final production-readiness polish without changing the core architecture:

- deeper FlashScore parsing and coverage reporting;
- ML calibration reports and calibrated future probabilities;
- drift monitoring for features, predictions, confidence and data quality;
- operational monitoring dashboard updates;
- scheduler/background job endpoints;
- JSON-style observability with request IDs and `/metrics`;
- production Dockerfile and `docker-compose.prod.yml`;
- GitHub Actions CI for backend tests, frontend build and clean artifact checks.

### Production commands

```bash
pip install -r requirements.txt
python run_full_decision_pipeline.py
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Production container command uses Gunicorn/Uvicorn workers via `Dockerfile.prod`.

### Scheduler endpoints

```text
GET  /api/jobs
GET  /api/jobs/history
POST /api/jobs/run/full_decision_pipeline
GET  /api/jobs/{job_id}
```

### Monitoring endpoints

```text
GET /metrics
GET /api/monitoring/drift
GET /api/data-engine/flashscore/coverage
GET /api/ml/calibration/report
```

## Production maturity: calibration, drift and model health

The final production maturity layer adds settled-result calibration and advanced drift monitoring without changing the main architecture.

Key endpoints:

- `GET /api/ml/calibration/report`
- `POST /api/ml/settled-predictions/sync`
- `GET /api/ml/model-health`
- `GET /api/monitoring/drift`
- `GET /api/monitoring/alerts`
- `POST /api/jobs/run/calibration_refresh`
- `POST /api/jobs/run/drift_analysis`
- `POST /api/jobs/run/model_health_analysis`

See:

- `docs/ML_PIPELINE.md`
- `docs/MONITORING.md`

## Real Settled Results Calibration

MatchFlow separates real settled results from paper, backtest and demo outcomes. Real ML calibration only uses `settlement_source_type=real` records from canonical Data Engine/FlashScore outcomes. If the real sample is insufficient, calibration is clearly marked as fallback and evidence alerts are generated.

See `docs/ML_CALIBRATION_REAL_SETTLEMENT.md`.

## Branding e Landing Page

O frontend inclui identidade visual premium do **MatchFlow AI** em `frontend/src/assets/brand/`, com logo principal, versão compacta reutilizada no header/login e favicon. A entrada pública do app agora abre uma landing page leve antes do login, apresentando o produto como uma plataforma AI-native de inteligência futebolística.

A landing page (`frontend/src/pages/LandingPage.jsx`) usa animações CSS sutis relacionadas a futebol, dados e IA: campo em grid neon, pontos táticos, bola minimalista, linha de sinal e cards com fade/slide. As animações respeitam `prefers-reduced-motion` e não usam canvas pesado.

Seções apresentadas:
- Data Engine interno com FlashScore, enrichment, mapping, deduplication e data quality.
- Machine Learning com Random Forest, LightGBM, XGBoost, calibration e drift monitoring.
- Decision Engine com EV, confidence, risk e bankroll simulation.
- Monitoring com scheduler, jobs, coverage, health e alerts.
- Safety com aviso de paper trading simulation only e sem ação real automática.

## MatchFlow AI — Premium UI & Motion Polish

This release adds a premium SaaS landing experience and lightweight motion system without changing backend, Data Engine, ML, Backtest or Decision Engine logic.

### Frontend polish included

- Premium landing hero using the MatchFlow AI logo.
- Lightweight football/data/AI motion: tactical grid, data lines, signal trace, soft particles and live status pulses.
- Product preview mock dashboard for Decision Engine, Monitoring and ML Calibration.
- Visual pipeline: FlashScore → Enrichment → Mapping → ML Ensemble → Calibration → Drift Monitoring → Decision Engine → Paper Trading.
- Microinteractions for buttons, cards, navigation, metrics, loading and empty states.
- Premium table polish with sticky headers, subtle hover states and confidence-ready styles.
- Reduced-motion support through `prefers-reduced-motion`.

### QA

Run:

```bash
cd frontend
npm install
npm run build
```

The patch is visual only and does not modify operational backend pipelines.

## Storage robustness: Parquet with CSV fallback

MatchFlow prefers Parquet for production data artifacts because it is compact and fast. The storage layer now detects the available Parquet engine at runtime using this order:

1. `pyarrow`
2. `fastparquet`
3. CSV fallback

Core pipelines should use `backend.core.storage.safe_read_dataframe()` and `safe_write_dataframe()` instead of direct `pandas.read_parquet()` / `DataFrame.to_parquet()` calls. If no Parquet engine is available, MatchFlow writes a `.csv` file next to the requested `.parquet` path and records clear metadata such as `storage_format`, `parquet_available`, `parquet_engine`, `fallback_used`, `fallback_reason`, `csv_path` and `parquet_path` in summaries/reports when available.

Recommended install:

```bash
pip install pyarrow fastparquet
```

Diagnostics are exposed in `/api/system/status` under `data.storage` with `parquet_available`, `parquet_engine`, `storage_fallback_enabled` and `recommended_install`.

## Storage robustness: Parquet preferred, CSV fallback

MatchFlow now uses `backend/core/storage.py` as the central dataframe storage layer across the main operational flows. Parquet remains the preferred production format, with `pyarrow` preferred first and `fastparquet` as the secondary engine. When neither engine is available, the system writes and reads CSV fallbacks next to the requested `.parquet` path instead of crashing the pipeline.

Operational behavior:

- `get_parquet_engine()` detects `pyarrow` then `fastparquet`.
- `safe_write_dataframe()` writes Parquet when possible and CSV fallback when needed.
- `safe_read_dataframe()` attempts Parquet first, then the equivalent CSV file.
- Summary/report JSON files include storage metadata when available: `parquet_available`, `parquet_engine`, `fallback_used`, `storage_format`, `parquet_path`, and `csv_path`.
- `MATCHFLOW_DISABLE_PARQUET=1` can be used in CI or constrained environments to force CSV fallback and validate deployment resilience.
- `/ready` and `/api/system/status` expose storage status including Parquet availability and recommended install command.

Recommended install:

```bash
pip install pyarrow fastparquet
```

Fallback validation:

```bash
MATCHFLOW_DISABLE_PARQUET=1 python run_full_decision_pipeline.py
pytest backend/tests/test_parquet_fallback_pipeline_coverage.py
```

## Final Technical Polish

- Data Engine principal: `backend/services/data_engine/providers/flashscore/`.
- Integrações legadas com `internal FlashScore provider` externo estão deprecated e fora do fluxo principal.
- Demo segura: `DATA_ENGINE_MODE=demo FLASHSCORE_USE_DEMO=true python run_full_decision_pipeline.py`.
- Validação operacional do FlashScore: `python scripts/validate_flashscore_provider.py`.
- Último relatório: `GET /api/data-engine/providers/flashscore/validation`.

Veja `docs/FINAL_TECHNICAL_POLISH.md`.

## SaaS Auth, Multiuser and Tenant Isolation

MatchFlow AI now uses the internal SaaS auth manager by default (`AUTH_MODE=saas`). It creates a persistent auth database at `data/auth/matchflow_auth.sqlite3` for local/demo usage and keeps the schema compatible with production concepts: users, tenants, roles, refresh tokens, reset tokens and verification tokens.

Default local/demo users:

- `admin@matchflow.local / admin123` — ADMIN
- `analyst@matchflow.local / analyst123` — analyst user allowed to run lab flows
- `viewer@matchflow.local / viewer123` — read-only viewer
- `demo@matchflow.local / demo123` — DEMO tenant user

Email verification is implemented but disabled by default:

```env
EMAIL_VERIFICATION_ENABLED=false
```

When disabled, users can use the system normally and the API returns `verification_pending_optional=true`. When enabled, the same token tables/endpoints are ready to enforce verification after a mail provider is configured.

Main auth endpoints:

- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/refresh`
- `POST /api/auth/logout`
- `GET /api/auth/me`
- `GET/PATCH /api/auth/profile`
- `POST /api/auth/forgot-password`
- `POST /api/auth/reset-password`
- `POST /api/auth/verify-email`
- `POST /api/auth/resend-verification`
- `GET /api/auth/status`

Production note: set real secrets, production CORS origins, a managed database URL if promoted beyond local SQLite, and enable HTTPS before public exposure.
