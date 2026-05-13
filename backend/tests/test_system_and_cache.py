from __future__ import annotations

import json
from pathlib import Path

from backend.core.cache import file_cache
from backend.services.dataset_service import dataset_path, get_dataset_summary


def test_health_structure(client):
    response = client.get('/health')
    assert response.status_code == 200
    body = response.json()
    assert body['ok'] is True
    assert body['status'] == 'healthy'


def test_system_status_structure(client, auth_headers):
    response = client.get('/api/system/status', headers=auth_headers)
    assert response.status_code == 200
    data = response.json()['data']
    for key in ['api_status','dataset_available','dataset_rows','dataset_file_size_mb','dataset_last_modified','cache_status','api_uptime','timestamp']:
        assert key in data


def test_dataset_summary(client, auth_headers):
    response = client.get('/api/datasets/summary', headers=auth_headers)
    assert response.status_code == 200
    data = response.json()['data']
    assert 'available' in data
    assert 'total_records' in data
    assert 'columns' in data


def test_quality_report(client, auth_headers):
    response = client.get('/api/data-quality/report', headers=auth_headers)
    assert response.status_code == 200
    data = response.json()['data']
    assert 'available' in data


def test_cache_hit_after_first_load():
    file_cache.clear()
    first = get_dataset_summary()
    second = get_dataset_summary()
    assert first['cache']['cache_status'] in ['miss', 'error']
    if first['available']:
        assert second['cache']['cache_status'] == 'hit'


def test_dataset_missing_fallback(monkeypatch):
    from backend import services
    import backend.services.dataset_service as ds
    monkeypatch.setattr(ds, 'dataset_path', lambda: Path('missing_dataset_file.parquet'))
    summary = ds.get_dataset_summary()
    assert summary['available'] is False
    assert summary['total_records'] == 0


def test_metadata_valid():
    path = Path('data/processed/versions/v1/metadata.json')
    assert path.exists()
    metadata = json.loads(path.read_text(encoding='utf-8'))
    for key in ['version_id','created_at','total_rows','checksum','source']:
        assert key in metadata
    assert metadata['total_rows'] > 0
