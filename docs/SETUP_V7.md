# MatchFlow Analytics v7.0 — Setup Rápido

## 1. Configurar variáveis de ambiente
```bash
cp .env.example .env
# Editar .env com suas chaves
```

### APIs necessárias (todas gratuitas):
| API | Link | Uso |
|-----|------|-----|
| Football-Data.org | https://www.football-data.org/client/register | Dados históricos |
| The Odds API | https://the-odds-api.com | Odds em tempo real |
| Groq API | https://console.groq.com/keys | AI Assistant (Llama 3.3 70B) |
| Telegram Bot | @BotFather no Telegram | Notificações |

## 2. Instalar dependências
```bash
pip install -r requirements.txt
```

## 3. Executar localmente
```bash
# Terminal 1: Backend
uvicorn backend.main:app --reload

# Terminal 2: Frontend
cd frontend && npm install && npm run dev

# Terminal 3: Scheduler (automático)
python start_scheduler.py
```

## 4. Docker (recomendado para produção)
```bash
cp .env.example .env   # configurar variáveis
docker-compose up -d
```

## 5. Verificar funcionamento
- Frontend: http://localhost:5173
- API: http://localhost:8000/docs
- Scheduler: logs/scheduler.log

## 6. Primeiro uso — popular dados históricos
```bash
# Após configurar FOOTBALL_DATA_API_KEY no .env:
cd football-saas
python 07_data_ops/football_data_connector.py
```

## Módulos v7.0 implementados
| Módulo | Arquivo | Status |
|--------|---------|--------|
| Dados históricos reais | `07_data_ops/football_data_connector.py` | ✅ |
| Odds em tempo real | `07_data_ops/odds_fetcher.py` | ✅ |
| Monitor de odds/sharp money | `07_data_ops/odds_monitor.py` | ✅ |
| Liquidação automática | `07_data_ops/result_settler.py` | ✅ |
| True EV (vig removida) | `09_decision_engine/market_pricer.py` | ✅ |
| CLV Tracker | `09_decision_engine/clv_tracker.py` | ✅ |
| Explicabilidade por aposta | `09_decision_engine/bet_explainer.py` | ✅ |
| Performance attribution | `09_decision_engine/performance_attributor.py` | ✅ |
| Kelly Calculator | `04_backtest/engine/kelly_calculator.py` | ✅ |
| Portfolio Kelly (correlação) | `04_backtest/engine/portfolio_optimizer.py` | ✅ |
| Significance Gate | `04_backtest/analysis/significance_tester.py` | ✅ |
| Monte Carlo | `04_backtest/analysis/monte_carlo.py` | ✅ |
| Telegram Notifier | `11_automation/telegram_notifier.py` | ✅ |
| Groq AI Assistant | `backend/services/groq_service.py` | ✅ |
| APScheduler | `11_automation/scheduler.py` | ✅ |
| Dashboard v7 | `frontend/src/pages/Dashboard.jsx` | ✅ |
| Decision Engine UI v7 | `frontend/src/pages/DecisionEngine.jsx` | ✅ |
| Automation UI v7 | `frontend/src/pages/Automation.jsx` | ✅ |
| Bankroll Projection | `frontend/src/pages/BankrollProjection.jsx` | ✅ |

## Variáveis críticas no .env
```
APP_MODE=PAPER_TRADING_SIMULATION_ONLY  # ou LIVE_RESEARCH para habilitar sinais
FOOTBALL_DATA_API_KEY=...
ODDS_API_KEY=...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
GROQ_API_KEY=...
INITIAL_BANKROLL=1000.0
KELLY_FRACTION=0.25
```
