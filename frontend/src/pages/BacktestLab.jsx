import { useEffect, useState } from 'react';
import { apiRequest } from '../api/client';
import MetricCard from '../components/MetricCard';
import Loading from '../components/Loading';
import ErrorState from '../components/ErrorState';
import EmptyState from '../components/EmptyState';
import StatusBadge from '../components/StatusBadge';

export default function BacktestLab() {
  const [summary, setSummary] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [deepAnalysis, setDeepAnalysis] = useState(null);
  const [refinement, setRefinement] = useState(null);
  const [paper, setPaper] = useState(null);
  const [loading, setLoading] = useState(true);
  const [analysisError, setAnalysisError] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let mounted = true;
    async function loadBacktest() {
      try {
        setLoading(true);
        setError(null);
        setAnalysisError(null);
        const [summaryResponse, analysisResponse, deepResponse, refinementResponse, paperResponse] = await Promise.allSettled([
          apiRequest('/api/backtest/summary'),
          apiRequest('/api/backtest/analysis-summary'),
          apiRequest('/api/backtest/deep-analysis-summary'),
          apiRequest('/api/backtest/refinement-summary'),
          apiRequest('/api/paper-trading/summary'),
        ]);
        if (!mounted) return;
        if (summaryResponse.status === 'fulfilled') setSummary(summaryResponse.value?.data || summaryResponse.value);
        else throw summaryResponse.reason;
        if (analysisResponse.status === 'fulfilled') setAnalysis(analysisResponse.value?.data || analysisResponse.value);
        else setAnalysisError(analysisResponse.reason?.message || 'Análise de performance indisponível.');
        if (deepResponse.status === 'fulfilled') setDeepAnalysis(deepResponse.value?.data || deepResponse.value);
        if (refinementResponse.status === 'fulfilled') setRefinement(refinementResponse.value?.data || refinementResponse.value);
        if (paperResponse.status === 'fulfilled') setPaper(paperResponse.value?.data || paperResponse.value);
      } catch (err) {
        if (mounted) setError(err?.message || 'Não foi possível carregar o resumo de backtest.');
      } finally {
        if (mounted) setLoading(false);
      }
    }
    loadBacktest();
    return () => { mounted = false; };
  }, []);

  if (loading) return <Loading label="Carregando Backtest Lab..." />;
  if (error) return <ErrorState title="Backtest indisponível" message={error} />;

  const strategies = summary?.strategies || [];
  const topMarkets = analysis?.top_markets || [];
  const topStrategies = analysis?.top_strategies || [];
  const bestLeague = analysis?.best_league;
  const worstDrawdown = analysis?.worst_drawdown;
  const topConsistency = deepAnalysis?.consistency_score_top_10 || [];
  const riskFlags = deepAnalysis?.risk_flags_count || {};
  const bestOddsRange = deepAnalysis?.best_odds_range;
  const bestLeagueMarkets = deepAnalysis?.best_league_market_combinations || [];
  const refinedCandidates = refinement?.refined_candidates_top_10 || [];
  const refinementMarkets = refinement?.markets || { KEEP: [], WATCH: [], DISCARD: [] };
  const favorableOdds = refinement?.favorable_odds_ranges || [];
  const highRiskStrategies = refinement?.high_risk_strategies || [];
  const latestSignals = paper?.latest_signals || [];

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Backtest Lab</h1>
          <p className="subtitle">Backtest financeiro, análise profunda, refinamento estratégico e paper trading local/simulado.</p>
        </div>
        <StatusBadge status={summary?.file_exists ? 'online' : 'offline'} label={summary?.file_exists ? 'Resultados disponíveis' : 'Sem resultado'} />
      </div>

      <div className="metrics-grid">
        <MetricCard label="Estratégias" value={summary?.total_strategies ?? 0} />
        <MetricCard label="Total Trades" value={summary?.total_trades ?? 0} />
        <MetricCard label="Lucro Total" value={Number(summary?.total_profit || 0).toFixed(2)} />
        <MetricCard label="ROI Geral" value={`${(Number(analysis?.overall_roi ?? summary?.roi ?? 0) * 100).toFixed(2)}%`} />
      </div>

      {analysisError && <ErrorState title="Análise avançada indisponível" message={analysisError} />}

      <div className="section-header">
        <div>
          <h2>Paper Trading</h2>
          <p className="subtitle">Simulação local controlada. Não executa apostas, não integra casas e não altera o histórico.</p>
        </div>
        <StatusBadge status={paper?.file_exists ? 'online' : 'offline'} label={paper?.paper_only ? 'paper_only=true' : 'Paper indisponível'} />
      </div>

      <div className="metrics-grid">
        <MetricCard label="Banca Fictícia" value={Number(paper?.current_bankroll ?? 100).toFixed(2)} />
        <MetricCard label="Sinais" value={paper?.total_signals ?? 0} />
        <MetricCard label="Pendentes" value={paper?.pending_signals ?? 0} />
        <MetricCard label="ROI Paper" value={`${(Number(paper?.roi ?? paper?.ROI ?? 0) * 100).toFixed(2)}%`} />
      </div>

      <div className="table-card">
        <h2>Últimos sinais paper</h2>
        {latestSignals.length === 0 ? (
          <EmptyState title="Nenhum sinal paper" message="Execute python run_paper_trading_pipeline.py. Se não houver KEEP elegível, o sistema mantém zero sinais por segurança." />
        ) : (
          <table>
            <thead>
              <tr><th>Data</th><th>Estratégia</th><th>Mercado</th><th>Time</th><th>Odd</th><th>Status</th></tr>
            </thead>
            <tbody>
              {latestSignals.map((item) => (
                <tr key={item.signal_id}>
                  <td>{String(item.date || '').slice(0, 10)}</td>
                  <td>{item.strategy}</td>
                  <td>{item.market}</td>
                  <td>{item.team_name || item.team_key}</td>
                  <td>{item.odd === null || item.odd === undefined ? 'N/A' : Number(item.odd).toFixed(2)}</td>
                  <td>{item.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {refinement?.refinement_available && (
        <>
          <div className="section-header">
            <div>
              <h2>Strategy Refinement</h2>
              <p className="subtitle">Classificação KEEP/WATCH/DISCARD para reduzir ruído, falso edge e dependência excessiva.</p>
            </div>
            <StatusBadge status="online" label="Refinement disponível" />
          </div>
          <div className="metrics-grid">
            <MetricCard label="KEEP" value={(refinementMarkets.KEEP || []).length} />
            <MetricCard label="WATCH" value={(refinementMarkets.WATCH || []).length} />
            <MetricCard label="DISCARD" value={(refinementMarkets.DISCARD || []).length} />
            <MetricCard label="Rejeitadas" value={refinement?.rejected_count ?? 0} />
          </div>
          <div className="table-card">
            <h2>Estratégias KEEP</h2>
            {refinedCandidates.length === 0 ? <EmptyState title="Nenhuma estratégia aprovada" message="Nenhuma estratégia passou por amostra mínima, ROI, PF, drawdown, estabilidade e flags críticas." /> : (
              <table><thead><tr><th>Estratégia</th><th>Mercado</th><th>Trades</th><th>ROI</th><th>PF</th><th>Drawdown</th><th>Score</th></tr></thead><tbody>
                {refinedCandidates.map((item) => <tr key={`${item.strategy}-${item.market}`}><td>{item.strategy}</td><td>{item.market}</td><td>{item.total_trades}</td><td>{(Number(item.roi || 0) * 100).toFixed(2)}%</td><td>{Number(item.profit_factor || 0).toFixed(2)}</td><td>{Number(item.max_drawdown || 0).toFixed(2)}</td><td>{Number(item.consistency_score || 0).toFixed(1)}</td></tr>)}
              </tbody></table>
            )}
          </div>
          <div className="table-card"><h2>Faixas de Odds Favoráveis</h2>{favorableOdds.length === 0 ? <EmptyState title="Sem faixa favorável" message="Nenhuma faixa passou nos critérios de ROI/PF/amostra." /> : <table><thead><tr><th>Mercado</th><th>Faixa</th><th>Trades</th><th>ROI</th><th>PF</th></tr></thead><tbody>{favorableOdds.map((item)=><tr key={`${item.market}-${item.odds_range}`}><td>{item.market}</td><td>{item.odds_range}</td><td>{item.total_trades}</td><td>{(Number(item.roi || 0)*100).toFixed(2)}%</td><td>{Number(item.profit_factor || 0).toFixed(2)}</td></tr>)}</tbody></table>}</div>
          <div className="table-card"><h2>Principais Riscos</h2>{highRiskStrategies.length === 0 ? <EmptyState title="Sem risco alto consolidado" message="Nenhuma estratégia foi classificada com overfitting_risk HIGH." /> : <table><thead><tr><th>Estratégia</th><th>Mercado</th><th>Flags</th><th>Recomendação</th></tr></thead><tbody>{highRiskStrategies.map((item)=><tr key={`${item.strategy}-${item.market}`}><td>{item.strategy}</td><td>{item.market}</td><td>{item.risk_flags}</td><td>{item.final_recommendation}</td></tr>)}</tbody></table>}</div>
        </>
      )}

      {deepAnalysis?.deep_analysis_available && (
        <>
          <div className="section-header"><div><h2>Deep Analysis</h2><p className="subtitle">Amostra, estabilidade temporal, odds range, matriz liga x mercado e risco de overfitting.</p></div><StatusBadge status="online" label="Deep disponível" /></div>
          <div className="metrics-grid"><MetricCard label="Top Consistency" value={topConsistency[0]?.strategy || 'N/A'} /><MetricCard label="Melhor Odds Range" value={bestOddsRange?.odds_range || 'N/A'} /><MetricCard label="Liga x Mercado" value={bestLeagueMarkets[0]?.league || 'N/A'} /><MetricCard label="Flags" value={Object.values(riskFlags).reduce((a, b) => a + Number(b || 0), 0)} /></div>
          {deepAnalysis?.insights && <div className="table-card"><h2>Deep Insights</h2><pre className="assistant-answer">{deepAnalysis.insights}</pre></div>}
        </>
      )}

      {analysis?.analysis_available && (
        <>
          <div className="table-card"><h2>Ranking de Mercados</h2>{topMarkets.length === 0 ? <EmptyState title="Sem ranking de mercados" message="Execute python run_backtest_analysis_pipeline.py para gerar a análise." /> : <table><thead><tr><th>Mercado</th><th>Trades</th><th>Winrate</th><th>ROI</th><th>PF</th><th>Drawdown</th><th>Odds Médias</th></tr></thead><tbody>{topMarkets.map((item)=><tr key={item.market}><td>{item.market}</td><td>{item.total_trades}</td><td>{Math.round((item.win_rate || 0)*100)}%</td><td>{(Number(item.roi || 0)*100).toFixed(2)}%</td><td>{Number(item.profit_factor || 0).toFixed(2)}</td><td>{Number(item.max_drawdown || 0).toFixed(2)}</td><td>{Number(item.avg_odds || 0).toFixed(2)}</td></tr>)}</tbody></table>}</div>
          <div className="table-card"><h2>Ranking de Estratégias</h2>{topStrategies.length === 0 ? <EmptyState title="Sem ranking de estratégias" message="Ainda não há ranking calculado." /> : <table><thead><tr><th>Rank</th><th>Estratégia</th><th>Mercado</th><th>Trades</th><th>ROI</th><th>PF</th><th>Score</th></tr></thead><tbody>{topStrategies.map((item)=><tr key={`${item.rank}-${item.strategy}-${item.market}`}><td>{item.rank}</td><td>{item.strategy}</td><td>{item.market}</td><td>{item.total_trades}</td><td>{(Number(item.roi || 0)*100).toFixed(2)}%</td><td>{Number(item.profit_factor || 0).toFixed(2)}</td><td>{Number(item.consistency_score || 0).toFixed(2)}</td></tr>)}</tbody></table>}</div>
          <div className="metrics-grid"><MetricCard label="Melhor Liga" value={bestLeague?.league || 'N/A'} /><MetricCard label="ROI Melhor Liga" value={`${(Number(bestLeague?.roi || 0)*100).toFixed(2)}%`} /><MetricCard label="Pior Drawdown" value={Number(worstDrawdown?.max_drawdown || 0).toFixed(2)} /><MetricCard label="Seq. Negativa" value={worstDrawdown?.max_losing_streak ?? 0} /></div>
          {analysis?.insights && <div className="table-card"><h2>Insights automáticos</h2><pre className="assistant-answer">{analysis.insights}</pre></div>}
        </>
      )}

      {strategies.length === 0 ? <EmptyState title="Nenhum backtest financeiro encontrado" message="Execute python run_backtest_pipeline.py para gerar resultados com odds reais." /> : (
        <div className="table-card"><h2>Resumo Financeiro por Estratégia</h2><table><thead><tr><th>Estratégia</th><th>Mercado</th><th>Trades</th><th>Winrate</th><th>ROI</th><th>Lucro</th><th>PF</th><th>Drawdown</th></tr></thead><tbody>{strategies.map((item)=><tr key={`${item.market}-${item.strategy}`}><td>{item.strategy}</td><td>{item.market}</td><td>{item.total_trades}</td><td>{Math.round((item.win_rate || 0)*100)}%</td><td>{(Number(item.roi || 0)*100).toFixed(2)}%</td><td>{Number(item.total_profit || 0).toFixed(2)}</td><td>{item.profit_factor === null || item.profit_factor === undefined ? 'N/A' : Number(item.profit_factor).toFixed(2)}</td><td>{Number(item.max_drawdown || 0).toFixed(2)}</td></tr>)}</tbody></table></div>
      )}
    </div>
  );
}
