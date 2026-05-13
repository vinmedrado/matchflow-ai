import { useEffect, useMemo, useState } from 'react';
import { api } from '../api/client.js';
import { useI18n } from '../i18n.js';

function Table({ children }) { return <div className="table-wrap premium-table"><table>{children}</table></div>; }

export default function Competitions() {
  const { t } = useI18n();
  const [overview, setOverview] = useState(null);
  const [detail, setDetail] = useState(null);
  const [league, setLeague] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  async function loadOverview() {
    setLoading(true); setError('');
    try {
      const res = await api.competitionsOverview();
      const data = res.data || res;
      setOverview(data);
      const first = data.leagues?.[0]?.league || '';
      setLeague((old) => old || first);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }

  useEffect(() => { loadOverview(); }, []);
  useEffect(() => {
    if (!league) return;
    api.competitionDetail(league).then((res) => setDetail(res.data || res)).catch((e) => setError(e.message));
  }, [league]);

  const leagues = overview?.leagues || [];
  const selected = useMemo(() => leagues.find((x) => x.league === league), [leagues, league]);

  if (loading) return <div className="card">{t('loading')}</div>;

  return (
    <div className="page">
      <div className="page-header premium-header">
        <div><div className="brand-pill">Competitions Intelligence</div><h1>{t('competitionsTitle')}</h1><p>{t('competitionsDesc')}</p></div>
        <button className="btn btn-secondary" onClick={loadOverview}>{t('refresh')}</button>
      </div>
      {error && <div className="alert alert-error">{error}</div>}

      <div className="grid-2 mb20">
        <div className="card">
          <div className="card-header"><div className="card-title">{t('selectLeague')}</div></div>
          <select className="input" value={league} onChange={(e) => setLeague(e.target.value)}>
            {leagues.map((item) => <option key={item.league} value={item.league}>{item.league}</option>)}
          </select>
          <div className="premium-grid-3 mt16">
            <div className="mini-stat"><span>Times</span><strong>{selected?.teams ?? 0}</strong></div>
            <div className="mini-stat"><span>Jogos</span><strong>{selected?.matches ?? 0}</strong></div>
            <div className="mini-stat"><span>Período</span><strong>{selected?.date_min || '—'} → {selected?.date_max || '—'}</strong></div>
          </div>
        </div>
        <div className="card">
          <div className="card-header"><div className="card-title">Saúde da base</div></div>
          <p className="text-muted">Esta tela lê a base local atual. Quando o Data Engine rodar, a tabela e os jogos passam a refletir os arquivos processados pelo bridge.</p>
          <div className="workflow-strip mt16"><span>FlashScore</span><span>Bridge</span><span>Features</span><span>Backtest/ML</span></div>
        </div>
      </div>

      <section className="card mb20">
        <div className="card-header"><div className="card-title">{t('standings')}</div></div>
        {(detail?.standings || []).length === 0 ? <p className="text-muted">{t('empty')}</p> : (
          <Table><thead><tr><th>#</th><th>Time</th><th className="right">J</th><th className="right">Pontos</th><th className="right">V</th><th className="right">E</th><th className="right">D</th><th className="right">GM</th><th className="right">GS</th><th className="right">Saldo</th></tr></thead>
          <tbody>{detail.standings.map((r, i) => <tr key={r.team_key || r.team_name}><td>{i+1}</td><td><b>{r.team_name}</b></td><td className="right">{r.matches}</td><td className="right"><b>{r.points}</b></td><td className="right">{r.wins}</td><td className="right">{r.draws}</td><td className="right">{r.losses}</td><td className="right">{r.goals_for}</td><td className="right">{r.goals_against}</td><td className="right">{r.goal_diff}</td></tr>)}</tbody></Table>
        )}
      </section>

      <section className="card">
        <div className="card-header"><div className="card-title">{t('recentMatches')}</div></div>
        {(detail?.recent_matches || []).length === 0 ? <p className="text-muted">{t('empty')}</p> : (
          <Table><thead><tr><th>Data</th><th>Jogo</th><th className="right">Placar</th><th>Fonte</th></tr></thead><tbody>{detail.recent_matches.map((m) => <tr key={m.event_id || m.match_key}><td>{m.date}</td><td><b>{m.home_team}</b> x <b>{m.away_team}</b></td><td className="right">{m.goals_home_ft ?? '-'} - {m.goals_away_ft ?? '-'}</td><td>{m.source_layer || 'base'}</td></tr>)}</tbody></Table>
        )}
      </section>
    </div>
  );
}
