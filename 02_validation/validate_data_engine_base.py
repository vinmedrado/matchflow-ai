from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
from backend.core.storage import safe_read_dataframe, safe_write_dataframe

from backend.core.logging_config import get_logger

LOGGER = get_logger("matchflow.validate_data_engine_base")


class DataValidationError(RuntimeError):
    """Erro bloqueante quando a validação final encontra falhas críticas."""


class DataEngineBaseValidator:
    def __init__(self, config: Dict[str, Any], football_saas_root: Path) -> None:
        self.config = config
        self.root = football_saas_root.resolve()
        self.base_path = self._resolve_path(config.get("processed_output_path", "data/processed/base_data_engine.parquet"))
        self.report_path = self._resolve_path(config.get("quality_report_path", "data/reports/data_engine_quality_report.json"))
        self.required_fields = list(config.get("required_fields", []))
        self.quality_gates = config.get("quality_gates", {})

    def run(self) -> Dict[str, Any]:
        LOGGER.info("=" * 90)
        LOGGER.info("MATCHFLOW DATA ENGINE VALIDATION - START")
        LOGGER.info("Base alvo: %s", self.base_path)
        self.report_path.parent.mkdir(parents=True, exist_ok=True)

        report: Dict[str, Any] = {
            "status": "success",
            "base_path": str(self.base_path),
            "errors": [],
            "warnings": [],
            "summary": {},
            "missing_ratio_by_column": {},
            "duplicates": {},
            "distributions": {},
            "quality_gate": {"passed": None, "errors": []},
        }

        try:
            df = self._load_base()
            self._validate_basic_structure(df, report)
            self._validate_content(df, report)
            self._build_distributions(df, report)
            self._apply_quality_gate(report)
        except Exception as exc:  # noqa: BLE001
            report["status"] = "failed"
            report["errors"].append(str(exc))
            LOGGER.exception("Validação falhou: %s", exc)
            self._save_report(report)
            raise

        self._save_report(report)
        LOGGER.info("Relatório salvo: %s", self.report_path)
        LOGGER.info("MATCHFLOW DATA ENGINE VALIDATION - END")
        LOGGER.info("=" * 90)
        return report

    def _resolve_path(self, path_value: str) -> Path:
        path = Path(path_value)
        return path if path.is_absolute() else (self.root / path).resolve()

    def _load_base(self) -> pd.DataFrame:
        if not self.base_path.exists():
            raise FileNotFoundError(f"Base processada não encontrada: {self.base_path}")
        if self.base_path.stat().st_size == 0:
            raise DataValidationError(f"Base processada está vazia em disco: {self.base_path}")
        if self.base_path.suffix.lower() == ".parquet":
            df = safe_read_dataframe(self.base_path)
        elif self.base_path.suffix.lower() == ".csv":
            df = pd.read_csv(self.base_path, low_memory=False)
        else:
            raise ValueError(f"Formato da base não suportado: {self.base_path.suffix}")
        if df.empty:
            raise DataValidationError("Base processada carregou sem registros.")
        return df

    def _validate_basic_structure(self, df: pd.DataFrame, report: Dict[str, Any]) -> None:
        report["summary"] = {
            "rows": int(len(df)),
            "columns": int(len(df.columns)),
            "column_names": list(df.columns),
        }
        missing_columns = [col for col in self.required_fields if col not in df.columns]
        if missing_columns:
            raise DataValidationError(f"Colunas obrigatórias ausentes: {missing_columns}")
        LOGGER.info("Estrutura validada: linhas=%s colunas=%s", len(df), len(df.columns))

    def _validate_content(self, df: pd.DataFrame, report: Dict[str, Any]) -> None:
        work = df.copy()
        work["date"] = pd.to_datetime(work["date"], errors="coerce")
        invalid_dates = int(work["date"].isna().sum())
        missing_home = int(work["home_team"].isna().sum() + (work["home_team"].astype(str).str.strip() == "").sum())
        missing_away = int(work["away_team"].isna().sum() + (work["away_team"].astype(str).str.strip() == "").sum())
        same_team = int((work["home_team_key"].astype(str) == work["away_team_key"].astype(str)).sum())

        if invalid_dates:
            report["warnings"].append(f"Datas inválidas encontradas: {invalid_dates}")
        if missing_home:
            report["warnings"].append(f"Jogos sem mandante: {missing_home}")
        if missing_away:
            report["warnings"].append(f"Jogos sem visitante: {missing_away}")
        if same_team:
            report["warnings"].append(f"Jogos com home_team igual away_team: {same_team}")

        report["summary"].update(
            {
                "invalid_dates": invalid_dates,
                "missing_home_team": missing_home,
                "missing_away_team": missing_away,
                "same_home_away_team": same_team,
            }
        )
        report["missing_ratio_by_column"] = {
            col: round(float(work[col].isna().mean()), 6) for col in work.columns
        }
        report["duplicates"] = {
            "event_id_duplicate_ratio": round(self._duplicate_ratio(work, "event_id", ignore_blank=True), 6),
            "event_id_duplicate_rows": int(self._duplicate_count(work, "event_id", ignore_blank=True)),
            "match_key_duplicate_ratio": round(self._duplicate_ratio(work, "match_key", ignore_blank=False), 6),
            "match_key_duplicate_rows": int(self._duplicate_count(work, "match_key", ignore_blank=False)),
        }
        LOGGER.info("Conteúdo validado: invalid_dates=%s same_team=%s", invalid_dates, same_team)

    def _build_distributions(self, df: pd.DataFrame, report: Dict[str, Any]) -> None:
        work = df.copy()
        work["date"] = pd.to_datetime(work["date"], errors="coerce")
        work["year_month"] = work["date"].dt.strftime("%Y-%m")
        home_counts = work.groupby("home_team_key", dropna=False).size()
        away_counts = work.groupby("away_team_key", dropna=False).size()
        team_counts = home_counts.add(away_counts, fill_value=0).sort_values(ascending=False)
        report["distributions"] = {
            "by_league": self._value_counts(work, "league"),
            "by_season": self._value_counts(work, "season"),
            "by_year_month": self._value_counts(work, "year_month"),
            "games_by_team_top_100": {str(k): int(v) for k, v in team_counts.head(100).items()},
            "games_by_league": self._value_counts(work, "league"),
        }
        LOGGER.info("Distribuições geradas: ligas=%s temporadas=%s", work["league"].nunique(dropna=True), work["season"].nunique(dropna=True))

    def _apply_quality_gate(self, report: Dict[str, Any]) -> None:
        if not bool(self.quality_gates.get("enabled", True)):
            report["quality_gate"] = {"passed": True, "errors": []}
            return
        errors: List[str] = []
        max_missing = float(self.quality_gates.get("max_missing_ratio", 0.2))
        max_dup = float(self.quality_gates.get("max_duplicate_ratio", 0.05))
        for col in self.required_fields:
            ratio = float(report["missing_ratio_by_column"].get(col, 1.0))
            if ratio > max_missing:
                errors.append(f"{col}: missing {ratio:.2%} acima do limite {max_missing:.2%}")
        event_dup = float(report["duplicates"].get("event_id_duplicate_ratio", 0.0))
        match_dup = float(report["duplicates"].get("match_key_duplicate_ratio", 0.0))
        if event_dup > max_dup:
            errors.append(f"event_id duplicado {event_dup:.2%} acima do limite {max_dup:.2%}")
        if match_dup > max_dup:
            errors.append(f"match_key duplicado {match_dup:.2%} acima do limite {max_dup:.2%}")
        report["quality_gate"] = {"passed": not errors, "errors": errors}
        if errors:
            raise DataValidationError("Quality gate bloqueou a base: " + " | ".join(errors))
        LOGGER.info("Quality gate da validação aprovado.")

    def _duplicate_ratio(self, df: pd.DataFrame, column: str, ignore_blank: bool) -> float:
        if column not in df.columns or df.empty:
            return 0.0
        series = df[column]
        if ignore_blank:
            series = series.dropna()
            series = series[series.astype(str).str.strip() != ""]
        if len(series) == 0:
            return 0.0
        return float(series.duplicated(keep=False).mean())

    def _duplicate_count(self, df: pd.DataFrame, column: str, ignore_blank: bool) -> int:
        if column not in df.columns or df.empty:
            return 0
        series = df[column]
        if ignore_blank:
            series = series.dropna()
            series = series[series.astype(str).str.strip() != ""]
        return int(series.duplicated(keep=False).sum())

    def _value_counts(self, df: pd.DataFrame, column: str) -> Dict[str, int]:
        if column not in df.columns:
            return {}
        counts = df[column].fillna("__MISSING__").astype(str).value_counts(dropna=False)
        return {str(k): int(v) for k, v in counts.items()}

    def _save_report(self, report: Dict[str, Any]) -> None:
        with self.report_path.open("w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=2)
