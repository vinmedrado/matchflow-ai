# MatchFlow Monitoring & Production Maturity

## What is monitored
- FlashScore provider health and coverage.
- Odds/stat/event coverage from `data/reports/flashscore_coverage_report.json`.
- ML calibration from `data/ml/calibration/calibration_report.json`.
- Drift from `data/monitoring/drift_report.json`.
- Job history from `data/jobs/job_history.json`.

## Main endpoints
- `GET /metrics`
- `GET /api/monitoring/drift`
- `GET /api/data-engine/flashscore/coverage`
- `GET /api/ml/calibration/report`
- `GET /api/jobs`
- `POST /api/jobs/run/full_decision_pipeline`

All outputs remain `PAPER_TRADING_SIMULATION_ONLY` and never imply real automated action.
