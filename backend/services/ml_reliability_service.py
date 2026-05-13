from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
from backend.core.storage import safe_read_dataframe, safe_write_dataframe

MODE = "PAPER_TRADING_SIMULATION_ONLY"
MODELS = ["random_forest", "lightgbm", "xgboost"]


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_float(v: Any, default: float | None = 0.0) -> float | None:
    try:
        if v is None:
            return default
        if isinstance(v, str) and not v.strip():
            return default
        x = float(v)
        if math.isnan(x) or math.isinf(x):
            return default
        return x
    except Exception:
        return default


def _clip_prob(v: Any, default: float = 0.5) -> float:
    x = _safe_float(v, default)
    assert x is not None
    return max(0.001, min(0.999, float(x)))


def _read_frame(path: Path) -> pd.DataFrame:
    try:
        if path.exists() or path.with_suffix(".csv").exists() or path.with_suffix(".parquet").exists():
            if path.suffix.lower() == ".csv" and path.exists():
                return pd.read_csv(path)
            return safe_read_dataframe(path)
    except Exception:
        pass
    return pd.DataFrame()


def _write_json(path: Path, payload: dict[str, Any] | list[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def _write_frame(df: pd.DataFrame, parquet_path: Path, csv_path: Path | None = None) -> None:
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    safe_write_dataframe(df, parquet_path, index=False)
    if csv_path is not None:
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(csv_path, index=False)


def _brier(probs: Iterable[float], labels: Iterable[int]) -> float | None:
    p = list(probs); y = list(labels)
    if not p or len(p) != len(y):
        return None
    return round(sum((float(a) - int(b)) ** 2 for a, b in zip(p, y)) / len(p), 6)


def _log_loss(probs: Iterable[float], labels: Iterable[int]) -> float | None:
    p = list(probs); y = list(labels)
    if not p or len(p) != len(y):
        return None
    eps = 1e-15
    return round(-sum(int(b) * math.log(max(eps, min(1 - eps, float(a)))) + (1 - int(b)) * math.log(max(eps, min(1 - eps, 1 - float(a)))) for a, b in zip(p, y)) / len(p), 6)


def reliability_bins(probs: list[float], labels: list[int], bins: int = 10) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i in range(bins):
        low, high = i / bins, (i + 1) / bins
        idx = [j for j, p in enumerate(probs) if p >= low and (p < high or i == bins - 1)]
        if not idx:
            rows.append({"bin": i, "range_low": round(low, 4), "range_high": round(high, 4), "count": 0, "avg_probability": None, "observed_rate": None, "abs_error": None})
            continue
        avg = sum(probs[j] for j in idx) / len(idx)
        obs = sum(labels[j] for j in idx) / len(idx)
        rows.append({"bin": i, "range_low": round(low, 4), "range_high": round(high, 4), "count": len(idx), "avg_probability": round(avg, 6), "observed_rate": round(obs, 6), "abs_error": round(abs(avg - obs), 6)})
    return rows


def ece_mce(bins: list[dict[str, Any]], total: int) -> tuple[float | None, float | None]:
    if total <= 0:
        return None, None
    ece = 0.0; mce = 0.0
    for b in bins:
        count = int(b.get("count") or 0)
        err = b.get("abs_error")
        if count and err is not None:
            err_f = float(err)
            ece += (count / total) * err_f
            mce = max(mce, err_f)
    return round(ece, 6), round(mce, 6)


def _fit_binned_calibrator(probs: list[float], labels: list[int], bins: int = 10) -> dict[str, Any]:
    rbins = reliability_bins(probs, labels, bins=bins)
    mapping = []
    for b in rbins:
        if b["count"] >= 3 and b["observed_rate"] is not None:
            value = float(b["observed_rate"])
        elif b["avg_probability"] is not None:
            # conservative Platt-like fallback for sparse bins
            avg = float(b["avg_probability"])
            value = 0.5 + (avg - 0.5) * 0.85
        else:
            value = None
        mapping.append({"low": b["range_low"], "high": b["range_high"], "calibrated": None if value is None else round(max(0.02, min(0.98, value)), 6), "count": b["count"]})
    return {"method": "binned_isotonic_proxy", "bins": mapping}


def apply_calibrator(prob: float, calibrator: dict[str, Any] | None = None) -> float:
    p = _clip_prob(prob)
    if calibrator and calibrator.get("bins"):
        for b in calibrator["bins"]:
            low = float(b.get("low", 0)); high = float(b.get("high", 1))
            if p >= low and (p < high or high >= 1):
                val = b.get("calibrated")
                if val is not None:
                    return round(max(0.02, min(0.98, float(val))), 6)
    # conservative Platt shrinkage when labeled history is thin
    return round(max(0.02, min(0.98, 0.5 + (p - 0.5) * 0.88)), 6)


def sync_settled_predictions(root: Path | None = None) -> dict[str, Any]:
    root = Path(root) if root else project_root()
    from backend.services.settled_results_service import build_all_settled_results, _read_frame as _rf
    build_all_settled_results(root)
    frames=[]
    for st in ["real","paper","backtest","demo"]:
        df=_rf(root / f"data/results/{st}_settled_results.parquet")
        if not df.empty: frames.append(df)
    combined=pd.concat([f.dropna(axis=1, how="all") for f in frames], ignore_index=True, sort=False) if frames else pd.DataFrame()
    rows=[]
    for _, row in combined.iterrows() if not combined.empty else []:
        raw=_clip_prob(row.get("predicted_probability") or row.get("raw_probability"),0.5); actual=int(_safe_float(row.get("actual_result"),0) or 0); st=str(row.get("settlement_source_type") or "unknown")
        for model_name in MODELS:
            rows.append({"match_identity_key":row.get("match_identity_key"),"match_date":row.get("match_date"),"league":row.get("league"),"market":row.get("market"),"odds":_safe_float(row.get("odds"),None),"raw_probability":raw,"calibrated_probability":_clip_prob(row.get("calibrated_probability") or raw,raw),"confidence_score":_safe_float(row.get("confidence_score"),None),"decision_score":_safe_float(row.get("decision_score"),None),"predicted_label":int(raw>=0.5),"actual_result":actual,"prediction_correct":int((raw>=0.5)==bool(actual)),"realized_roi":_safe_float(row.get("realized_roi"),None),"model_name":model_name,"ensemble_probability":raw,"bankroll_profile":row.get("bankroll_profile") or "balanced","data_quality_score":_safe_float(row.get("data_quality_score"),None),"is_settled":bool(row.get("is_settled", True)),"settlement_source":row.get("settlement_source"),"settlement_source_type":st,"settlement_confidence":_safe_float(row.get("settlement_confidence"),None),"settled_at":row.get("settled_at") or _now()})
    cols=["match_identity_key","match_date","league","market","odds","raw_probability","calibrated_probability","confidence_score","decision_score","predicted_label","actual_result","prediction_correct","realized_roi","model_name","ensemble_probability","bankroll_profile","data_quality_score","is_settled","settlement_source","settlement_source_type","settlement_confidence","settled_at"]
    df=pd.DataFrame(rows); df=pd.DataFrame(columns=cols) if df.empty else df[cols]
    out_parquet=root/"data/ml/settled_predictions.parquet"; out_csv=root/"data/ml/settled_predictions.csv"; _write_frame(df,out_parquet,out_csv)
    breakdown=df.get("settlement_source_type",pd.Series(dtype=str)).value_counts().to_dict() if not df.empty else {}
    return {"ok":True,"mode":MODE,"settled_predictions":int(len(df)),"source_type_breakdown":breakdown,"real_rows":int(breakdown.get("real",0)),"output_paths":{"parquet":str(out_parquet.relative_to(root)),"csv":str(out_csv.relative_to(root))},"generated_at":_now()}


def build_calibration_artifacts(root: Path | None = None) -> dict[str, Any]:
    root = Path(root) if root else project_root(); sync=sync_settled_predictions(root); df_all=_read_frame(root/"data/ml/settled_predictions.parquet")
    out_dir=root/"data/ml/calibration"; out_dir.mkdir(parents=True, exist_ok=True); min_n=30
    if not df_all.empty:
        real_mask=(df_all.get("settlement_source_type",pd.Series(dtype=str)).astype(str)=="real") & (df_all.get("is_settled",pd.Series([True]*len(df_all))).astype(bool)); df=df_all[real_mask].copy()
    else: df=pd.DataFrame()
    source_breakdown=df_all.get("settlement_source_type",pd.Series(dtype=str)).value_counts().to_dict() if not df_all.empty else {}; real_n=int(len(df)); fallback_n=int(len(df_all)-real_n); is_real=real_n>=min_n
    mode="real" if is_real else "fallback"; source="real_settled_results" if is_real else "insufficient_real_settled_results"; reason=None if is_real else f"Only {real_n} real settled rows available; minimum is {min_n}. Paper/backtest/demo are excluded from real calibration."
    model_reports={}; all_bins=[]; registry_models=[]
    for model in MODELS:
        sub=df[df.get("model_name",pd.Series(dtype=str)).astype(str)==model].copy() if not df.empty else pd.DataFrame(); probs=[_clip_prob(x) for x in sub.get("raw_probability",pd.Series(dtype=float)).tolist()] if not sub.empty else []; labels=[int(_safe_float(x,0) or 0) for x in sub.get("actual_result",pd.Series(dtype=int)).tolist()] if not sub.empty else []
        sample_size=len(probs); method="binned_isotonic_proxy_real_settled" if is_real and sample_size>=min_n else "conservative_platt_fallback_no_real_sample"; bins=reliability_bins(probs,labels) if probs else reliability_bins([],[]); ece,mce=ece_mce(bins,sample_size); brier=_brier(probs,labels); ll=_log_loss(probs,labels); calibrator=_fit_binned_calibrator(probs,labels) if sample_size>=min_n else {"method":method,"bins":[],"source":source}; reliability_score=None if ece is None else round(max(0.0,1.0-ece*2.5),6); quality=0.2 if sample_size==0 else 0.35 if sample_size<min_n else (reliability_score if reliability_score is not None else 0.7); warning=None if sample_size>=min_n else "Insufficient real settled results; conservative fallback is active and not marked as real calibration."
        report={"model_name":model,"calibration_mode":mode,"calibration_source":source,"is_real_calibration":bool(is_real and sample_size>=min_n),"uses_backtest_data":False,"uses_paper_data":False,"uses_demo_data":False,"calibration_method":method,"calibration_sample_size":sample_size,"real_sample_size":sample_size,"fallback_sample_size":fallback_n,"minimum_required_sample_size":min_n,"brier_score":brier,"log_loss":ll,"ece":ece,"mce":mce,"reliability_score":reliability_score,"calibration_quality_score":round(float(quality),6),"calibration_warning":warning,"reliability_bins":bins,"calibrator":calibrator}
        model_reports[model]=report; registry_models.append({"model_name":model,**{k:v for k,v in report.items() if k!="reliability_bins"}}); all_bins += [{"model_name":model,**b} for b in bins]
    vals=[v.get("ece") for v in model_reports.values() if v.get("ece") is not None]; global_ece=round(sum(float(x) for x in vals)/len(vals),6) if vals else None; markets=sorted(df.get("market",pd.Series(dtype=str)).dropna().astype(str).unique().tolist()) if not df.empty else []
    payload={"ok":True,"mode":MODE,"generated_at":_now(),"settled_predictions_sync":sync,"calibration_mode":mode,"calibration_source":source,"is_real_calibration":bool(is_real),"real_calibration_available":bool(is_real),"real_sample_size":real_n,"fallback_sample_size":fallback_n,"minimum_required_sample_size":min_n,"required_sample_size":min_n,"uses_backtest_data":False,"uses_paper_data":False,"uses_demo_data":False,"fallback_reason":reason,"calibration_data_breakdown":{"real_used":real_n,"fallback_available_but_excluded":fallback_n},"source_type_breakdown":source_breakdown,"markets_calibrated":markets,"models_calibrated":[m for m,r in model_reports.items() if r["is_real_calibration"]],"excluded_records_count":fallback_n,"excluded_reasons":{"non_real_settlement_source_type":fallback_n},"reliability_by_market":{},"reliability_by_model":{m:{"ece":r.get("ece"),"mce":r.get("mce"),"brier_score":r.get("brier_score"),"sample_size":r.get("real_sample_size")} for m,r in model_reports.items()},"models":model_reports,"global_metrics":{"total_settled_rows":int(len(df_all)),"real_settled_rows":real_n,"global_ece":global_ece,"calibration_status":"real_settled_feedback" if is_real else "fallback_insufficient_real_settled_feedback"},"warnings":[] if is_real else [reason]}
    _write_json(out_dir/"calibration_report.json",payload); _write_json(out_dir/"calibrated_model_registry.json",{"ok":True,"mode":MODE,"updated_at":payload["generated_at"],"calibration_mode":mode,"is_real_calibration":bool(is_real),"models":registry_models}); pd.DataFrame(all_bins).to_csv(out_dir/"reliability_bins.csv",index=False)
    hist_path=out_dir/"calibration_metrics_history.parquet"; hist=pd.DataFrame([{"timestamp":payload["generated_at"],"total_settled_rows":len(df_all),"real_settled_rows":real_n,"global_ece":global_ece,"model_count":len(MODELS),"is_real_calibration":bool(is_real)}])
    if hist_path.exists():
        old=_read_frame(hist_path)
        if not old.empty: hist=pd.concat([old.dropna(axis=1,how="all"),hist.dropna(axis=1,how="all")],ignore_index=True)
    safe_write_dataframe(hist, hist_path, index=False); return payload


def get_calibrator_for_model(root: Path | None, model_name: str) -> dict[str, Any] | None:
    root = Path(root) if root else project_root()
    path = root / "data/ml/calibration/calibrated_model_registry.json"
    if not path.exists():
        build_calibration_artifacts(root)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        for rec in payload.get("models", []):
            if rec.get("model_name") == model_name:
                return rec.get("calibrator") or None
    except Exception:
        return None
    return None


def apply_model_calibration(root: Path | None, model_name: str, probability: float) -> float:
    return apply_calibrator(probability, get_calibrator_for_model(root, model_name))
