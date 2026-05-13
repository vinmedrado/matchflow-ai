from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    from .alert_dispatcher import dispatch_alerts
    from .automation_state import load_state, save_state
    from .common import MODE, automation_dir, load_config, save_json, utc_now
    from .export_engine import export_candidates
    from .job_runner import run_jobs
    from .report_generator import generate_daily_report
except ImportError:  # execução direta por caminho
    import sys
    base = Path(__file__).resolve().parents[1]
    if str(base) not in sys.path:
        sys.path.insert(0, str(base))
    from importlib import import_module
    dispatch_alerts = import_module("11_automation.alert_dispatcher").dispatch_alerts
    load_state = import_module("11_automation.automation_state").load_state
    save_state = import_module("11_automation.automation_state").save_state
    MODE = import_module("11_automation.common").MODE
    automation_dir = import_module("11_automation.common").automation_dir
    load_config = import_module("11_automation.common").load_config
    save_json = import_module("11_automation.common").save_json
    utc_now = import_module("11_automation.common").utc_now
    export_candidates = import_module("11_automation.export_engine").export_candidates
    run_jobs = import_module("11_automation.job_runner").run_jobs
    generate_daily_report = import_module("11_automation.report_generator").generate_daily_report


def run_automation(root: Path | None = None) -> dict[str, Any]:
    root = root or Path.cwd()
    config = load_config(root)
    started = utc_now()
    job_result = run_jobs(root)
    export_result = export_candidates(root)
    alert_result = dispatch_alerts(root)
    report_result = generate_daily_report(root)

    state = load_state(root)
    state["overall_status"] = "SUCCESS" if job_result.get("status") == "SUCCESS" else "WARNING"
    state["last_run_at"] = started
    state["last_completed_at"] = utc_now()
    state["mode"] = MODE
    save_state(root, state)

    summary = {
        "mode": MODE,
        "paper_only": True,
        "started_at": started,
        "finished_at": utc_now(),
        "status": state["overall_status"],
        "ml_training_auto_run": False,
        "jobs": job_result,
        "export": export_result,
        "alerts": {"total_dispatched": alert_result.get("total_dispatched", 0)},
        "report": report_result,
        "safety_message": "Este sistema NÃO executa apostas reais e NÃO gera recomendação financeira direta.",
    }
    save_json(automation_dir(root) / "last_run_summary.json", summary)
    return summary


if __name__ == "__main__":
    result = run_automation(Path.cwd())
    print(result)  # CLI local; backend não depende deste print.
