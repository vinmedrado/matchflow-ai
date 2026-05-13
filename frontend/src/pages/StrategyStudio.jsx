import { useEffect, useState } from 'react';
import { api } from '../api/client.js';

export default function StrategyStudio() {
  const [bankroll, setBankroll] = useState(1000);
  const [risk, setRisk] = useState('balanced');
  const [data, setData] = useState(null);
  useEffect(() => { api.platformStrategyStudio(bankroll, risk).then(r => setData(r.data)).catch(() => setData(null)); }, [bankroll, risk]);
  return <div className="page erp-page">
    <section className="erp-hero strategy-hero">
      <div>
        <span className="brand-pill">Strategy Studio</span>
        <h1>Estratégia e banca inteligente</h1>
        <p>Configure banca, perfil de risco e presets para o sistema recomendar stake sem depender de regra fixa.</p>
        <div className="quick-actions-panel inputs">
          <label>Banca<input type="number" value={bankroll} min="1" onChange={e => setBankroll(Number(e.target.value || 0))} /></label>
          <label>Perfil<select value={risk} onChange={e => setRisk(e.target.value)}><option value="conservative">Conservador</option><option value="balanced">Balanceado</option><option value="aggressive">Agressivo</option></select></label>
        </div>
      </div>
      <div className="hero-score-card clean"><span>Método</span><strong className="small-strong">{data?.recommended_policy?.recommended_method || '-'}</strong><small>stake máx: {data?.recommended_policy?.max_stake_value ?? 0}</small></div>
    </section>
    <section className="section-block">
      <div className="section-title-row"><h2>Presets comerciais</h2><span>do conservador ao ML calibrado</span></div>
      <div className="preset-grid">
        {(data?.presets || []).map(p => <div className="preset-card" key={p.id}><span>{p.ml_required ? 'ML requerido' : 'Sem ML obrigatório'}</span><h3>{p.name}</h3><p>{p.best_for}</p><b>{p.stake_method}</b><small>Exposição diária: {p.max_daily_exposure}</small></div>)}
      </div>
    </section>
    <section className="section-block">
      <div className="section-title-row"><h2>Guardrails</h2><span>regras para não vender ilusão estatística</span></div>
      <div className="rule-grid">{(data?.guardrails || []).map((rule, idx) => <div className="rule-card" key={rule}><span>{idx + 1}</span><p>{rule}</p></div>)}</div>
    </section>
  </div>;
}
