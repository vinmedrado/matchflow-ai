import { useEffect, useState, useCallback } from 'react';
import { apiRequest } from '../api/client.js';

// ─── API helpers ──────────────────────────────────────────────────────────────
const getDecisionSummary  = () => apiRequest('/api/decision-engine/summary');
const getCandidates       = () => apiRequest('/api/decision-engine/candidates');
const getPaperSummary     = () => apiRequest('/api/paper-trading/summary');
const getAutomationStatus = () => apiRequest('/api/automation/status');

// ─── Paleta ───────────────────────────────────────────────────────────────────
const C = {
  bg:       '#0f1117',
  surface:  '#1a1d2e',
  card:     '#232640',
  border:   '#2e3356',
  text:     '#e2e8f0',
  muted:    '#8892b0',
  accent:   '#7c6aff',
  green:    '#22c55e',
  red:      '#ef4444',
  orange:   '#f59e0b',
  blue:     '#3b82f6',
  steam:    '#ff6b35',
};

const fmt = {
  pct:  v => v == null ? '—' : `${(v*100).toFixed(1)}%`,
  pct2: v => v == null ? '—' : `${v >= 0 ? '+' : ''}${v.toFixed(1)}%`,
  brl:  v => v == null ? '—' : `R$ ${Number(v).toFixed(2)}`,
  dec:  v => v == null ? '—' : Number(v).toFixed(2),
  score: v => v == null ? '—' : Number(v).toFixed(0),
};

// ─── Sub-components ───────────────────────────────────────────────────────────
function KpiCard({ label, value, sub, color, icon }) {
  return (
    <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 12,
                  padding: '18px 22px', display: 'flex', flexDirection: 'column', gap: 4 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ color: C.muted, fontSize: 12, fontWeight: 600, textTransform: 'uppercase',
                        letterSpacing: '0.05em' }}>{label}</span>
        {icon && <span style={{ fontSize: 18 }}>{icon}</span>}
      </div>
      <span style={{ color: color || C.text, fontSize: 26, fontWeight: 700, lineHeight: 1.1 }}>{value}</span>
      {sub && <span style={{ color: C.muted, fontSize: 12 }}>{sub}</span>}
    </div>
  );
}

function Badge({ label, color }) {
  const map = { HIGH: C.green, MEDIUM: C.orange, LOW: C.red, STEAM: C.steam };
  const bg = map[color] || C.blue;
  return (
    <span style={{ background: `${bg}22`, color: bg, border: `1px solid ${bg}55`,
                   borderRadius: 6, padding: '2px 8px', fontSize: 11, fontWeight: 700 }}>
      {label}
    </span>
  );
}

function CandidateRow({ c, i }) {
  const ev = c.true_ev != null ? c.true_ev * 100 : null;
  const kelly = c.kelly_stake_pct != null ? c.kelly_stake_pct * 100 : null;
  const score = c.decision_score;
  const steam = c.steam_detected;
  const band = c.confidence_band || '';
  const bandColor = band.includes('HIGH') ? 'HIGH' : band.includes('MEDIUM') ? 'MEDIUM' : 'LOW';
  const marketIcons = { goals: '⚽', corners: '🚩', btts: '🎯', shots: '🥅' };
  const mIcon = marketIcons[c.market] || '📊';

  return (
    <tr style={{ borderBottom: `1px solid ${C.border}`, transition: 'background .15s' }}
        onMouseEnter={e => e.currentTarget.style.background = C.border}
        onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
      <td style={{ padding: '12px 14px', color: C.muted, fontSize: 12 }}>{c.date || '—'}</td>
      <td style={{ padding: '12px 14px' }}>
        <div style={{ fontWeight: 600, color: C.text, fontSize: 13 }}>
          {c.home_team} <span style={{ color: C.muted }}>x</span> {c.away_team}
        </div>
        <div style={{ color: C.muted, fontSize: 11 }}>{c.league}</div>
      </td>
      <td style={{ padding: '12px 14px' }}>
        <span style={{ color: C.text }}>{mIcon} {(c.market || '').toUpperCase()}</span>
        <div style={{ color: C.muted, fontSize: 11 }}>odds {fmt.dec(c.odds)}</div>
      </td>
      <td style={{ padding: '12px 14px', textAlign: 'right' }}>
        <span style={{ color: C.blue, fontWeight: 700 }}>
          {c.ml_probability != null ? `${(c.ml_probability * 100).toFixed(0)}%` : '—'}
        </span>
      </td>
      <td style={{ padding: '12px 14px', textAlign: 'right' }}>
        <span style={{ color: ev > 0 ? C.green : (ev < 0 ? C.red : C.muted), fontWeight: 700 }}>
          {ev != null ? `${ev >= 0 ? '+' : ''}${ev.toFixed(1)}%` : '—'}
        </span>
      </td>
      <td style={{ padding: '12px 14px', textAlign: 'right' }}>
        <span style={{ color: kelly > 0 ? C.accent : C.muted, fontWeight: 700 }}>
          {kelly != null ? `${kelly.toFixed(1)}%` : '—'}
        </span>
      </td>
      <td style={{ padding: '12px 14px', textAlign: 'center' }}>
        <div style={{ display: 'flex', gap: 4, justifyContent: 'center', flexWrap: 'wrap' }}>
          <Badge label={`${fmt.score(score)}`} color={score >= 70 ? 'HIGH' : score >= 50 ? 'MEDIUM' : 'LOW'} />
          {steam && <Badge label="🔥 STEAM" color="STEAM" />}
        </div>
      </td>
      <td style={{ padding: '12px 14px' }}>
        <Badge label={band.replace('_SIMULATION', '').replace('_', ' ')} color={bandColor} />
      </td>
    </tr>
  );
}

function EquityCurve({ history }) {
  if (!history || history.length < 2) return null;
  const w = 520, h = 120, pad = { l: 48, r: 12, t: 10, b: 28 };
  const vals = history.map(Number);
  const min = Math.min(...vals), max = Math.max(...vals);
  const range = max - min || 1;
  const W = w - pad.l - pad.r;
  const H = h - pad.t - pad.b;
  const pts = vals.map((v, i) => `${pad.l + (i / (vals.length - 1)) * W},${pad.t + (1 - (v - min) / range) * H}`).join(' ');
  const lastVal = vals[vals.length - 1];
  const positive = lastVal >= vals[0];

  return (
    <svg width="100%" viewBox={`0 0 ${w} ${h}`} style={{ display: 'block' }}>
      <defs>
        <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={positive ? C.green : C.red} stopOpacity={0.35} />
          <stop offset="100%" stopColor={positive ? C.green : C.red} stopOpacity={0} />
        </linearGradient>
      </defs>
      {/* Grid lines */}
      {[0, 0.25, 0.5, 0.75, 1].map(t => (
        <line key={t} x1={pad.l} x2={w - pad.r}
              y1={pad.t + t * H} y2={pad.t + t * H}
              stroke={C.border} strokeWidth={0.5} />
      ))}
      {/* Area fill */}
      <polygon
        points={`${pad.l},${pad.t + H} ${pts} ${pad.l + W},${pad.t + H}`}
        fill="url(#equityGrad)" />
      {/* Line */}
      <polyline points={pts} fill="none"
                stroke={positive ? C.green : C.red} strokeWidth={2}
                strokeLinejoin="round" strokeLinecap="round" />
      {/* Y labels */}
      {[min, max].map((v, i) => (
        <text key={i} x={pad.l - 4} y={i === 0 ? pad.t + H : pad.t + 8}
              textAnchor="end" fontSize={9} fill={C.muted}>
          {v.toFixed(0)}
        </text>
      ))}
    </svg>
  );
}

function Section({ title, children, action }) {
  return (
    <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 14,
                  overflow: 'hidden', marginBottom: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    padding: '14px 20px', borderBottom: `1px solid ${C.border}` }}>
        <span style={{ color: C.text, fontWeight: 700, fontSize: 14 }}>{title}</span>
        {action}
      </div>
      {children}
    </div>
  );
}

// ─── Main Dashboard ───────────────────────────────────────────────────────────
export default function Dashboard() {
  const [de, setDe]       = useState(null);
  const [candidates, setCandidates] = useState([]);
  const [paper, setPaper] = useState(null);
  const [auto, setAuto]   = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr]     = useState('');
  const [lastRefresh, setLastRefresh] = useState(null);
  const [filter, setFilter] = useState('ALL');

  const load = useCallback(async () => {
    setLoading(true); setErr('');
    try {
      const [deRes, candRes, paperRes, autoRes] = await Promise.allSettled([
        getDecisionSummary(), getCandidates(), getPaperSummary(), getAutomationStatus(),
      ]);
      if (deRes.status === 'fulfilled')    setDe(deRes.value);
      if (candRes.status === 'fulfilled')  setCandidates(Array.isArray(candRes.value) ? candRes.value : candRes.value?.candidates || []);
      if (paperRes.status === 'fulfilled') setPaper(paperRes.value);
      if (autoRes.status === 'fulfilled')  setAuto(autoRes.value);
      setLastRefresh(new Date().toLocaleTimeString('pt-BR'));
    } catch (e) {
      setErr(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  // Auto-refresh a cada 5 minutos
  useEffect(() => {
    const id = setInterval(load, 5 * 60 * 1000);
    return () => clearInterval(id);
  }, [load]);

  // Candidatos filtrados
  const filtered = candidates.filter(c => {
    if (filter === 'HIGH') return (c.confidence_band || '').includes('HIGH_CONFIDENCE');
    if (filter === 'STEAM') return c.steam_detected;
    if (filter === 'VALUE') return (c.true_ev || 0) > 0.02;
    return true;
  }).sort((a, b) => (b.kelly_stake_pct || 0) - (a.kelly_stake_pct || 0));

  if (loading && !de) return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center',
                  height: '60vh', color: C.muted, gap: 12, fontSize: 14 }}>
      <div style={{ width: 20, height: 20, border: `2px solid ${C.accent}`,
                    borderTopColor: 'transparent', borderRadius: '50%',
                    animation: 'spin 0.8s linear infinite' }} />
      Carregando dashboard...
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );

  const bankroll = paper?.current_bankroll ?? de?.bankroll ?? 1000;
  const initialBankroll = 1000;
  const roi = paper?.roi ?? 0;
  const clv = de?.clv_last_30d_pct ?? 0;
  const drawdown = de?.current_drawdown_pct ?? 0;
  const beating = de?.beating_market ?? false;
  const highConf = de?.high_confidence ?? 0;
  const actionReq = de?.action_required ?? 0;
  const pipelineStatus = auto?.overall_status || auto?.status || '—';
  const lastRun = auto?.last_run_at ? new Date(auto.last_run_at).toLocaleString('pt-BR') : '—';

  // Equity curve histórica (simulada a partir dos dados disponíveis)
  const equityCurveData = paper?.equity_curve || [];

  return (
    <div style={{ background: C.bg, minHeight: '100vh', padding: '24px',
                  fontFamily: "'Inter', -apple-system, sans-serif", color: C.text }}>

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 22, fontWeight: 800, color: C.text }}>
            MatchFlow <span style={{ color: C.accent }}>Analytics</span>
          </h1>
          <p style={{ margin: '4px 0 0', color: C.muted, fontSize: 12 }}>
            v7.0 · Modo: {de?.mode?.replace('_', ' ') || '—'} · Atualizado: {lastRefresh || '—'}
          </p>
        </div>
        <button onClick={load}
          style={{ background: C.accent, color: '#fff', border: 'none', borderRadius: 8,
                   padding: '8px 16px', cursor: 'pointer', fontSize: 13, fontWeight: 600 }}>
          ↻ Atualizar
        </button>
      </div>

      {err && (
        <div style={{ background: `${C.red}22`, border: `1px solid ${C.red}44`, borderRadius: 10,
                      padding: '12px 16px', marginBottom: 20, color: C.red, fontSize: 13 }}>
          ⚠ {err}
        </div>
      )}

      {/* KPIs Row 1: Banca */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))',
                    gap: 14, marginBottom: 20 }}>
        <KpiCard label="Banca Atual" value={fmt.brl(bankroll)} icon="💰"
                 sub={`Inicial: ${fmt.brl(initialBankroll)}`}
                 color={bankroll >= initialBankroll ? C.green : C.red} />
        <KpiCard label="ROI Acumulado" value={`${roi >= 0 ? '+' : ''}${(roi * 100).toFixed(2)}%`}
                 icon="📈" color={roi >= 0 ? C.green : C.red}
                 sub={`${paper?.total_trades || 0} trades liquidados`} />
        <KpiCard label="CLV 30 dias" value={`${clv >= 0 ? '+' : ''}${clv.toFixed(1)}%`}
                 icon="🎯" color={clv >= 2 ? C.green : (clv >= 0 ? C.orange : C.red)}
                 sub={beating ? '✓ Batendo o mercado' : 'Coletando dados…'} />
        <KpiCard label="Drawdown Atual" value={`${drawdown.toFixed(1)}%`}
                 icon="📉" color={drawdown < 10 ? C.green : (drawdown < 20 ? C.orange : C.red)}
                 sub={drawdown >= 20 ? '⚠ Modo sobrevivência ativo' : 'Dentro do limite'} />
      </div>

      {/* KPIs Row 2: Pipeline */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))',
                    gap: 14, marginBottom: 24 }}>
        <KpiCard label="Candidatos Hoje" value={de?.total_candidates ?? '—'} icon="📊"
                 sub={`${highConf} HIGH CONFIDENCE`} color={highConf > 0 ? C.green : C.muted} />
        <KpiCard label="Action Required" value={actionReq} icon="🔔"
                 color={actionReq > 0 ? C.orange : C.muted}
                 sub={actionReq > 0 ? 'Confirmação manual necessária' : 'Nenhuma ação pendente'} />
        <KpiCard label="Status Pipeline" value={pipelineStatus} icon="⚙"
                 color={pipelineStatus === 'SUCCESS' ? C.green : C.orange}
                 sub={`Última execução: ${lastRun}`} />
        <KpiCard label="Apostas Pendentes" value={paper?.pending_signals ?? '—'} icon="⏳"
                 sub={`Win rate: ${fmt.pct(paper?.win_rate)}`} color={C.muted} />
      </div>

      {/* Equity Curve */}
      {equityCurveData.length > 1 && (
        <Section title="📈 Curva de Banca">
          <div style={{ padding: '16px 20px' }}>
            <EquityCurve history={equityCurveData} />
          </div>
        </Section>
      )}

      {/* Candidatos */}
      <Section
        title={`🎯 Candidatos do Dia (${filtered.length})`}
        action={
          <div style={{ display: 'flex', gap: 6 }}>
            {['ALL', 'HIGH', 'VALUE', 'STEAM'].map(f => (
              <button key={f} onClick={() => setFilter(f)}
                style={{ background: filter === f ? C.accent : C.surface,
                         color: filter === f ? '#fff' : C.muted,
                         border: `1px solid ${filter === f ? C.accent : C.border}`,
                         borderRadius: 6, padding: '4px 10px', cursor: 'pointer', fontSize: 11,
                         fontWeight: 700 }}>
                {f}
              </button>
            ))}
          </div>
        }>
        {filtered.length === 0 ? (
          <div style={{ padding: '32px 20px', textAlign: 'center', color: C.muted, fontSize: 13 }}>
            {candidates.length === 0
              ? 'Nenhum candidato disponível. Execute o pipeline para gerar análises.'
              : 'Nenhum candidato com o filtro selecionado.'}
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ background: C.surface }}>
                  {['Data', 'Jogo', 'Mercado', 'Prob ML', 'True EV', 'Kelly %', 'Score', 'Band'].map(h => (
                    <th key={h} style={{ padding: '10px 14px', textAlign: h === 'Data' || h === 'Jogo' || h === 'Mercado' ? 'left' : 'right',
                                         color: C.muted, fontSize: 11, fontWeight: 700, textTransform: 'uppercase',
                                         letterSpacing: '0.04em', whiteSpace: 'nowrap',
                                         ...(h === 'Score' || h === 'Band' ? { textAlign: 'center' } : {}) }}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.slice(0, 20).map((c, i) => <CandidateRow key={c.match_id || i} c={c} i={i} />)}
              </tbody>
            </table>
            {filtered.length > 20 && (
              <div style={{ padding: '10px 20px', color: C.muted, fontSize: 12, textAlign: 'center' }}>
                Mostrando 20 de {filtered.length} candidatos
              </div>
            )}
          </div>
        )}
      </Section>

      {/* Performance Summary */}
      {paper && (
        <Section title="📊 Performance do Paper Trading">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
                        gap: 16, padding: '16px 20px' }}>
            {[
              ['Total Trades', paper.total_trades ?? '—'],
              ['Vitórias', paper.total_wins ?? '—'],
              ['Derrotas', paper.total_losses ?? '—'],
              ['Win Rate', fmt.pct(paper.win_rate)],
              ['P&L Total', fmt.brl(paper.total_profit)],
              ['Banca Final', fmt.brl(paper.current_bankroll)],
            ].map(([label, value]) => (
              <div key={label} style={{ textAlign: 'center' }}>
                <div style={{ color: C.muted, fontSize: 11, marginBottom: 4 }}>{label}</div>
                <div style={{ color: C.text, fontWeight: 700, fontSize: 16 }}>{value}</div>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Footer */}
      <div style={{ textAlign: 'center', color: C.muted, fontSize: 11, marginTop: 16, paddingBottom: 8 }}>
        MatchFlow Analytics v7.0 · Este sistema não executa apostas automáticas.
        Confirmação manual obrigatória para qualquer operação.
      </div>
    </div>
  );
}
