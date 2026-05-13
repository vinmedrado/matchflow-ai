from __future__ import annotations

import os
import zipfile
from pathlib import Path


def test_patch_zip_has_no_cache_or_log_files_when_zip_path_is_provided():
    """Validate final delivery archive cleanliness when PATCH_ZIP_PATH is supplied."""
    zip_path = os.environ.get('PATCH_ZIP_PATH')
    if not zip_path:
        return

    path = Path(zip_path)
    assert path.exists(), f'PATCH_ZIP_PATH não encontrado: {path}'

    forbidden_fragments = ['__pycache__', '.pytest_cache']
    forbidden_suffixes = ['.pyc', '.pyo', '.tmp', '.log']

    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()

    violations = []
    for name in names:
        normalized = name.replace('\\', '/')
        if any(fragment in normalized for fragment in forbidden_fragments):
            violations.append(normalized)
        if any(normalized.endswith(suffix) for suffix in forbidden_suffixes):
            violations.append(normalized)
        if '/logs/' in normalized and normalized.endswith('.log'):
            violations.append(normalized)

    assert not violations, f'Arquivos proibidos encontrados no ZIP: {violations}'
