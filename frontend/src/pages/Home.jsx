import { useEffect, useState } from 'react';
import { api } from '../api/client.js';
import { useI18n } from '../i18n.js';

const MODULES = [
  { page:'Data Operations', key:'operations', text:'Orquestra FlashScore Engine, bridge e validação dos dados.' },
  { page:'Competitions', key:'competitions', text:'Tabela, jogos, ligas e visão operacional por campeonato.' },
  { page:'Backtest Lab', key:'backtest', text:'Valida estratégia por liga, time, mercado, odds e amostra.' },
  { page:'ML Lab', key:'ml', text:'Modelos treinados depois da camada de backtest e features.' },
  { page:'Bankroll Projection', key:'bankroll', text:'Define stake por risco, banca e qualidade do edge.' },
  { page:'Decision Engine', key:'decision', text:'Transforma odds, ML e backtest em candidatos auditáveis.' },
];

function MiniCard({ title, value, sub }) {
  return <div className="premium-kpi"><span>{title}</span><strong>{value}</strong><small>{sub}</small></div>;
}

export default function Home({ setPage }) {
  const { t } = useI18n();
  const [audit, setAudit] = useState(null);
  const [status, setStatus] = useState(null);

  useEffect(() => {
    Promise.allSettled([api.productAudit(), api.status()]).then(([a, s]) => {
      if (a.status === 'fulfilled') setAudit(a.value?.data || a.value);
      if (s.status === 'fulfilled') setStatus(s.value?.data || s.value);
    });
  }, []);

  return (
    <div className="page premium-page">
      <section className="hero-panel">
        <div>
          <div className="brand-pill">MatchFlow ERP · Paper Trading Safe</div>
          <h1>{t('premiumTitle')}</h1>
          <p>{t('premiumSubtitle')}</p>
          <div className="hero-actions">
            <button className="btn btn-primary" onClick={() => setPage('Data Operations')}>{t('runEngine')}</button>
            <button className="btn btn-secondary" onClick={() => setPage('Competitions')}>{t('competitions')}</button>
            <button className="btn btn-secondary" onClick={() => setPage('Backtest Lab')}>{t('backtestHealth')}</button>
          </div>
        </div>
        <div className="hero-score-card">
          <span>Readiness</span>
          <strong>{audit?.readiness_score ?? 0}%</strong>
          <small>{audit?.readiness_label || 'Aguardando auditoria'}</small>
        </div>
      </section>

      <section className="premium-grid-4">
        <MiniCard title="API" value={status?.api_status || 'online'} sub="FastAPI isolado" />
        <MiniCard title="Dataset" value={status?.dataset_rows ?? 0} sub="jogos na base atual" />
        <MiniCard title="Backtest" value={audit?.backtest?.sample_level || '—'} sub="amostra e consistência" />
        <MiniCard title="Usuários" value={audit?.multi_user?.status || 'local'} sub="base para multi-tenant" />
      </section>

      <section className="section-block">
        <div className="section-title-row"><h2>Mapa operacional</h2><span>Do dado bruto até a decisão</span></div>
        <div className="module-grid-premium">
          {MODULES.map((m) => <button key={m.page} className="module-tile" onClick={() => setPage(m.page)}><b>{t(m.key)}</b><p>{m.text}</p></button>)}
        </div>
      </section>
    </div>
  );
}
