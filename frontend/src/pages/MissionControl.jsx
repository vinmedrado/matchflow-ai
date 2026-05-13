import { useEffect, useState } from 'react';
import { api } from '../api/client.js';

const PAGE_BY_ACTION = {
  'Central de Dados': 'Data Center',
  'Qualidade de Dados': 'Data Quality',
  'Backtest Intelligence': 'Backtest Intelligence',
  'ML Intelligence': 'ML Intelligence',
  'Risk Engine': 'Risk Engine',
  'Jobs Center': 'Jobs Center',
};

function StageCard({ stage, index, setPage }) {
  return <button className={`mission-stage ${stage.status}`} onClick={() => setPage(PAGE_BY_ACTION[stage.action] || 'Product Cockpit')}>
    <span className="mission-index">{String(index + 1).padStart(2, '0')}</span>
    <div>
      <b>{stage.name}</b>
      <small>{stage.owner}</small>
      <p>{stage.why}</p>
    </div>
    <em>{stage.status}</em>
  </button>;
}

export default function MissionControl({ setPage }) {
  const [data, setData] = useState(null);
  useEffect(() => { api.platformMissionControl().then(r => setData(r.data)).catch(() => setData(null)); }, []);
  return <div className="page erp-page">
    <section className="erp-hero mission-hero">
      <div>
        <span className="brand-pill">Mission Control</span>
        <h1>Fluxo guiado do MatchFlow</h1>
        <p>{data?.headline || 'Operação guiada para transformar scripts, dados, backtest, ML e banca em produto de verdade.'}</p>
        <div className="hero-actions">
          <button className="btn btn-primary" onClick={() => setPage('Data Center')}>Começar pela Central de Dados</button>
          <button className="btn btn-secondary" onClick={() => setPage('API Catalog')}>Entender APIs</button>
        </div>
      </div>
      <div className="hero-score-card clean"><span>Readiness</span><strong>{data?.readiness_score ?? 0}%</strong><small>{data?.warning || 'Modo seguro'}</small></div>
    </section>

    <section className="section-block">
      <div className="section-title-row"><h2>Este é o fluxo que o cliente entende</h2><span>Sem pasta técnica, sem terminal obrigatório</span></div>
      <div className="mission-timeline">
        {(data?.stages || []).map((stage, index) => <StageCard key={stage.id} stage={stage} index={index} setPage={setPage} />)}
      </div>
    </section>

    <section className="section-block split-2">
      <div className="panel-card">
        <h3>O que precisa virar automático</h3>
        <p className="muted-text">Cada etapa deve registrar status, logs, duração, resultado e erro em banco. Isso tira o sistema da aparência de projeto local e aproxima de SaaS real.</p>
      </div>
      <div className="panel-card">
        <h3>O que já pode ser demo</h3>
        <p className="muted-text">Login, cockpit, Central de Dados, navegação premium, backtest/ML/risk intelligence e scheduler já formam uma narrativa forte de portfólio.</p>
      </div>
    </section>
  </div>;
}
