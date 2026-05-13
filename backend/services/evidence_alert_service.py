from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from backend.services.ml_calibration_service import build_calibration_report
from backend.services.model_health_service import build_model_health_report
MODE="PAPER_TRADING_SIMULATION_ONLY"
def project_root() -> Path: return Path(__file__).resolve().parents[2]
def build_evidence_alerts(root: Path | None=None) -> dict[str, Any]:
    root=Path(root) if root else project_root(); cal=build_calibration_report(root); health=build_model_health_report(root); alerts=[]
    if not cal.get('is_real_calibration'):
        alerts.append({'alert_type':'CALIBRATION_EVIDENCE','severity':'warning','code':'REAL_CALIBRATION_UNAVAILABLE','message':'Calibração real indisponível: amostra real liquidada insuficiente.','context':cal.get('fallback_reason'),'source_type_breakdown':cal.get('source_type_breakdown',{}),'recommendation':'Acumule resultados reais liquidados pelo Data Engine/FlashScore antes de tratar calibração como real.'})
    if cal.get('fallback_sample_size',0):
        alerts.append({'alert_type':'FALLBACK_EVIDENCE','severity':'info','code':'FALLBACK_DATA_EXCLUDED_FROM_REAL_CALIBRATION','message':'Paper/backtest/demo existem, mas foram excluídos da calibração real.','excluded_records_count':cal.get('excluded_records_count',0),'recommendation':'Use esses dados apenas para dashboards/fallback e mantenha separação de evidência.'})
    for model,item in (health.get('models') or {}).items():
        if item.get('reliability_status') in {'fallback_only','insufficient_evidence'}:
            alerts.append({'alert_type':'MODEL_EVIDENCE','severity':'warning' if item.get('reliability_status')=='fallback_only' else 'info','code':'MODEL_NOT_REAL_VERIFIED','model_name':model,'message':f'Modelo {model} sem evidência real suficiente.','health_source_type':item.get('health_source_type'),'real_evidence_score':item.get('real_evidence_score'),'fallback_evidence_score':item.get('fallback_evidence_score'),'recommendation':'Evite promover peso operacional do modelo até haver resultados reais liquidados suficientes.'})
    payload={'ok':True,'mode':MODE,'generated_at':datetime.now(timezone.utc).isoformat(),'total_alerts':len(alerts),'alerts':alerts}; out=root/'data/monitoring/evidence_alerts.json'; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2,ensure_ascii=False,default=str),encoding='utf-8'); return payload
