# Versionamento de Dataset

A estrutura inicial de versionamento fica em:

```text
data/processed/versions/v1/
├── base_data_engine.parquet
└── metadata.json
```

O `metadata.json` contém:

- `version_id`
- `created_at`
- `total_rows`
- `checksum`
- `source`
- `source_files`
- `columns`

O Parquet do patch é um sample válido para garantir que backend, frontend e testes funcionem mesmo antes de conectar a base real completa.
