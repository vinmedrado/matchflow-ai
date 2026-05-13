import { useEffect, useState } from 'react';
import { api } from '../api/client.js';

export default function DecisionRoom({ setPage }) {
  const [data, setData] = useState(null);
  useEffect(() => { api.platformDecisionRoom().then(r => setData(r.data)).catch(() => setData(null)); }, []);
  const checklist = data?.decision_checklist || [];
  return <div className="page erp-page">
    <section className="erp-hero decision-hero">
      <div>
        <span className="brand-pill">Decision Room</span>
        <h1>Sala de decisão</h1>
        <p>Um painel para entender sinais, risco, amostra, EV e stake antes de qualquer ação operacional.</p>
        <div className="hero-actions">
          <button className="btn btn-primary" onClick={() => setPage('Decision Engine')}>Abrir motor atual</button>
          <button className="btn btn-secondary" onClick={() => setPage('Risk Engine')}>Revisar banca</button>
        </div>
      </div>
      <div className="hero-score-card clean"><span>Sinais</span><strong>{data?.summary?.signals_available ?? 0}</strong><small>{data?.mode || 'paper trading'}</small></div>
    </section>
    <section className="section-block split-2">
      <div className="panel-card">
        <h3>Checklist de decisão</h3>
        <div className="gate-grid compact">
          {checklist.map((item) => <div key={item.label} className={`gate-card ${item.passed ? 'ok' : 'warn'}`}><b>{item.label}</b><span>{item.passed ? 'ok' : 'pendente'}</span></div>)}
        </div>
      </div>
      <div className="panel-card insight-box light">
        <h3>Nota operacional</h3>
        <p>{data?.operator_note}</p>
      </div>
    </section>
    <section className="section-block">
      <div className="section-title-row"><h2>Candidatos principais</h2><span>preview dos sinais disponíveis</span></div>
      <div className="signal-table">
        {(data?.top_candidates || []).length === 0 ? <div className="empty-premium">Nenhum sinal gerado ainda. Rode Data Engine → Backtest → ML → Decision Engine.</div> :
          data.top_candidates.map((row, idx) => <div className="signal-row" key={idx}>{Object.entries(row).slice(0, 6).map(([k, v]) => <span key={k}><small>{k}</small><b>{String(v)}</b></span>)}</div>)}
      </div>
    </section>
  </div>;
}
