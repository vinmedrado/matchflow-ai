from pathlib import Path
import importlib.util
def root(): return Path(__file__).resolve().parents[2]
def load(rel):
 spec=importlib.util.spec_from_file_location(rel.replace('/','_'),root()/rel); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
def test_decision_candidates_allowed_only():
 rows=load('08_test_lab/decision_research_engine.py').build_simulated_candidates(root(),10)
 assert all(r['recommendation_type'] in {'SIMULATION_CANDIDATE','WATCH_ONLY','REJECTED'} for r in rows)
 text=' '.join(str(v) for r in rows for v in r.values()).upper()
 for term in ['BET','APOSTAR','REAL_ENTRY','STAKE_NOW']: assert term not in text
def test_outputs_generate():
 assert load('06_ml/calibration.py').run_calibration(root())['mode']=='PAPER_TRADING_SIMULATION_ONLY'
 assert load('06_ml/ensemble.py').run_ensemble(root())['mode']=='PAPER_TRADING_SIMULATION_ONLY'
 assert load('08_test_lab/test_lab_runner.py').run_test_lab(root())['mode']=='PAPER_TRADING_SIMULATION_ONLY'
def test_viewer_cannot_run_test_lab(client):
 login=client.post('/api/auth/login',json={'email':'viewer@matchflow.local','password':'viewer123'}); assert login.status_code==200
 r=client.post('/api/test-lab/run',headers={'Authorization':f"Bearer {login.json()['access_token']}"}); assert r.status_code==403
def test_analyst_can_run_test_lab(client):
 login=client.post('/api/auth/login',json={'email':'analyst@matchflow.local','password':'analyst123'}); assert login.status_code==200
 r=client.post('/api/test-lab/run',headers={'Authorization':f"Bearer {login.json()['access_token']}"}); assert r.status_code==200
def test_endpoints_work(client):
 login=client.post('/api/auth/login',json={'email':'admin@matchflow.local','password':'admin123'}); h={'Authorization':f"Bearer {login.json()['access_token']}"}
 for p in ['/api/test-lab/status','/api/test-lab/report','/api/test-lab/candidates','/api/ml/calibration-summary','/api/ml/ensemble-summary']:
  r=client.get(p,headers=h); assert r.status_code==200; assert r.json()['ok'] is True
