
## Parquet engine troubleshooting

Parquet is recommended for normal MatchFlow operation. Install `pyarrow` first and keep `fastparquet` as a secondary engine:

```bash
pip install pyarrow fastparquet
```

If neither engine is installed, the backend storage helper automatically falls back to CSV for generated artifacts. This keeps demo, CI and lightweight deploy environments operational while still warning clearly that Parquet support is unavailable. Check `/api/system/status` and inspect `data.storage` for the active engine and fallback state.

## Parquet / CSV fallback

Parquet is recommended for production because it is compact and fast. Install `pyarrow` and optionally `fastparquet`. If the runtime does not have either engine, MatchFlow uses the central storage helper in `backend/core/storage.py` and falls back to CSV for the main pipelines.

Useful diagnostics:

```bash
python -c "from backend.core.storage import storage_status; print(storage_status())"
MATCHFLOW_DISABLE_PARQUET=1 python run_full_decision_pipeline.py
```

Status endpoints expose storage information through `/ready` and `/api/system/status`.
