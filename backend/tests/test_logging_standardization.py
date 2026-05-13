from __future__ import annotations

import ast
from pathlib import Path

from backend.core.logging_config import DEFAULT_DATE_FORMAT, DEFAULT_LOG_FORMAT, configure_logging, get_logger

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_PATHS = [
    PROJECT_ROOT / "backend",
    PROJECT_ROOT / "03_features",
    PROJECT_ROOT / "01_scripts",
    PROJECT_ROOT / "02_validation",
]
RUNTIME_FILES = [
    PROJECT_ROOT / "run_data_engine_pipeline.py",
    PROJECT_ROOT / "run_team_dataset_pipeline.py",
]


def test_logging_config_initializes_standard_logger():
    configure_logging(force=True)
    logger = get_logger("matchflow.tests.logging")
    assert logger.name == "matchflow.tests.logging"
    assert "%(levelname)s" in DEFAULT_LOG_FORMAT
    assert DEFAULT_DATE_FORMAT == "%Y-%m-%d %H:%M:%S"


def test_backend_and_pipelines_do_not_use_print_calls():
    files = []
    for base in BACKEND_PATHS:
        if base.exists():
            files.extend(base.rglob("*.py"))
    files.extend([p for p in RUNTIME_FILES if p.exists()])

    offenders = []
    for path in files:
        if "__pycache__" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
                offenders.append(f"{path.relative_to(PROJECT_ROOT)}:{node.lineno}")

    assert offenders == []


def test_core_modules_use_standard_logging_config():
    expected_files = [
        PROJECT_ROOT / "backend" / "services" / "dataset_service.py",
        PROJECT_ROOT / "backend" / "services" / "quality_service.py",
        PROJECT_ROOT / "backend" / "services" / "ollama_service.py",
        PROJECT_ROOT / "backend" / "api" / "system.py",
        PROJECT_ROOT / "03_features" / "team_dataset_builder.py",
    ]
    missing = []
    for path in expected_files:
        text = path.read_text(encoding="utf-8")
        if "get_logger" not in text and "configure_logging" not in text:
            missing.append(str(path.relative_to(PROJECT_ROOT)))
    assert missing == []
