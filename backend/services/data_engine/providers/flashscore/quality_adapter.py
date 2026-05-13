from __future__ import annotations
import pandas as pd

def adapt_flashscore_quality(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "data_quality_score" not in out.columns:
        out["data_quality_score"] = 0.78
    out["source_priority"] = 1
    out["primary_source"] = "flashscore"
    if "provider" not in out.columns:
        out["provider"] = "flashscore"
    if "is_demo_data" not in out.columns:
        out["is_demo_data"] = False
    # Demo rows are allowed only when explicitly configured and should carry lower confidence.
    demo_mask = out["is_demo_data"].astype(str).str.lower().isin({"true", "1", "yes"})
    if demo_mask.any():
        out.loc[demo_mask, "data_quality_score"] = out.loc[demo_mask, "data_quality_score"].fillna(0.62).clip(upper=0.65)
    return out
