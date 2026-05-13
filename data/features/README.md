# data/features

Pasta destinada aos datasets derivados do MatchFlow Analytics.

## Arquivo principal do PATCH 2

- `team_dataset.parquet`

Esse arquivo é gerado por:

```bash
python run_team_dataset_pipeline.py
```

Cada partida vira duas linhas: uma para o mandante e outra para o visitante. Todas as features temporais usam `shift(1)` antes de `rolling`, evitando data leakage.


## PATCH 3.0

O arquivo `team_dataset_advanced.parquet` é gerado pelo comando:

```bash
python run_advanced_features_pipeline.py
```

Ele usa como entrada `team_dataset.parquet` e adiciona features avançadas multi-mercado sem data leakage.
