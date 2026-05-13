# FINAL TECHNICAL POLISH

Current release note: MatchFlow uses the internal FlashScore provider at `backend/services/data_engine/providers/flashscore/` as the primary Data Engine. The main pipeline, API, tests, scheduler, demo and validation commands are self-contained and require no standalone data-engine repository.

Operational commands:

- `python run_full_decision_pipeline.py`
- `python scripts/validate_flashscore_provider.py`
- `GET /api/data-engine/status`
- `GET /api/data-engine/providers/flashscore/validation`
