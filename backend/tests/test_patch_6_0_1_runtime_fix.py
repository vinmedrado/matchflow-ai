from __future__ import annotations

import importlib
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_module(rel: str):
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    module_name = rel.replace('\\\\', '/').replace('/', '.').removesuffix('.py')
    return importlib.import_module(module_name)


def test_data_ops_entrypoint_exists_and_runs_without_attribute_error():
    module = _load_module('07_data_ops/run_data_ops.py')
    assert hasattr(module, 'run_data_ops')
    result = module.run_data_ops(PROJECT_ROOT)
    assert isinstance(result, dict)
    assert 'status' in result
    assert 'AttributeError' not in json.dumps(result, ensure_ascii=False)


def test_monitoring_runs_as_direct_script_without_import_error():
    completed = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / '10_monitoring/run_monitoring.py')],
        cwd=str(PROJECT_ROOT),
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0
    combined = completed.stdout + completed.stderr
    assert 'attempted relative import with no known parent package' not in combined
    assert 'ImportError' not in combined


def test_job_runner_executes_data_ops_without_attribute_error():
    job_runner = _load_module('11_automation/job_runner.py')
    result = job_runner._run_optional(PROJECT_ROOT, 'data_ops', '07_data_ops/run_data_ops.py', ['run_data_ops', 'main'])
    assert result['status'] == 'SUCCESS'
    assert 'AttributeError' not in json.dumps(result, ensure_ascii=False)


def test_job_runner_executes_monitoring_without_import_error():
    job_runner = _load_module('11_automation/job_runner.py')
    result = job_runner._run_optional(PROJECT_ROOT, 'monitoring', '10_monitoring/run_monitoring.py', ['run_monitoring', 'main'])
    assert result['status'] == 'SUCCESS'
    assert 'ImportError' not in json.dumps(result, ensure_ascii=False)


def test_run_automation_has_no_import_or_entrypoint_failures():
    automation = _load_module('11_automation/run_automation.py')
    result = automation.run_automation(PROJECT_ROOT)
    serialized = json.dumps(result, ensure_ascii=False)
    assert result['status'] in {'SUCCESS', 'WARNING'}
    assert "has no attribute 'run_data_ops'" not in serialized
    assert 'attempted relative import with no known parent package' not in serialized
    assert 'ImportError' not in serialized
