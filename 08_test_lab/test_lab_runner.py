from __future__ import annotations
from pathlib import Path
import csv, json, sys
HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path: sys.path.insert(0,str(HERE))
from decision_research_engine import build_simulated_candidates, validate_candidates, read_future
MODE="PAPER_TRADING_SIMULATION_ONLY"
def project_root(): return Path(__file__).resolve().parents[1]
def run_test_lab(root=None):
    root=root or project_root(); out=root/"data/test_lab"; out.mkdir(parents=True,exist_ok=True); future=read_future(root); candidates=build_simulated_candidates(root); validate_candidates(candidates)
    base_cols=["match_id","date","league","home_team","away_team","market","strategy","rule_status","ml_probability","ensemble_probability","odds","risk_flags","confidence_band","recommendation_type","mode"]
    extra_cols=[]
    for c in candidates:
        for k in c.keys():
            if k not in base_cols and k not in extra_cols:
                extra_cols.append(k)
    cols=base_cols+extra_cols
    with (out/"simulated_candidates.csv").open("w",newline="",encoding="utf-8") as f: w=csv.DictWriter(f,fieldnames=cols,extrasaction="ignore"); w.writeheader(); w.writerows(candidates)
    with (out/"future_games_test_results.csv").open("w",newline="",encoding="utf-8") as f:
        if future: w=csv.DictWriter(f,fieldnames=list(future[0].keys())); w.writeheader(); w.writerows(future)
        else: f.write("match_id,date,league,home_team,away_team\n")
    report={"mode":MODE,"future_games_rows":len(future),"simulated_candidates":len(candidates),"warning":"Ambiente de simulação. Este sistema não executa operações reais."}
    (out/"test_lab_report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    (out/"test_lab_journal.md").write_text(f"# MatchFlow Test Lab Journal\n\nModo: {MODE}\n\nJogos futuros carregados: {len(future)}\nCandidatos simulados: {len(candidates)}\n\nAviso: ambiente de simulação; não há execução real nem integração externa.\n",encoding="utf-8")
    return report
if __name__=="__main__":
    sys.stdout.write(json.dumps(run_test_lab(),indent=2,ensure_ascii=False))
