import { useEffect, useState } from 'react';
import { api } from '../api/client.js';
import { useI18n } from '../i18n.js';

function Kpi({ label, value, hint }) {
  return <div className="erp-kpi"><span>{label}</span><strong>{value}</strong><small>{hint}</small></div>;
}

export default function ProductCockpit({ setPage }) {
  const { t } = useI18n();
  const [data, setData] = useState(null);
  useEffect(() => { api.platformCockpit().then(r => setData(r.data)).catch(() => setData(null)); }, []);
  const k = data?.kpis || {};
  return <div className="page erp-page">
    <section className="erp-hero light-hero">
      <div>
        <span className="brand-pill">MatchFlow SaaS Blueprint</span>
        <h1>Cockpit do Produto</h1>
        <p>Visão executiva para transformar o projeto autoral em plataforma vendável: dados, backtest, ML, decisão, banca e operação online.</p>
        <div className="hero-actions">
          <button className="btn btn-primary" onClick={() => setPage('Data Center')}>Começar pela Central de Dados</button>
          <button className="btn btn-secondary" onClick={() => setPage('Jobs Center')}>Ver Jobs</button>
        </div>
      </div>
      <div className="hero-score-card clean"><span>Readiness SaaS</span><strong>{data?.readiness_score ?? 0}%</strong><small>{data?.positioning || 'Carregando...'}</small></div>
    </section>
    <section className="premium-grid-5">
      <Kpi label="Jogos" value={k.matches ?? 0} hint="base atual" />
      <Kpi label="Ligas" value={k.leagues ?? 0} hint="campeonatos" />
      <Kpi label="Times" value={k.teams ?? 0} hint="entidades" />
      <Kpi label="Backtest" value={k.backtest_trades ?? 0} hint="trades simulados" />
      <Kpi label="Sinais" value={k.active_signals ?? 0} hint="candidatos" />
    </section>
    <section className="section-block">
      <div className="section-title-row"><h2>Próximas ações</h2><span>Fluxo guiado para produto</span></div>
      <div className="action-stack">
        {(data?.next_actions || []).map((a, idx) => <button key={idx} className="action-row" onClick={() => setPage(a.area === 'Central de Dados' ? 'Data Center' : a.area)}>
          <b>{a.label}</b><span>{a.area}</span><em>{a.priority}</em>
        </button>)}
      </div>
    </section>
  </div>;
}
