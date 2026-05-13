# ML Pipeline

The future prediction flow uses real future features and three configured model slots: Random Forest, LightGBM and XGBoost. When optional libraries or trained artifacts are unavailable, the pipeline keeps explicit fallback artifacts and warnings instead of fixed probabilities.

Calibration writes:

- `data/ml/calibration/calibration_report.json`
- `data/ml/calibration/calibrated_model_registry.json`

Future predictions include raw and calibrated ensemble probabilities:

- `raw_ensemble_probability`
- `calibrated_ensemble_probability`
- `calibration_quality_score`
