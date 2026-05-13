from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends

from backend.core.authz import require_permission, current_user, tenant_data_path

router = APIRouter(prefix="/api/data-engine", tags=["data-engine"])


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _safe_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default
    except Exception:
        return default


def _file_meta(path: Path, expose_path: bool = True) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, **({"path": str(path.relative_to(_root())) if path.is_relative_to(_root()) else str(path)} if expose_path else {})}
    stat = path.stat()
    data = {
        "exists": True,
        "size_bytes": stat.st_size,
        "updated_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
    }
    if expose_path:
        data["path"] = str(path.relative_to(_root())) if path.is_relative_to(_root()) else str(path)
    return data


def build_data_engine_status(*, public: bool = False) -> dict[str, Any]:
    root = _root()
    mode = os.getenv("DATA_ENGINE_MODE", "internal")
    state = _safe_json(root / "data/data_engine/state/flashscore_state.json", {}) if not public else {}
    flash_report = _safe_json(root / "data/reports/flashscore_sync_report.json", {}) if not public else {}
    outputs = {
        "flashscore_matches": _file_meta(root / "data/raw/flashscore_matches.parquet", expose_path=not public),
        "future_matches": _file_meta(root / "data/future_matches/future_matches_snapshot.parquet", expose_path=not public),
        "future_features": _file_meta(root / "data/features/future_features.parquet", expose_path=not public),
        "future_predictions": _file_meta(root / "data/ml/predictions/future_predictions.parquet", expose_path=not public),
        "decision_candidates": _file_meta(root / "data/decision_engine/decision_candidates.csv", expose_path=not public),
    }
    ready_outputs = [name for name, meta in outputs.items() if meta.get("exists")]
    warnings = []
    if mode != "internal":
        warnings.append("DATA_ENGINE_MODE não está em internal; use apenas para legado/demo controlado.")
    if not ready_outputs:
        warnings.append("Nenhum output operacional encontrado.")
    payload: dict[str, Any] = {
        "status": "ready" if ready_outputs else "needs_data",
        "internal_mode": mode == "internal",
        "data_engine_mode": mode,
        "flashscore_enabled": os.getenv("FLASHSCORE_ENABLED", "true").lower() not in {"0", "false", "no"},
        "last_run": state.get("last_run") or flash_report.get("generated_at"),
        "outputs_ready": ready_outputs,
        "warnings": warnings + flash_report.get("warnings", []),
        "demo_enabled": os.getenv("DATA_ENGINE_MODE", "internal").lower() == "demo" or os.getenv("FLASHSCORE_USE_DEMO", "false").lower() in {"1", "true", "yes"},
    }
    if public:
        payload["public"] = True
        payload["details"] = "redacted"
        return payload
    payload.update({
        "configured_leagues_count": flash_report.get("configured_leagues_count") or len(_safe_json(root / "backend/services/data_engine/providers/flashscore/config/leagues/leagues.json", {"leagues": []}).get("leagues", [])),
        "state_path": "data/data_engine/state/flashscore_state.json",
        "outputs": outputs,
        "provider_health": {"flashscore": "ready" if outputs["flashscore_matches"].get("exists") else "not_synced", "football_data_org": "configured" if os.getenv("FOOTBALL_DATA_API_KEY") else "not_configured", "the_odds_api": "configured" if os.getenv("ODDS_API_KEY") else "not_configured"},
        "fallback_mode": "demo/local only when DATA_ENGINE_MODE=demo or FLASHSCORE_USE_DEMO=true",
        "real_provider_enabled": os.getenv("DATA_ENGINE_MODE", "internal").lower() == "internal" and os.getenv("FLASHSCORE_USE_DEMO", "false").lower() not in {"1","true","yes"},
        "is_using_external_repo": False,
        "uses_external_repo": False,
        "next_steps": ["POST /api/data-engine/providers/flashscore/sync", "Rodar python run_full_decision_pipeline.py", "Revisar entities/unresolved e quality/report."],
    })
    return payload


@router.get("/public-status")
def public_status() -> dict[str, Any]:
    return {"ok": True, "data": build_data_engine_status(public=True)}

@router.get("/status")
def data_engine_status(user: dict = Depends(require_permission("view_data_engine"))) -> dict[str, Any]:
    return {"ok": True, "tenant_id": user.get("tenant_id"), "data": build_data_engine_status()}

@router.get('/providers/status')
def data_engine_providers_status(user: dict = Depends(require_permission("view_data_engine"))) -> dict[str, Any]:
    status = build_data_engine_status()
    return {
        'ok': True,
        'tenant_id': user.get('tenant_id'),
        'mode': status['data_engine_mode'],
        'internal_mode': status['internal_mode'],
        'providers': {
            'flashscore': {'configured': True, 'enabled': status['flashscore_enabled'], 'role': 'primary_canonical_source', 'status': status['provider_health']['flashscore'], 'state_path': status['state_path']},
            'football_data_org': {'configured': bool(os.getenv('FOOTBALL_DATA_API_KEY')), 'role': 'enrichment_only', 'env_var': 'FOOTBALL_DATA_API_KEY'},
            'the_odds_api': {'configured': bool(os.getenv('ODDS_API_KEY')), 'role': 'enrichment_only', 'env_var': 'ODDS_API_KEY'},
            'demo_fallback': {'configured': True, 'source': 'demo/local', 'warning': 'Used only when APIs/browser/local snapshots are unavailable.'},
        },
        'warnings': status['warnings'],
    }

@router.get('/providers/flashscore/status')
def flashscore_provider_status(user: dict = Depends(require_permission("view_data_engine"))) -> dict[str, Any]:
    from backend.services.data_engine.providers.flashscore import load_leagues, get_flashscore_config
    cfg = get_flashscore_config()
    loaded = load_leagues()
    status = build_data_engine_status()
    safe_cfg = dict(cfg.__dict__)
    for key in list(safe_cfg):
        if 'key' in key.lower() or 'token' in key.lower() or 'secret' in key.lower():
            safe_cfg[key] = '***redacted***'
    return {'ok': True, 'tenant_id': user.get('tenant_id'), 'provider': 'flashscore', 'mode': cfg.data_engine_mode, 'real_provider_enabled': cfg.real_provider_enabled, 'demo_enabled': cfg.use_demo, 'internal_mode': status['internal_mode'], 'config': safe_cfg, 'configured_leagues_count': loaded['total'], 'leagues_sample': loaded['leagues'][:10], 'outputs': status['outputs'], 'last_run': status['last_run'], 'warnings': loaded.get('warnings', []) + status.get('warnings', [])}

@router.post('/providers/flashscore/sync')
def flashscore_provider_sync(user: dict = Depends(require_permission("run_data_engine"))) -> dict[str, Any]:
    from backend.services.data_engine.providers.flashscore import run_flashscore_sync
    result = run_flashscore_sync()
    tenant_data_path(_root(), user, 'data_engine', 'last_sync_marker.json').write_text(json.dumps({'run_at': datetime.now(timezone.utc).isoformat(), 'user_id': user.get('user_id'), 'result_ok': bool(result)}, ensure_ascii=False), encoding='utf-8')
    return {'ok': True, 'tenant_id': user.get('tenant_id'), 'data': result}


def _report_payload(relative_path: str, default: Any) -> dict[str, Any]:
    root = _root()
    path = root / relative_path
    return {"ok": True, "data": _safe_json(path, default), "meta": _file_meta(path)}

@router.get('/providers/flashscore/report')
def flashscore_provider_report(user: dict = Depends(require_permission("view_data_engine"))) -> dict[str, Any]:
    return _report_payload('data/reports/flashscore_sync_report.json', {'ok': False, 'provider': 'flashscore', 'total_records': 0, 'warnings': ['sync_not_run_yet']})

@router.get('/entities/unresolved')
def unresolved_entities(user: dict = Depends(require_permission("view_data_engine"))) -> dict[str, Any]:
    return _report_payload('backend/services/data_engine/audit/unresolved_entities.json', [])

@router.get('/entities/conflicts')
def entity_conflicts(user: dict = Depends(require_permission("view_data_engine"))) -> dict[str, Any]:
    root = _root()
    primary = root / 'data/reports/provider_conflicts_report.json'
    if primary.exists():
        return _report_payload('data/reports/provider_conflicts_report.json', {'total_conflicts': 0, 'conflicts': []})
    return _report_payload('backend/services/data_engine/audit/conflicts_report.json', [])

@router.get('/mapping/report')
def mapping_report(user: dict = Depends(require_permission("view_data_engine"))) -> dict[str, Any]:
    return _report_payload('data/reports/entity_mapping_report.json', {'total_mappings': 0, 'review_required': 0, 'samples': []})

@router.get('/deduplication/report')
def deduplication_report(user: dict = Depends(require_permission("view_data_engine"))) -> dict[str, Any]:
    return _report_payload('data/reports/deduplication_report.json', {'duplicates_removed': 0, 'canonical_matches': 0, 'conflicts': 0})

@router.get('/quality/report')
def quality_report(user: dict = Depends(require_permission("view_data_engine"))) -> dict[str, Any]:
    return _report_payload('data/reports/data_engine_quality_report.json', {'total_records': 0, 'quality_bands': {}, 'blocked_records': 0})

@router.get('/flashscore/coverage')
def flashscore_coverage_report(user: dict = Depends(require_permission("view_data_engine"))) -> dict[str, Any]:
    try:
        from backend.services.data_engine.providers.flashscore.coverage_report import build_flashscore_coverage_report
        data = build_flashscore_coverage_report(_root())
    except Exception:
        data = _safe_json(_root() / 'data/reports/flashscore_coverage_report.json', {'ok': False, 'total_matches': 0, 'provider_warnings': ['coverage_report_unavailable']})
    return {'ok': True, 'tenant_id': user.get('tenant_id'), 'data': data}

@router.get('/providers/flashscore/validation')
def flashscore_validation_report(user: dict = Depends(require_permission("view_data_engine"))) -> dict[str, Any]:
    return _report_payload('data/reports/flashscore_live_validation_report.json', {
        'success': False,
        'provider': 'flashscore',
        'provider_health': 'not_validated',
        'live_probe_executed': False,
        'playwright_available': False,
        'browser_available': False,
        'errors': [],
        'warnings': ['validation_not_run_yet'],
        'next_steps': ['python -m playwright install chromium', 'MATCHFLOW_FLASH_SCORE_VALIDATE_LIVE=1 python scripts/validate_flashscore_provider.py'],
    })
