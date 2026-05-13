from __future__ import annotations

__test__ = False
import csv, json, importlib.util
from pathlib import Path
MODE="PAPER_TRADING_SIMULATION_ONLY"
def project_root(): return Path(__file__).resolve().parents[2]
def _json(p):
    try: return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except Exception: return {}
def _csv(p):
    if not p.exists(): return []
    with p.open(newline="",encoding="utf-8") as f: return list(csv.DictReader(f))
def test_lab_status():
    root=project_root(); return {"mode":MODE,"report_exists":(root/"data/test_lab/test_lab_report.json").exists(),"future_games_snapshot_exists":(root/"jogos_futuros").exists(),"paper_summary_exists":(root/"data/paper_trading/paper_summary.json").exists(),"ml_summary_exists":(root/"data/ml/models/registry.json").exists(),"last_report":_json(root/"data/test_lab/test_lab_report.json"),"message":"Ambiente de simulação. Este sistema não executa operações reais."}
def run_test_lab():
    root=project_root(); spec=importlib.util.spec_from_file_location("test_lab_runner",root/"08_test_lab/test_lab_runner.py"); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod.run_test_lab(root)
def test_lab_report(): return {"mode":MODE,"report":_json(project_root()/"data/test_lab/test_lab_report.json")}
def test_lab_candidates():
    rows=_csv(project_root()/"data/test_lab/simulated_candidates.csv"); return {"mode":MODE,"total":len(rows),"items":rows}
def calibration_summary(): return {"mode":MODE,"data":_json(project_root()/"data/ml/evaluation/calibration_report.json")}
def ensemble_summary(): return {"mode":MODE,"data":_json(project_root()/"data/ml/evaluation/ensemble_metrics.json")}
