"""
matchflow_imports.py — utilitário de import seguro para pastas numéricas.

O projeto mantém diretórios versionados como 11_automation e 10_monitoring.
Esses nomes são válidos como pastas, mas não funcionam bem como pacotes Python
quando um arquivo é carregado diretamente por importlib. Este helper cria um
alias de pacote válido em runtime e preserva os imports relativos internos.
"""
from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path
from types import ModuleType


def ensure_package_alias(alias: str, package_dir: Path) -> ModuleType:
    package_dir = Path(package_dir).resolve()
    if not package_dir.exists():
        raise FileNotFoundError(f"Diretório de pacote não encontrado: {package_dir}")

    parent = str(package_dir.parent)
    if parent not in sys.path:
        sys.path.insert(0, parent)

    current = sys.modules.get(alias)
    if current is not None:
        current.__path__ = [str(package_dir)]  # type: ignore[attr-defined]
        return current

    pkg = types.ModuleType(alias)
    pkg.__file__ = str(package_dir / "__init__.py")
    pkg.__path__ = [str(package_dir)]  # type: ignore[attr-defined]
    pkg.__package__ = alias
    sys.modules[alias] = pkg
    return pkg


def import_from_dir(alias: str, package_dir: Path, module_name: str) -> ModuleType:
    ensure_package_alias(alias, package_dir)
    return importlib.import_module(f"{alias}.{module_name}")
