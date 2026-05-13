# Real Settled Results Calibration

MatchFlow separates evidence sources before calibration:

- `real`: results settled from canonical Data Engine / FlashScore outcomes.
- `paper`: paper-trading outcomes.
- `backtest`: historical simulation outcomes.
- `demo`: explicit demo data.
- `unknown`: records that cannot be safely classified.

Only records with `settlement_source_type = real` and `is_settled = true` are eligible for real ML calibration. Paper, backtest and demo records are still useful for dashboards and testing, but they are never mixed silently into real calibration.

## Canonical outputs

- `data/results/real_settled_results.parquet`
- `data/results/real_settled_results.csv`
- `data/results/real_settled_results_summary.json`
- `data/results/paper_settled_results.parquet`
- `data/results/backtest_settled_results.parquet`
- `data/results/demo_settled_results.parquet`
- `data/ml/settled_predictions.parquet` with `settlement_source_type`
- `data/ml/calibration/calibration_report.json`
- `data/monitoring/evidence_alerts.json`

## Calibration rules

Real calibration requires at least 30 real settled rows by default. If the real sample is smaller, the report returns:

- `calibration_mode = fallback`
- `calibration_source = insufficient_real_settled_results`
- `is_real_calibration = false`
- `uses_backtest_data = false`
- `uses_paper_data = false`
- `uses_demo_data = false`

Fallback is conservative and clearly marked. It does not pretend to be real evidence.

## Reliability metrics

When enough real settled results exist, MatchFlow computes Brier score, log loss, ECE, MCE, reliability bins and model-level reliability.

## Model health source awareness

`/api/ml/model-health` includes `health_source_type`, `real_evidence_score`, `fallback_evidence_score`, `evidence_quality` and `reliability_status`.

## Evidence alerts

`/api/monitoring/evidence-alerts` warns when real calibration is unavailable, real sample size is low, fallback data exists but is excluded, or a model has no real evidence.

## Scheduler jobs

- `real_settled_results_sync`
- `calibration_real_refresh`
- `evidence_quality_check`
