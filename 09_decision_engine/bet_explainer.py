"""
signal_explainer.py — Explicabilidade de sinais usando SHAP.
Para cada candidato HIGH_CONFIDENCE, mostra exatamente quais
features impulsionaram a decisão do modelo (top 3 positivas e negativas).
"""
from __future__ import annotations
import json, logging
from pathlib import Path
from typing import Any
import pandas as pd
import numpy as np

logger = logging.getLogger("matchflow.decision_engine.signal_explainer")

FEATURE_LABELS_PT = {
    "avg_goals_last_5": "Média de gols últimos 5 jogos",
    "goals_for_ft_avg_last_5": "Média de gols marcados últimos 5 jogos",
    "goals_against_ft_avg_last_5": "Média de gols sofridos últimos 5 jogos",
    "goal_trend": "Tendência de gols (subindo/descendo)",
    "expected_goals_proxy": "xG estimado",
    "h2h_over25_rate": "Taxa de Over 2.5 no H2H",
    "btts_rate_last_10": "Taxa BTTS últimos 10 jogos",
    "corners_avg_last_5": "Média de escanteios últimos 5 jogos",
    "corners_trend": "Tendência de escanteios",
    "shots_avg_last_5": "Média de chutes a gol últimos 5",
    "shots_on_target_rate_avg_last_5": "Taxa de chutes no alvo últimos 5",
    "pressure_avg_last_5": "Pressão ofensiva média últimos 5",
    "home_win_rate_last_10": "Taxa de vitórias em casa (últimos 10)",
    "away_win_rate_last_10": "Taxa de vitórias fora (últimos 10)",
    "league_avg_goals": "Média de gols da liga",
    "consistency_score": "Consistência histórica da estratégia",
    "odds": "Odds de mercado",
    "ml_probability": "Probabilidade estimada pelo ML",
    "ensemble_probability": "Probabilidade do ensemble de modelos",
    "true_ev": "Expected Value verdadeiro",
    "edge_over_market": "Edge sobre o mercado justo",
    "movement_pct": "Movimento das odds desde abertura",
    "steam_detected": "Steam move detectado (dinheiro profissional)",
}

def explain_with_shap(model: Any, features: pd.DataFrame, top_n: int = 3) -> dict[str, Any]:
    """
    Usa SHAP TreeExplainer para explicar decisão do modelo.
    Retorna top features positivas e negativas.
    """
    try:
        import shap
    except ImportError:
        return {"error": "shap não instalado. Execute: pip install shap", "available": False}

    try:
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(features)

        # Para classificação binária, pegar valores da classe positiva
        if isinstance(shap_values, list):
            sv = shap_values[1] if len(shap_values) > 1 else shap_values[0]
        else:
            sv = shap_values

        if len(sv.shape) > 1:
            sv = sv[0]

        feature_names = list(features.columns)
        feature_values = features.iloc[0].to_dict() if len(features) > 0 else {}

        # Ordenar por impacto absoluto
        shap_dict = dict(zip(feature_names, sv))
        sorted_features = sorted(shap_dict.items(), key=lambda x: abs(x[1]), reverse=True)

        positive = [(k, v) for k, v in sorted_features if v > 0][:top_n]
        negative = [(k, v) for k, v in sorted_features if v < 0][:top_n]

        return {
            "available": True,
            "top_positive": [
                {"feature": k, "label": FEATURE_LABELS_PT.get(k, k),
                 "shap_value": round(float(v), 4),
                 "feature_value": round(float(feature_values.get(k, 0)), 3) if isinstance(feature_values.get(k), (int, float)) else feature_values.get(k)}
                for k, v in positive
            ],
            "top_negative": [
                {"feature": k, "label": FEATURE_LABELS_PT.get(k, k),
                 "shap_value": round(float(v), 4),
                 "feature_value": round(float(feature_values.get(k, 0)), 3) if isinstance(feature_values.get(k), (int, float)) else feature_values.get(k)}
                for k, v in negative
            ],
            "base_probability": round(float(explainer.expected_value[1] if isinstance(explainer.expected_value, (list, np.ndarray)) else explainer.expected_value), 4),
        }
    except Exception as exc:
        logger.warning("SHAP falhou: %s", exc)
        return {"available": False, "error": str(exc)}

def build_rule_based_explanation(candidate: dict) -> dict[str, Any]:
    """
    Explicação baseada em regras quando SHAP não está disponível.
    Usa os campos do candidato para construir uma explicação legível.
    """
    strengths = []
    risks = []

    ml_prob = float(candidate.get("ml_probability") or candidate.get("ensemble_probability") or 0)
    consistency = float(candidate.get("consistency_score") or 0)
    true_ev = float(candidate.get("true_ev") or 0)
    edge_pct = float(candidate.get("edge_pct") or candidate.get("edge_over_market") or 0) * 100
    odds = float(candidate.get("odds") or 0)
    movement_type = candidate.get("movement_type", "")
    steam = bool(candidate.get("steam_detected", False))
    rule_status = str(candidate.get("rule_status", "")).upper()
    risk_flags = str(candidate.get("risk_flags") or "")

    # Pontos fortes
    if ml_prob >= 0.60:
        strengths.append(f"Alta probabilidade ML: {ml_prob:.1%}")
    elif ml_prob >= 0.55:
        strengths.append(f"Probabilidade ML favorável: {ml_prob:.1%}")

    if consistency >= 70:
        strengths.append(f"Estratégia altamente consistente (score {consistency:.0f}/100)")
    elif consistency >= 55:
        strengths.append(f"Estratégia moderadamente consistente (score {consistency:.0f}/100)")

    if true_ev > 0.05:
        strengths.append(f"Excelente value signal: EV real +{true_ev:.2%}")
    elif true_ev > 0.02:
        strengths.append(f"Value signal identificado: EV real +{true_ev:.2%}")

    if steam:
        strengths.append("Steam move detectado: dinheiro profissional na mesma direção")
    elif movement_type == "SHARP_MOVEMENT":
        strengths.append("Movimento sharp nas odds confirma o sinal")

    if rule_status == "KEEP":
        strengths.append("Estratégia aprovada no backtest histórico")

    # Riscos
    flags = [f.strip() for f in risk_flags.replace(",", "|").split("|") if f.strip()]
    if "LOW_SAMPLE_SIZE" in flags:
        risks.append("Amostra histórica pequena — confiança limitada")
    if "HIGH_DRAWDOWN" in flags:
        risks.append("Drawdown histórico elevado nesta estratégia")
    if "POSSIBLE_OVERFITTING" in flags:
        risks.append("Possível overfitting no modelo")
    if odds < 1.50:
        risks.append(f"Odds baixas ({odds}) limitam o retorno potencial")
    if ml_prob < 0.52:
        risks.append(f"Probabilidade ML próxima do aleatório ({ml_prob:.1%})")

    return {
        "strengths": strengths,
        "risks": risks,
        "method": "rule_based",
    }

def generate_explanation_text(candidate: dict, shap_result: dict | None = None) -> str:
    """
    Gera texto de explicação em português para o Telegram/dashboard.
    """
    home = candidate.get("home_team", "?")
    away = candidate.get("away_team", "?")
    market = str(candidate.get("market", "")).upper()
    odds = float(candidate.get("odds") or 0)
    ml_prob = float(candidate.get("ml_probability") or candidate.get("ensemble_probability") or 0)
    true_ev = float(candidate.get("true_ev") or 0)
    edge_pct = float(candidate.get("edge_pct") or 0)
    kelly_pct = float(candidate.get("kelly_stake_pct") or 0)

    lines = [
        f"🎯 <b>{home} x {away}</b>",
        f"📊 Mercado: <b>{market}</b> @ {odds:.2f}",
        f"🤖 Prob ML: <b>{ml_prob:.1%}</b> | True EV: <b>{true_ev:+.2%}</b>",
        f"📈 Edge sobre mercado: <b>{edge_pct:+.1f}%</b>",
        f"💰 Kelly recomendado: <b>{kelly_pct:.1%}</b> da banca",
    ]

    if shap_result and shap_result.get("available"):
        pos = shap_result.get("top_positive", [])
        if pos:
            lines.append("\n✅ <b>Principais razões PARA considerar:</b>")
            for f in pos[:3]:
                lines.append(f"  • {f['label']}: {f['feature_value']}")

        neg = shap_result.get("top_negative", [])
        if neg:
            lines.append("\n⚠️ <b>Fatores de risco:</b>")
            for f in neg[:2]:
                lines.append(f"  • {f['label']}: {f['feature_value']}")
    else:
        rule_expl = build_rule_based_explanation(candidate)
        if rule_expl["strengths"]:
            lines.append("\n✅ <b>Por que considerar:</b>")
            for s in rule_expl["strengths"][:3]:
                lines.append(f"  • {s}")
        if rule_expl["risks"]:
            lines.append("\n⚠️ <b>Riscos:</b>")
            for r in rule_expl["risks"][:2]:
                lines.append(f"  • {r}")

    steam = candidate.get("steam_detected")
    if steam:
        lines.append("\n🔥 <b>STEAM MOVE detectado</b> — dinheiro profissional nesta direção")

    lines.append("\n⚠️ <i>Confirmação manual obrigatória antes de qualquer ação real.</i>")

    return "\n".join(lines)

def enrich_candidates_with_explanations(candidates_df: pd.DataFrame,
                                         models_dir: Path | None = None) -> pd.DataFrame:
    """
    Enriquece candidatos com explicações SHAP ou baseadas em regras.
    """
    if candidates_df.empty:
        return candidates_df

    df = candidates_df.copy()

    # Tentar carregar modelos ML para SHAP
    shap_models = {}
    if models_dir is not None and models_dir.exists():
        try:
            import joblib
            for model_path in models_dir.glob("*.pkl"):
                market = model_path.stem.replace("_model", "").replace("model_", "")
                try:
                    shap_models[market] = joblib.load(model_path)
                except Exception:
                    pass
        except ImportError:
            pass

    explanations = []
    for _, row in df.iterrows():
        candidate = row.to_dict()
        shap_result = None  # SHAP requer features do match, simplificado aqui

        rule_expl = build_rule_based_explanation(candidate)
        text = generate_explanation_text(candidate, shap_result)

        explanations.append({
            "explanation_text": text,
            "strengths_list": " | ".join(rule_expl["strengths"]),
            "risks_list": " | ".join(rule_expl["risks"]),
        })

    expl_df = pd.DataFrame(explanations, index=df.index)
    df["explanation_text"] = expl_df["explanation_text"]
    df["strengths_list"] = expl_df["strengths_list"]
    df["risks_list"] = expl_df["risks_list"]

    return df

if __name__ == "__main__":
    sample = {
        "home_team": "Arsenal", "away_team": "Chelsea",
        "market": "goals", "odds": 1.85,
        "ml_probability": 0.62, "ensemble_probability": 0.60,
        "true_ev": 0.07, "edge_pct": 0.08, "kelly_stake_pct": 0.03,
        "consistency_score": 72, "rule_status": "KEEP",
        "steam_detected": True, "movement_type": "SHARP_MOVEMENT",
        "risk_flags": "",
    }
    print(generate_explanation_text(sample))
