from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd
from backend.core.storage import safe_read_dataframe, safe_write_dataframe
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

LGBMClassifier = None

try:
    from backend.core.logging_config import get_logger
except Exception:  # pragma: no cover
    import logging
    logging.basicConfig(level=logging.INFO)
    def get_logger(name: str):
        return logging.getLogger(name)

try:
    from .evaluator import ModelEvaluator
    from .feature_selector import FeatureSelector
    from .model_registry import ModelRegistry
except Exception:  # pragma: no cover
    try:
        from evaluator import ModelEvaluator
        from feature_selector import FeatureSelector
        from model_registry import ModelRegistry
    except Exception:
        import importlib.util as _importlib_util
        _base = Path(__file__).resolve().parent
        def _load_local(_name: str, _file: str):
            _spec = _importlib_util.spec_from_file_location(_name, _base / _file)
            _mod = _importlib_util.module_from_spec(_spec)
            assert _spec and _spec.loader
            _spec.loader.exec_module(_mod)
            return _mod
        ModelEvaluator = _load_local("mf_ml_evaluator", "evaluator.py").ModelEvaluator
        FeatureSelector = _load_local("mf_ml_feature_selector", "feature_selector.py").FeatureSelector
        ModelRegistry = _load_local("mf_ml_model_registry", "model_registry.py").ModelRegistry

logger = get_logger("matchflow.ml.model_trainer")

MARKET_TARGETS = {"goals": "target_goals", "corners": "target_corners", "shots": "target_shots", "btts": "target_btts"}
ODDS_ALIASES = {
    "goals": ["odds_over_2_5", "Odd_Over25_FT", "odd_over25_ft", "odds_goals", "odds_over25"],
    "corners": ["odds_corners", "Odd_Corners_Over95", "odd_corners_over95", "odds_corners_over_9_5"],
    "shots": ["odds_shots", "odd_shots", "odds_shots_over"],
    "btts": ["odds_btts", "Odd_BTTS_Yes", "odd_btts_yes"],
}

class ModelTrainer:
    def __init__(self, project_root: Path, config: Dict[str, Any]) -> None:
        self.project_root = project_root
        self.config = config
        self.models_dir = self.project_root / config.get("models_dir", "data/ml/models")
        self.predictions_dir = self.project_root / config.get("predictions_dir", "data/ml/predictions")
        self.evaluation_dir = self.project_root / config.get("evaluation_dir", "data/ml/evaluation")
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.predictions_dir.mkdir(parents=True, exist_ok=True)
        self.evaluation_dir.mkdir(parents=True, exist_ok=True)
        self.selector = FeatureSelector(project_root, config)
        self.evaluator = ModelEvaluator(project_root, config)
        self.registry = ModelRegistry(project_root, config)

    def train_all(self, df: pd.DataFrame) -> Dict[str, Any]:
        summary: Dict[str, Any] = {"markets": {}, "research_only": True}
        comparison_records: List[Dict[str, Any]] = []
        for market in self.config.get("target_markets", list(MARKET_TARGETS)):
            target_col = MARKET_TARGETS.get(market)
            if not target_col or target_col not in df.columns:
                logger.warning("Target ML indisponível para market=%s", market)
                continue
            try:
                result = self.train_market(df, market, target_col)
                summary["markets"][market] = result
                comparison_records.extend(result.get("comparison_records", []))
            except Exception as exc:
                logger.exception("Falha no treino ML de market=%s: %s", market, exc)
                summary["markets"][market] = {"trained": False, "error": str(exc)}
        self._save_ml_vs_rules_comparison(comparison_records)
        return summary

    def train_market(self, df: pd.DataFrame, market: str, target_col: str) -> Dict[str, Any]:
        data = df[df[target_col].notna()].copy()
        if data.empty:
            return {"trained": False, "reason": "target_empty"}
        data["date"] = pd.to_datetime(data["date"], errors="coerce")
        data = data[data["date"].notna()].sort_values("date").reset_index(drop=True)
        features = self.selector.select(data, target_col)
        if not features:
            return {"trained": False, "reason": "no_valid_features"}

        folds = self._walk_forward_splits(data)
        if not folds:
            return {"trained": False, "reason": "not_enough_walk_forward_data"}

        model_results = []
        for model_name in self.config.get("models", ["lightgbm", "random_forest"]):
            fold_records, all_predictions = [], []
            for fold_idx, (train_df, test_df) in enumerate(folds, start=1):
                model = self._create_model(model_name)
                X_train, y_train = train_df[features], train_df[target_col].astype(int)
                X_test, y_test = test_df[features], test_df[target_col].astype(int)
                model.fit(X_train, y_train)
                probabilities = self._predict_proba(model, X_test)
                metrics = self.evaluator.evaluate(market, model_name, y_test, probabilities, suffix=f"fold_{fold_idx}")
                fold_records.append({
                    "fold": fold_idx,
                    "train_rows": int(len(train_df)),
                    "test_rows": int(len(test_df)),
                    "train_start": str(train_df["date"].min().date()),
                    "train_end": str(train_df["date"].max().date()),
                    "test_start": str(test_df["date"].min().date()),
                    "test_end": str(test_df["date"].max().date()),
                    "metrics": metrics,
                })
                all_predictions.append(self._build_prediction_frame(test_df, market, model_name, target_col, probabilities, fold_idx))

            final_train = data[data["date"] <= folds[-1][0]["date"].max()].copy()
            if final_train.empty:
                final_train = folds[-1][0]
            final_model = self._create_model(model_name)
            final_model.fit(final_train[features], final_train[target_col].astype(int))
            model_path = self.models_dir / f"{market}_{model_name}_model.pkl"
            joblib.dump({
                "model": final_model,
                "features": features,
                "target": target_col,
                "market": market,
                "validation": "walk_forward",
                "target_policy": "X(t)->y(t+1)",
                "research_only": True,
            }, model_path)

            pred_df = pd.concat(all_predictions, ignore_index=True) if all_predictions else pd.DataFrame()
            pred_path = self.predictions_dir / f"{market}_{model_name}_predictions.parquet"
            if not pred_df.empty:
                safe_write_dataframe(pred_df, pred_path, index=False)

            aggregate_metrics = self._aggregate_fold_metrics(market, model_name, fold_records)
            final_metrics_path = self.evaluation_dir / f"{market}_{model_name}_metrics.json"
            final_metrics_path.write_text(json.dumps(aggregate_metrics, indent=2, ensure_ascii=False), encoding="utf-8")
            importance_path = self._save_feature_importance(final_model, features, market, model_name)

            record = {
                "market": market,
                "model_name": model_name,
                "target": target_col,
                "features_count": len(features),
                "validation": "walk_forward",
                "folds": fold_records,
                "model_path": str(model_path.relative_to(self.project_root)),
                "predictions_path": str(pred_path.relative_to(self.project_root)),
                "feature_importance_path": str(importance_path.relative_to(self.project_root)),
                "metrics": aggregate_metrics,
            }
            self.registry.register(record)
            model_results.append(record)

        best = self._best_model(model_results)
        if best:
            (self.models_dir / f"{market}_model.pkl").write_bytes((self.project_root / best["model_path"]).read_bytes())
            best_pred = self.project_root / best["predictions_path"]
            if best_pred.exists():
                (self.predictions_dir / f"{market}_predictions.parquet").write_bytes(best_pred.read_bytes())
            (self.evaluation_dir / f"{market}_metrics.json").write_text(json.dumps(best["metrics"], indent=2, ensure_ascii=False), encoding="utf-8")

        logger.info("Treino walk-forward ML concluído: market=%s modelos=%s features=%s", market, len(model_results), len(features))
        comparison_records = self._build_comparison_records(market, best, data)
        return {
            "trained": bool(model_results),
            "market": market,
            "target": target_col,
            "features_count": len(features),
            "validation": "walk_forward",
            "target_policy": "X(t)->y(t+1)",
            "models": model_results,
            "best_model": best["model_name"] if best else None,
            "comparison_records": comparison_records,
        }

    def _time_split(self, data: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Legacy holdout split kept for Patch 5.0 compatibility.

        Uses the same chronological no-leakage principle as the current
        walk-forward splitter and returns the first available fold.
        """
        folds = self._walk_forward_splits(data)
        if folds:
            return folds[0]
        data = data.sort_values("date").reset_index(drop=True).copy() if "date" in data.columns else data.reset_index(drop=True).copy()
        if len(data) <= 1:
            return data.copy(), data.iloc[0:0].copy()
        split_index = max(1, int(len(data) * 0.8))
        split_index = min(split_index, len(data) - 1)
        return data.iloc[:split_index].copy(), data.iloc[split_index:].copy()

    def _walk_forward_splits(self, data: pd.DataFrame) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
        min_train = int(self.config.get("min_train_rows", 20))
        min_val = int(self.config.get("min_validation_rows", 5))
        data = data.sort_values("date").reset_index(drop=True)
        years = sorted(data["date"].dt.year.dropna().unique().tolist())
        folds: List[Tuple[pd.DataFrame, pd.DataFrame]] = []
        for year in years[1:]:
            train_df = data[data["date"].dt.year < year].copy()
            test_df = data[data["date"].dt.year == year].copy()
            if len(train_df) >= min_train and len(test_df) >= min_val:
                folds.append((train_df, test_df))
        if not folds:
            test_size = float(self.config.get("test_size", 0.2))
            split_index = max(min_train, int(len(data) * (1 - test_size)))
            split_index = min(split_index, len(data) - min_val)
            if split_index > 0 and split_index < len(data):
                train_df = data.iloc[:split_index].copy()
                test_df = data.iloc[split_index:].copy()
                if len(train_df) >= min_train and len(test_df) >= min_val and train_df["date"].max() <= test_df["date"].min():
                    folds.append((train_df, test_df))
        logger.info("Walk-forward splits criados: folds=%s", len(folds))
        return folds

    def _build_prediction_frame(self, test_df: pd.DataFrame, market: str, model_name: str, target_col: str, probabilities: np.ndarray, fold_idx: int) -> pd.DataFrame:
        base_cols = [col for col in ["date", "league", "season", "team_key", "team_name", "opponent_key", "opponent_name", "side", "target_match_date", "target_league", "target_opponent_key", "target_side"] if col in test_df.columns]
        pred_df = test_df[base_cols].copy()
        pred_df["market"] = market
        pred_df["model_name"] = model_name
        pred_df["fold"] = fold_idx
        pred_df["target_col"] = target_col
        pred_df["target"] = test_df[target_col].astype(int).values
        pred_df["probability"] = probabilities
        pred_df["odds"] = self._extract_odds(test_df, market).values
        pred_df["strategy_associated"] = self._strategy_label_for_market(market)
        pred_df["research_only"] = True
        return pred_df

    def _extract_odds(self, df: pd.DataFrame, market: str) -> pd.Series:
        for col in ODDS_ALIASES.get(market, []):
            if col in df.columns:
                return pd.to_numeric(df[col], errors="coerce")
        return pd.Series(np.nan, index=df.index)

    def _strategy_label_for_market(self, market: str) -> str:
        path = self.project_root / self.config.get("baseline_refinement_path", "data/backtest/refinement/refined_strategy_candidates.csv")
        if not path.exists():
            return "research_probability_only"
        try:
            baseline = pd.read_csv(path)
            if "market" in baseline.columns and "strategy" in baseline.columns:
                rows = baseline[baseline["market"].astype(str).str.lower() == market.lower()]
                if not rows.empty:
                    return str(rows.iloc[0]["strategy"])
        except Exception as exc:
            logger.warning("Não foi possível ler baseline refinement para strategy label: %s", exc)
        return "research_probability_only"

    def _aggregate_fold_metrics(self, market: str, model_name: str, fold_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        metric_keys = ["accuracy", "precision", "recall", "roc_auc", "log_loss", "brier_score", "calibration_error"]
        out: Dict[str, Any] = {"market": market, "model_name": model_name, "validation": "walk_forward", "folds_count": len(fold_records)}
        out["folds"] = fold_records
        for key in metric_keys:
            values = [fold["metrics"].get(key) for fold in fold_records if fold.get("metrics", {}).get(key) is not None]
            out[key] = float(np.mean(values)) if values else None
        return out

    def _save_feature_importance(self, model, features: List[str], market: str, model_name: str) -> Path:
        estimator = model.named_steps.get("model") if hasattr(model, "named_steps") else model
        if hasattr(estimator, "feature_importances_"):
            importance = np.asarray(estimator.feature_importances_, dtype=float)
        else:
            importance = np.zeros(len(features), dtype=float)
        frame = pd.DataFrame({"feature": features, "importance": importance})
        frame = frame.sort_values("importance", ascending=False).reset_index(drop=True)
        frame["rank"] = np.arange(1, len(frame) + 1)
        path = self.evaluation_dir / f"{market}_{model_name}_feature_importance.csv"
        frame.to_csv(path, index=False)
        return path

    def _build_comparison_records(self, market: str, best: Dict[str, Any] | None, data: pd.DataFrame) -> List[Dict[str, Any]]:
        if not best:
            return []
        metrics = best.get("metrics", {})
        baseline = self._load_rules_baseline(market)
        return [{
            "market": market,
            "ml_model": best.get("model_name"),
            "ml_roc_auc": metrics.get("roc_auc"),
            "ml_brier_score": metrics.get("brier_score"),
            "ml_calibration_error": metrics.get("calibration_error"),
            "ml_rows": int(len(data)),
            "rule_strategy": baseline.get("strategy"),
            "rule_recommendation": baseline.get("final_recommendation") or baseline.get("recommendation"),
            "rule_roi": baseline.get("ROI") or baseline.get("roi"),
            "rule_profit_factor": baseline.get("profit_factor"),
            "rule_sample_size": baseline.get("total_trades") or baseline.get("sample_size"),
            "comparison_note": "Research comparison only. ML probabilities are not operational signals.",
        }]

    def _load_rules_baseline(self, market: str) -> Dict[str, Any]:
        for cfg_key in ["baseline_refinement_path", "baseline_summary_path"]:
            path = self.project_root / self.config.get(cfg_key, "")
            if not path.exists():
                continue
            try:
                df = pd.read_csv(path)
                if "market" in df.columns:
                    rows = df[df["market"].astype(str).str.lower() == market.lower()]
                    if not rows.empty:
                        return rows.iloc[0].to_dict()
            except Exception as exc:
                logger.warning("Falha ao carregar baseline de regras %s: %s", path, exc)
        return {}

    def _save_ml_vs_rules_comparison(self, records: List[Dict[str, Any]]) -> None:
        path = self.evaluation_dir / "ml_vs_rules_comparison.csv"
        if records:
            pd.DataFrame(records).to_csv(path, index=False)
        else:
            pd.DataFrame(columns=["market", "ml_model", "ml_roc_auc", "rule_strategy", "rule_roi", "comparison_note"]).to_csv(path, index=False)
        logger.info("Comparação ML vs regras salva: %s", path)

    def _create_model(self, model_name: str):
        random_state = int(self.config.get("random_state", 42))
        if model_name == "lightgbm" and LGBMClassifier is not None:
            estimator = LGBMClassifier(n_estimators=30, learning_rate=0.05, max_depth=4, random_state=random_state, verbose=-1)
            return Pipeline([("imputer", SimpleImputer(strategy="median")), ("model", estimator)])
        if model_name == "lightgbm":
            logger.warning("LightGBM não instalado. Usando HistGradientBoostingClassifier como fallback local.")
            return Pipeline([("imputer", SimpleImputer(strategy="median")), ("model", HistGradientBoostingClassifier(max_iter=30, learning_rate=0.05, max_leaf_nodes=15, random_state=random_state))])
        return Pipeline([("imputer", SimpleImputer(strategy="median")), ("model", RandomForestClassifier(n_estimators=40, min_samples_leaf=2, random_state=random_state, n_jobs=-1))])

    def _predict_proba(self, model, X: pd.DataFrame) -> np.ndarray:
        if hasattr(model, "predict_proba"):
            proba = model.predict_proba(X)
            if proba.shape[1] == 1:
                classes = getattr(model, "classes_", [0])
                only_class = int(classes[0]) if len(classes) else 0
                return np.ones(len(X), dtype=float) if only_class == 1 else np.zeros(len(X), dtype=float)
            return np.clip(proba[:, 1], 0.0, 1.0)
        return np.clip(np.asarray(model.predict(X), dtype=float), 0.0, 1.0)

    def _best_model(self, records: List[Dict[str, Any]]) -> Dict[str, Any] | None:
        if not records:
            return None
        def score(record: Dict[str, Any]) -> float:
            metrics = record.get("metrics", {})
            auc = metrics.get("roc_auc")
            brier = metrics.get("brier_score")
            if auc is not None:
                return float(auc)
            if brier is not None:
                return float(1 - brier)
            return float(metrics.get("accuracy", 0.0) or 0.0)
        return sorted(records, key=score, reverse=True)[0]
