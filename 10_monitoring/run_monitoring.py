from __future__ import annotations

import importlib
import logging
import sys
import types
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _bootstrap_monitoring_imports() -> tuple[Any, Any, str, Any, Any, Any, Any]:
    """Carrega módulos de monitoring tanto como package quanto como script direto.

    O diretório começa com número (`10_monitoring`), então import tradicional por
    statement não é confiável em todos os contextos. O alias sintético abaixo cria
    um contexto de package estável para imports relativos internos.
    """
    if __package__ in {None, ""}:
        package_name = "matchflow_runtime_monitoring"
        package_dir = Path(__file__).resolve().parent
        if package_name not in sys.modules:
            package = types.ModuleType(package_name)
            package.__path__ = [str(package_dir)]  # type: ignore[attr-defined]
            sys.modules[package_name] = package
        alert_mod = importlib.import_module(f"{package_name}.alert_engine")
        anomaly_mod = importlib.import_module(f"{package_name}.anomaly_detector")
        common_mod = importlib.import_module(f"{package_name}.common")
        drift_mod = importlib.import_module(f"{package_name}.drift_detector")
        performance_mod = importlib.import_module(f"{package_name}.performance_monitor")
        system_mod = importlib.import_module(f"{package_name}.system_monitor")
        return (
            alert_mod.AlertEngine,
            anomaly_mod.AnomalyDetector,
            common_mod.MODE,
            common_mod.project_root,
            common_mod.write_json,
            drift_mod.DriftDetector,
            performance_mod.PerformanceMonitor,
            system_mod.SystemMonitor,
        )

    from .alert_engine import AlertEngine
    from .anomaly_detector import AnomalyDetector
    from .common import MODE, project_root, write_json
    from .drift_detector import DriftDetector
    from .performance_monitor import PerformanceMonitor
    from .system_monitor import SystemMonitor

    return AlertEngine, AnomalyDetector, MODE, project_root, write_json, DriftDetector, PerformanceMonitor, SystemMonitor


AlertEngine, AnomalyDetector, MODE, project_root, write_json, DriftDetector, PerformanceMonitor, SystemMonitor = _bootstrap_monitoring_imports()

logger = logging.getLogger("matchflow.monitoring.runner")


class MonitoringRunner:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or project_root()
        self.monitoring_dir = self.root / "data/monitoring"
        self.monitoring_dir.mkdir(parents=True, exist_ok=True)

    def run(self) -> dict[str, Any]:
        logger.info("Iniciando monitoramento em modo PAPER_TRADING_SIMULATION_ONLY")
        status = SystemMonitor(self.root).collect()
        drift = DriftDetector(self.root).detect()
        anomalies = AnomalyDetector(self.root).detect()
        performance = PerformanceMonitor(self.root).collect()
        alerts = AlertEngine(self.root).generate()
        journal = self._journal(status, alerts, drift, anomalies, performance)
        (self.monitoring_dir / "monitoring_journal.md").write_text(journal, encoding="utf-8")
        result = {
            "ok": True,
            "mode": MODE,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "alerts": alerts,
            "drift": drift,
            "anomalies": anomalies,
            "performance": performance,
        }
        logger.info("Monitoramento concluído com %s alertas", alerts.get("total_alerts", 0))
        return result

    @staticmethod
    def _journal(status: dict[str, Any], alerts: dict[str, Any], drift: dict[str, Any], anomalies: dict[str, Any], performance: dict[str, Any]) -> str:
        lines = [
            "# MatchFlow Monitoring Journal",
            "",
            f"Modo: {MODE}",
            f"Status geral: {status.get('overall_status')}",
            f"Risco: {status.get('risk_level')}",
            f"Alertas ativos: {alerts.get('total_alerts', 0)}",
            f"Drift detectado: {drift.get('drift_detected')}",
            f"Anomalias detectadas: {anomalies.get('anomalies_detected')}",
            f"Paper ROI: {performance.get('paper_roi')}",
            f"Paper Drawdown: {performance.get('paper_max_drawdown')}",
            "",
            "## Aviso",
            "Este monitoramento é exclusivo para simulação/paper trading. Nenhuma ação real é executada.",
        ]
        for alert in alerts.get("alerts", []):
            lines.extend(["", f"- [{alert.get('severity')}] {alert.get('code')}: {alert.get('message')}"])
        return "\n".join(lines) + "\n"


def run_monitoring(root: Path | None = None) -> dict[str, Any]:
    return MonitoringRunner(root).run()


def main(root: Path | None = None) -> dict[str, Any]:
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s")
    result = run_monitoring(root)
    logger.info("Resultado monitoring: %s", result.get("status", {}).get("overall_status"))
    return result


if __name__ == "__main__":
    main(Path.cwd())
