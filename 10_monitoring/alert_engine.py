from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .common import MODE, project_root, safe_json, write_json


class AlertEngine:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or project_root()
        self.monitoring_dir = self.root / "data/monitoring"

    @staticmethod
    def _alert(category: str, severity: str, code: str, message: str, next_step: str) -> dict[str, Any]:
        return {
            "category": category,
            "severity": severity,
            "code": code,
            "message": message,
            "next_step": next_step,
            "mode": MODE,
        }

    def generate(self) -> dict[str, Any]:
        status = safe_json(self.root / "data/monitoring/monitoring_status.json", {})
        drift = safe_json(self.root / "data/monitoring/drift_report.json", {})
        anomalies = safe_json(self.root / "data/monitoring/anomaly_report.json", {})
        ops = status.get("data_ops", {})
        paper = status.get("paper_trading", {})
        decision = status.get("decision_engine", {})
        alerts: list[dict[str, Any]] = []

        if ops.get("engine_status") in {"ENGINE_MISSING", "ENGINE_OUTPUTS_EMPTY"}:
            alerts.append(self._alert(
                "DATA", "HIGH", "ENGINE_DATA_UNAVAILABLE",
                "Provider interno FlashScore está sem outputs históricos locais.",
                "Rodar o provider interno FlashScore ou validar o relatório operacional antes de atualizar bases.",
            ))
        if ops.get("future_games_status") in {"FUTURE_GAMES_EMPTY", "FUTURE_GAMES_NO_DATA_FILES"}:
            alerts.append(self._alert(
                "DATA", "MEDIUM", "FUTURE_GAMES_UNAVAILABLE",
                "A pasta de jogos futuros não possui arquivos de dados utilizáveis.",
                "Gerar arquivos em jogos_futuros antes de executar simulações forward.",
            ))
        if float(paper.get("roi") or 0) < -0.10:
            alerts.append(self._alert("PERFORMANCE", "HIGH", "PAPER_ROI_DROP", "ROI do paper trading está negativo em nível relevante.", "Revisar refinamento e reduzir confiança operacional simulada."))
        if float(paper.get("max_drawdown") or 0) < -20:
            alerts.append(self._alert("PERFORMANCE", "HIGH", "PAPER_DRAWDOWN_SPIKE", "Drawdown do paper trading excedeu limite de atenção.", "Pausar conclusões e revisar mercados/ligas responsáveis."))
        if drift.get("drift_detected"):
            alerts.append(self._alert("ML", "MEDIUM", "DRIFT_DETECTED", "Drift detectado em features ou probabilidades.", "Comparar distribuição recente com baseline antes de confiar em probabilidades."))
        if anomalies.get("anomalies_detected"):
            alerts.append(self._alert("SYSTEM", "MEDIUM", "ANOMALIES_DETECTED", "Anomalias detectadas no monitoramento.", "Inspecionar anomaly_report.json para causas prováveis."))
        total = int(decision.get("total_candidates") or 0)
        rejected = int(decision.get("rejected_candidates") or 0)
        if total > 0 and rejected / total > 0.70:
            alerts.append(self._alert("DECISION_ENGINE", "MEDIUM", "HIGH_REJECTION_RATE", "Decision Engine está rejeitando mais de 70% dos candidatos.", "Verificar risk flags, qualidade dos dados e thresholds de simulação."))
        if total > 0 and int(decision.get("high_confidence_candidates") or 0) == 0:
            alerts.append(self._alert("DECISION_ENGINE", "LOW", "NO_HIGH_CONFIDENCE", "Nenhum candidato de alta confiança em simulação foi encontrado.", "Aguardar mais dados ou revisar consistência das estratégias KEEP."))

        payload = {
            "ok": True,
            "mode": MODE,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_alerts": len(alerts),
            "highest_severity": self._highest(alerts),
            "alerts": alerts,
        }
        write_json(self.monitoring_dir / "alerts.json", payload)
        return payload

    @staticmethod
    def _highest(alerts: list[dict[str, Any]]) -> str:
        order = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}
        if not alerts:
            return "NONE"
        return max(alerts, key=lambda a: order.get(str(a.get("severity")), 0)).get("severity", "LOW")
