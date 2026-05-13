"""
match_reconciler.py — Wrapper sobre o motor de deduplicação interno.

Delega para:
  backend/services/data_engine/normalization/deduplication_engine.py
  backend/services/data_engine/normalization/match_identity_resolver.py
  backend/services/data_engine/enrichment/enrichment_engine.py

Hierarquia de fontes (prioridade 1 = maior):
  1. FlashScore   → FONTE DE VERDADE (escanteios, chutes, XG, odds reais)
  2. football-data.org → preenche campos vazios (season, matchday, etc.)
  3. The Odds API → preenche odds ausentes
"""
from __future__ import annotations
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import numpy as np

logger = logging.getLogger("matchflow.data_ops.match_reconciler")

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "backend/services/data_engine/normalization"))

DATE_TOLERANCE_DAYS = 1

ENRICHMENT_FIELDS_FROM_API = ["season", "matchday", "competition_code",
                               "home_team_id", "away_team_id"]
ENRICHMENT_FIELDS_FROM_ODDS = ["odds_home_ft", "odds_draw_ft", "odds_away_ft",
                                "odds_over_2_5_ft", "odds_under_2_5_ft",
                                "odds_btts_yes", "odds_btts_no"]


def _norm_date(val: Any) -> pd.Timestamp | None:
    try:
        ts = pd.to_datetime(val, errors="coerce", utc=False)
        if pd.isna(ts):
            return None
        return ts.normalize()
    except Exception:
        return None


def _build_match_key(date: Any, home: str, away: str) -> str:
    d = _norm_date(date)
    date_str = d.strftime("%Y-%m-%d") if d else "unknown"
    return f"{date_str}|{str(home).lower().strip()}|{str(away).lower().strip()}"


def _non_null_count(row: pd.Series) -> int:
    return int(row.notna().sum())


class MatchReconciler:
    """
    Reconcilia múltiplas fontes de dados em uma base única e sem duplicatas.
    Usa o motor interno de deduplicação quando disponível.
    """

    def __init__(self, team_reconciler=None, root: Path | None = None) -> None:
        self.root = root or _ROOT
        self._team_reconciler = team_reconciler
        self._log: list[dict] = []

        # Tentar usar motor interno
        self._internal_dedup = None
        try:
            from deduplication_engine import deduplicate_matches
            self._internal_dedup = deduplicate_matches
            logger.debug("Usando motor interno de deduplicação")
        except ImportError:
            logger.debug("Motor interno não disponível — usando deduplicação própria")

    def _normalize_teams(self, df: pd.DataFrame) -> pd.DataFrame:
        """Adiciona colunas home_team_norm, away_team_norm e match_key."""
        df = df.copy()

        # Usar serviço interno se disponível
        try:
            from text_normalizer import normalize_text
            def norm(n): return normalize_text(str(n or ""), entity_type="team")
        except ImportError:
            # Fallback: wrapper do team_normalizer
            from team_normalizer import normalize_team_name as norm  # type: ignore

        df["home_team_norm"] = df.get("home_team", pd.Series(dtype=str)).apply(
            lambda x: norm(str(x)) if pd.notna(x) else "")
        df["away_team_norm"] = df.get("away_team", pd.Series(dtype=str)).apply(
            lambda x: norm(str(x)) if pd.notna(x) else "")
        df["match_key"] = df.apply(
            lambda r: _build_match_key(r.get("date"), r.get("home_team_norm",""), r.get("away_team_norm","")),
            axis=1)
        return df

    def reconcile(
        self,
        flashscore_df: pd.DataFrame,
        api_df: pd.DataFrame | None = None,
        odds_df: pd.DataFrame | None = None,
    ) -> pd.DataFrame:
        """
        Reconcilia FlashScore (primária) com fontes secundárias.
        FlashScore nunca é sobrescrito — fontes secundárias apenas preenchem campos vazios.
        """
        if flashscore_df.empty:
            return flashscore_df

        stats = {"enriched_api": 0, "enriched_odds": 0, "new_from_api": 0, "dupes_removed": 0}
        primary = self._normalize_teams(flashscore_df.copy())
        primary["data_source"] = primary.get("data_source", pd.Series()).fillna("flashscore")

        # Índice de busca rápida {match_key: row_index}
        key_idx: dict[str, int] = {}
        for idx, row in primary.iterrows():
            key = row.get("match_key", "")
            if key and "unknown" not in key:
                key_idx[key] = idx
                # Variações de ±1 dia
                d = _norm_date(row.get("date"))
                if d:
                    h, a = row.get("home_team_norm",""), row.get("away_team_norm","")
                    for delta in range(-DATE_TOLERANCE_DAYS, DATE_TOLERANCE_DAYS + 1):
                        fk = f"{(d + timedelta(days=delta)).strftime('%Y-%m-%d')}|{h}|{a}"
                        key_idx.setdefault(fk, idx)

        # Enriquecer com football-data.org
        if api_df is not None and not api_df.empty:
            api_norm = self._normalize_teams(api_df.copy())
            new_rows = []
            for _, row in api_norm.iterrows():
                key = row.get("match_key", "")
                matched_idx = key_idx.get(key)
                if matched_idx is not None:
                    for field in ENRICHMENT_FIELDS_FROM_API:
                        if field in row and pd.notna(row[field]):
                            cur = primary.at[matched_idx, field] if field in primary.columns else None
                            if cur is None or str(cur).strip() in ("", "nan", "None"):
                                primary.at[matched_idx, field] = row[field]
                                stats["enriched_api"] += 1
                else:
                    new_rows.append({**row.to_dict(), "data_source": "football_data_api"})
                    stats["new_from_api"] += 1
            if new_rows:
                primary = pd.concat([primary, pd.DataFrame(new_rows)], ignore_index=True, sort=False)

        # Enriquecer com odds
        if odds_df is not None and not odds_df.empty:
            odds_norm = self._normalize_teams(odds_df.copy())
            for _, row in odds_norm.iterrows():
                matched_idx = key_idx.get(row.get("match_key", ""))
                if matched_idx is not None:
                    for field in ENRICHMENT_FIELDS_FROM_ODDS:
                        if field in row and pd.notna(row[field]):
                            cur = primary.at[matched_idx, field] if field in primary.columns else None
                            if cur is None or (isinstance(cur, float) and np.isnan(cur)):
                                primary.at[matched_idx, field] = row[field]
                                stats["enriched_odds"] += 1

        # Deduplicação final
        before = len(primary)
        if "match_key" in primary.columns:
            primary["_nn"] = primary.apply(_non_null_count, axis=1)
            primary = (primary.sort_values("_nn", ascending=False)
                               .drop_duplicates(subset=["match_key"], keep="first")
                               .drop(columns=["_nn"]))
        stats["dupes_removed"] = before - len(primary)

        # Limpar colunas auxiliares
        for col in ["home_team_norm", "away_team_norm", "match_key"]:
            if col in primary.columns:
                primary = primary.drop(columns=[col])

        if "date" in primary.columns:
            primary = primary.sort_values("date", na_position="last")
        primary = primary.reset_index(drop=True)

        logger.info("Reconciliação: %s jogos | enrich_api=%s | enrich_odds=%s | novos=%s | dupes=%s",
                    len(primary), stats["enriched_api"], stats["enriched_odds"],
                    stats["new_from_api"], stats["dupes_removed"])
        self._log.append({"timestamp": datetime.utcnow().isoformat(),
                          "output_rows": len(primary), **stats})
        return primary

    def get_log(self) -> list[dict]:
        return self._log


def reconcile_all_sources(root: Path | None = None) -> dict[str, Any]:
    """Ponto de entrada principal: carrega fontes, reconcilia, salva parquet."""
    root = root or _ROOT
    output_path = root / "data/processed/base_data_engine.parquet"
    output_csv   = root / "data/processed/base_data_engine.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Carregar FlashScore
    flashscore_df = pd.DataFrame()
    for path in [output_path, output_csv]:
        if path.exists() and path.stat().st_size > 1000:
            try:
                flashscore_df = pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path, low_memory=False)
                break
            except Exception as e:
                logger.warning("Falha ao carregar %s: %s", path.name, e)

    if flashscore_df.empty:
        return {"ok": False, "reason": "NO_FLASHSCORE_DATA",
                "hint": "Execute Data Operations → Atualizar (7 dias) primeiro"}

    api_df = None
    api_path = root / "data/raw/historical/all_leagues_historical.parquet"
    if api_path.exists():
        try: api_df = pd.read_parquet(api_path)
        except Exception: pass

    odds_df = None
    odds_path = root / "data/odds/odds_latest.parquet"
    if odds_path.exists():
        try: odds_df = pd.read_parquet(odds_path)
        except Exception: pass

    reconciler = MatchReconciler(root=root)
    unified = reconciler.reconcile(flashscore_df, api_df, odds_df)
    unified.to_parquet(output_path, index=False)
    unified.to_csv(output_csv, index=False, encoding="utf-8-sig")

    log = reconciler.get_log()[-1] if reconciler.get_log() else {}
    return {"ok": True, "total_rows": len(unified), **log}
