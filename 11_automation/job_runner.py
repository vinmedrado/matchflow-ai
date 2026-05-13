"""
job_runner.py — Orquestrador de jobs com suporte a todos os novos módulos v7.0.
Sequência: data_engine → odds_fetcher → data_ops → result_settler → test_lab →
           decision_engine → monitoring → clv_tracker → performance_report
"""
from __future__ import annotations
import importlib.util, inspect, logging, subprocess, sys, traceback
from pathlib import Path
from typing import Any, Callable, Iterable

from .automation_state import mark_run
from .common import MODE, automation_dir, load_config, load_json, save_json, utc_now

logger = logging.getLogger("matchflow.automation.job_runner")


def _load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Módulo não carregável: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _resolve(mod: Any, candidates: Iterable[str]) -> Callable:
    for name in candidates:
        fn = getattr(mod, name, None)
        if callable(fn):
            return fn
    raise AttributeError(f"Nenhum entrypoint encontrado: {list(candidates)}")


def _call(fn: Callable, root: Path) -> Any:
    sig = inspect.signature(fn)
    return fn() if len(sig.parameters) == 0 else fn(root)


def _subprocess(root: Path, label: str, rel: str) -> dict:
    t0 = utc_now()
    path = root / rel
    if not path.exists():
        return {"job": label, "status": "SKIPPED", "reason": f"Not found: {rel}", "started_at": t0, "finished_at": utc_now()}
    logger.info("Job %s via subprocess: %s", label, rel)
    r = subprocess.run([sys.executable, str(path)], cwd=str(root), text=True, capture_output=True)
    return {
        "job": label,
        "status": "SUCCESS" if r.returncode == 0 else "FAILED",
        "started_at": t0, "finished_at": utc_now(),
        "returncode": r.returncode,
        "stdout": r.stdout[-3000:],
        "stderr": r.stderr[-2000:],
    }


def _run(root: Path, label: str, rel: str, entrypoints: Iterable[str],
         subprocess_fallback: bool = True) -> dict:
    t0 = utc_now()
    path = root / rel
    if not path.exists():
        return {"job": label, "status": "SKIPPED", "reason": f"Not found: {rel}", "started_at": t0, "finished_at": utc_now()}
    try:
        logger.info("Executando job: %s", label)
        mod = _load_module(path, f"mf_job_{label}")
        fn = _resolve(mod, entrypoints)
        result = _call(fn, root)
        if isinstance(result, int) and result != 0:
            return {"job": label, "status": "FAILED", "error": f"returncode={result}", "started_at": t0, "finished_at": utc_now()}
        return {"job": label, "status": "SUCCESS", "started_at": t0, "finished_at": utc_now(), "result": result}
    except (ImportError, AttributeError) as exc:
        logger.warning("Job %s fallback: %s", label, exc)
        if subprocess_fallback:
            fb = _subprocess(root, label, rel)
            if fb.get("status") == "SUCCESS":
                fb["fallback_reason"] = str(exc)
                return fb
        return {"job": label, "status": "FAILED", "error": str(exc), "trace": traceback.format_exc(3), "started_at": t0, "finished_at": utc_now()}
    except Exception as exc:
        logger.exception("Job %s falhou: %s", label, exc)
        return {"job": label, "status": "FAILED", "error": str(exc), "trace": traceback.format_exc(3), "started_at": t0, "finished_at": utc_now()}



def _run_optional(root: Path, label: str, rel: str, entrypoints: Iterable[str], subprocess_fallback: bool = True) -> dict:
    """Legacy compatibility wrapper retained for Patch 6.0.1 tests.

    The current orchestrator uses _run(), but historical callers still import
    _run_optional directly. This delegates to the current implementation without
    changing job semantics.
    """
    return _run(root, label, rel, entrypoints, subprocess_fallback=subprocess_fallback)


def _run_inline(root: Path, label: str, fn: Callable) -> dict:
    """Executa uma função Python diretamente (sem carregar arquivo)."""
    t0 = utc_now()
    try:
        logger.info("Executando job inline: %s", label)
        result = fn(root)
        return {"job": label, "status": "SUCCESS", "started_at": t0, "finished_at": utc_now(), "result": result}
    except Exception as exc:
        logger.exception("Job inline %s falhou: %s", label, exc)
        return {"job": label, "status": "FAILED", "error": str(exc), "started_at": t0, "finished_at": utc_now()}


def append_history(root: Path, record: dict) -> None:
    path = automation_dir(root) / "job_history.json"
    history = load_json(path, {"mode": MODE, "runs": []})
    runs = history.get("runs", [])
    runs.append(record)
    save_json(path, {"mode": MODE, "runs": runs[-100:]})


def _run_data_engine(root: Path) -> dict:
    """Executa o provider interno FlashScore. Legacy externo não é usado no fluxo principal."""
    try:
        from backend.services.data_engine.providers.flashscore import run_flashscore_sync
        result = run_flashscore_sync(max_leagues=2, test_mode=True)
        return {"status": "SUCCESS" if result.get("ok") else "ERROR", "uses_external_repo": False, "result": result}
    except Exception as exc:
        logger.warning("data_engine interno falhou (não crítico): %s", exc)
        return {"status": "ERROR", "uses_external_repo": False, "error": str(exc)}


def run_jobs(root: Path | None = None) -> dict[str, Any]:
    root = root or Path.cwd()
    config = load_config(root)
    configured_jobs = config.get("jobs", [])
    t0 = utc_now()
    jobs = []

    # ── FASE 0: FlashScore Engine (fonte primária de dados) ──────────────
    if "data_engine" in configured_jobs:
        jobs.append(_run_inline(root, "data_engine", lambda r: _run_data_engine(r)))

    # ── FASE 1: Dados externos ────────────────────────────────────────────
    if "odds_fetcher" in configured_jobs:
        jobs.append(_run(root, "odds_fetcher", "07_data_ops/odds_fetcher.py",
                         ["fetch_all_odds", "main"]))

    if "data_ops" in configured_jobs:
        jobs.append(_run(root, "data_ops", "07_data_ops/run_data_ops.py",
                         ["run_data_ops", "main"]))

    if "odds_monitor" in configured_jobs:
        jobs.append(_run(root, "odds_monitor", "07_data_ops/odds_monitor.py",
                         ["build_odds_movement_report", "main"]))

    # ── FASE 2: Liquidação automática ─────────────────────────────────────
    if "result_settler" in configured_jobs:
        jobs.append(_run(root, "result_settler", "07_data_ops/result_settler.py",
                         ["settle_pending_bets", "main"]))

    # ── FASE 3: Análise e ML ──────────────────────────────────────────────
    if "test_lab" in configured_jobs:
        jobs.append(_run(root, "test_lab", "08_test_lab/test_lab_runner.py",
                         ["run_test_lab", "main"]))

    if "decision_engine" in configured_jobs:
        jobs.append(_run(root, "decision_engine", "09_decision_engine/decision_engine.py",
                         ["run_decision_engine", "main"]))

    if "monitoring" in configured_jobs:
        jobs.append(_run(root, "monitoring", "10_monitoring/run_monitoring.py",
                         ["run_monitoring", "main"]))

    # ── FASE 4: Performance e CLV ─────────────────────────────────────────
    if "clv_tracker" in configured_jobs:
        jobs.append(_run(root, "clv_tracker", "09_decision_engine/clv_tracker.py",
                         ["update_clv_for_settled_bets", "main"]))

    if "performance_report" in configured_jobs:
        jobs.append(_run(root, "performance_report", "09_decision_engine/performance_attributor.py",
                         ["generate_performance_report", "main"]))

    if "monte_carlo" in configured_jobs:
        jobs.append(_run(root, "monte_carlo", "04_backtest/analysis/monte_carlo.py",
                         ["save_monte_carlo_report", "main"]))

    # ── Status final ──────────────────────────────────────────────────────
    failed = [j for j in jobs if j["status"] == "FAILED"]
    status = "SUCCESS" if not failed else "PARTIAL" if len(failed) < len(jobs) else "FAILED"

    record = {
        "mode": MODE,
        "started_at": t0,
        "finished_at": utc_now(),
        "status": status,
        "jobs": jobs,
        "failed_jobs": [j["job"] for j in failed],
    }
    append_history(root, record)
    mark_run(root, status)
    save_json(automation_dir(root) / "last_run_summary.json", record)
    logger.info("Jobs finalizados: status=%s total=%s failed=%s", status, len(jobs), len(failed))
    return record
