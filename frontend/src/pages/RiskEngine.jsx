import { useEffect, useState } from 'react';
import { api } from '../api/client.js';

export default function RiskEngine() {
  const [bankroll, setBankroll] = useState(1000);
  const [profile, setProfile] = useState('balanced');
  const [data, setData] = useState(null);
  useEffect(() => { api.platformRiskEngine(bankroll, profile).then(r => setData(r.data)).catch(() => setData(null)); }, [bankroll, profile]);
  return <div className="page erp-page">
    <section className="erp-hero risk-hero"><div><span className="brand-pill">Smart Bankroll</span><h1>Risk Engine</h1><p>A banca deixa de ser manual: o sistema escolhe stake fixa, híbrido ou Kelly fracionado conforme banca, risco, drawdown e qualidade do sinal.</p></div><div className="hero-score-card clean"><span>Método</span><strong>{data?.recommended_method || '—'}</strong><small>Stake máxima: R$ {data?.max_stake_value ?? 0}</small></div></section>
    <section className="quick-actions-panel inputs"><label>Banca <input type="number" value={bankroll} onChange={e => setBankroll(Number(e.target.value || 0))} /></label><label>Perfil <select value={profile} onChange={e => setProfile(e.target.value)}><option value="conservative">Conservador</option><option value="balanced">Balanceado</option><option value="aggressive">Agressivo</option></select></label></section>
    <section className="section-block"><div className="section-title-row"><h2>Regras automáticas</h2><span>Proteção operacional</span></div><div className="rule-grid">{(data?.automatic_rules || []).map((r, i) => <div className="rule-card" key={r}><span>{i+1}</span><p>{r}</p></div>)}</div></section>
  </div>;
}
