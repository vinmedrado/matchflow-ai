export function unwrap(payload) {
  return payload?.data ?? payload ?? {};
}

export function PremiumHeader({ eyebrow, title, subtitle, actions }) {
  return (
    <section className="premium-hero">
      <div>
        <span className="premium-eyebrow">{eyebrow}</span>
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </div>
      {actions && <div className="premium-actions">{actions}</div>}
    </section>
  );
}

export function DataStateBadge({ state = 'no_data' }) {
  const label = {
    real_data: 'dados reais', partial_data: 'dados parciais', no_data: 'sem dados',
    unavailable_data: 'indisponível', simulated_data: 'simulação segura'
  }[state] || state;
  return <span className={`data-state state-${state}`}>{label}</span>;
}

export function PremiumState({ loading, error, empty, message, onRetry }) {
  if (loading) return <div className="premium-skeleton"><i/><i/><i/></div>;
  if (error) return <div className="premium-empty"><b>Falha ao carregar dados reais.</b><small>{String(error.message || error)}</small>{onRetry && <button onClick={onRetry}>Tentar novamente</button>}</div>;
  if (empty) return <div className="premium-empty"><b>Sem dados operacionais reais.</b><small>{message || 'Rode os pipelines correspondentes para popular esta visão. Nenhum número foi simulado.'}</small></div>;
  return null;
}

export function StatTile({ label, value, sub, tone = 'blue', state }) {
  const empty = value === null || value === undefined || value === '';
  return <div className={`quant-tile tone-${tone} ${empty ? 'is-empty' : ''}`}><span>{label}</span><strong>{empty ? '—' : value}</strong><small>{sub}</small>{state && <DataStateBadge state={state}/>}</div>;
}

export function MiniBarChart({ data = [], valueKey = 'value', labelKey = 'name', compact = false }) {
  if (!data?.length) return <PremiumState empty message="Série vazia: não há amostra real suficiente para desenhar o ranking." />;
  const max = Math.max(1, ...data.map(d => Math.abs(Number(d[valueKey]) || 0)));
  return <div className={`mini-bars ${compact ? 'compact' : ''}`}>{data.slice(0, 12).map((d, i) => {
    const v = Number(d[valueKey]) || 0;
    return <div className="mini-bar-row" key={`${d[labelKey]}-${i}`}>
      <span title={d[labelKey]}>{d[labelKey] || 'N/D'}</span>
      <div><i style={{ width: `${Math.max(4, Math.abs(v) / max * 100)}%` }} className={v >= 0 ? 'positive' : 'negative'} /></div>
      <b>{v > 0 ? '+' : ''}{v.toFixed(1)}</b>
    </div>;
  })}</div>;
}

export function Sparkline({ data = [], valueKey = 'value' }) {
  const values = (data || []).map(d => Number(d[valueKey])).filter(v => Number.isFinite(v));
  if (values.length < 2) return <PremiumState empty message="Sem série real suficiente para gráfico." />;
  const min = Math.min(...values), max = Math.max(...values), range = max - min || 1;
  const pts = values.map((v, i) => `${(i/(values.length-1))*100},${42 - ((v-min)/range)*36}`).join(' ');
  return <svg className="sparkline" viewBox="0 0 100 48" preserveAspectRatio="none"><polyline points={pts} /></svg>;
}

export function SignalCard({ signal }) {
  if (!signal) return <PremiumState empty message="Nenhum sinal real selecionado." />;
  const ev = Number(signal.true_ev);
  const ml = Number(signal.ml_probability);
  const risk = Number(signal.risk_score);
  return <article className="signal-premium-card">
    <div className="signal-top"><b>{signal.home_team || 'Time A'} <em>x</em> {signal.away_team || 'Time B'}</b><span>{signal.confidence_band || signal.data_state || 'N/D'}</span></div>
    <small>{signal.league || 'Liga não informada'} • {signal.market || 'Mercado N/D'} • odds {signal.odds ? Number(signal.odds).toFixed(2) : '—'}</small>
    <div className="score-ring"><strong>{signal.decision_score != null ? Number(signal.decision_score).toFixed(0) : '—'}</strong><span>AI Score</span></div>
    <div className="signal-metrics"><span>EV <b className={ev >= 0 ? 'good' : 'bad'}>{Number.isFinite(ev) ? `${ev >= 0 ? '+' : ''}${(ev*100).toFixed(1)}%` : '—'}</b></span><span>ML <b>{Number.isFinite(ml) ? `${(ml*100).toFixed(0)}%` : '—'}</b></span><span>Risk <b>{Number.isFinite(risk) ? risk.toFixed(0) : '—'}</b></span></div>
    <DataStateBadge state={signal.data_state || 'real_data'} />
  </article>;
}

export function Radar({ data = [] }) {
  const axes = data || [];
  if (axes.length < 3) return <PremiumState empty message="Radar indisponível: faltam métricas reais suficientes." />;
  const cx = 50, cy = 50, r = 38;
  const points = axes.map((d, i) => {
    const a = -Math.PI/2 + (Math.PI*2*i/axes.length);
    const rr = r * Math.max(0, Math.min(100, Number(d.value)||0)) / 100;
    return `${cx + Math.cos(a)*rr},${cy + Math.sin(a)*rr}`;
  }).join(' ');
  return <svg className="radar" viewBox="0 0 100 100">
    {[.25,.5,.75,1].map(t => <circle key={t} cx={cx} cy={cy} r={r*t} />)}
    {axes.map((d,i)=>{ const a=-Math.PI/2+(Math.PI*2*i/axes.length); return <g key={d.axis}><line x1={cx} y1={cy} x2={cx+Math.cos(a)*r} y2={cy+Math.sin(a)*r}/><text x={cx+Math.cos(a)*(r+8)} y={cy+Math.sin(a)*(r+8)}>{d.axis}</text></g>; })}
    <polygon points={points}/>
  </svg>;
}
