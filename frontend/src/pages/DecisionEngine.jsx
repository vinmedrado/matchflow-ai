import { useEffect, useState } from 'react';
import { apiRequest } from '../api/client';

const C = {
  bg:'#0f1117',surface:'#1a1d2e',card:'#232640',border:'#2e3356',
  text:'#e2e8f0',muted:'#8892b0',accent:'#7c6aff',
  green:'#22c55e',red:'#ef4444',orange:'#f59e0b',blue:'#3b82f6',steam:'#ff6b35',
};

function Badge({v,color}){
  const map={HIGH:C.green,MED:C.orange,LOW:C.red,STEAM:C.steam,INFO:C.blue};
  const c=map[color]||C.muted;
  return <span style={{background:`${c}22`,color:c,border:`1px solid ${c}55`,borderRadius:6,
    padding:'2px 8px',fontSize:11,fontWeight:700,whiteSpace:'nowrap'}}>{v}</span>;
}

function KPI({label,value,sub,color}){
  return <div style={{background:C.card,border:`1px solid ${C.border}`,borderRadius:12,padding:'16px 20px'}}>
    <div style={{color:C.muted,fontSize:11,textTransform:'uppercase',letterSpacing:'0.05em',marginBottom:4}}>{label}</div>
    <div style={{color:color||C.text,fontSize:22,fontWeight:700}}>{value}</div>
    {sub&&<div style={{color:C.muted,fontSize:11,marginTop:2}}>{sub}</div>}
  </div>;
}

function Btn({children,onClick,loading,variant='primary'}){
  const bg=variant==='primary'?C.accent:C.surface;
  return <button onClick={onClick} disabled={loading}
    style={{background:bg,color:'#fff',border:`1px solid ${variant==='primary'?C.accent:C.border}`,
    borderRadius:8,padding:'8px 16px',cursor:loading?'default':'pointer',fontSize:13,fontWeight:600,opacity:loading?.7:1}}>
    {loading?'Executando…':children}
  </button>;
}

const marketIcons={goals:'⚽',corners:'🚩',btts:'🎯',shots:'🥅'};

export default function DecisionEngine(){
  const [summary,setSummary]=useState(null);
  const [candidates,setCandidates]=useState([]);
  const [loading,setLoading]=useState(true);
  const [running,setRunning]=useState(false);
  const [error,setError]=useState('');
  const [filter,setFilter]=useState('ALL');
  const [showExplain,setShowExplain]=useState(null);

  async function load(){
    setLoading(true);setError('');
    try{
      const [s,c]=await Promise.all([
        apiRequest('/api/decision-engine/summary'),
        apiRequest('/api/decision-engine/candidates'),
      ]);
      setSummary(s.data||s);
      const items=(c.data||c)?.candidates||(c.data||c)?.items||[];
      setCandidates(Array.isArray(items)?items:[]);
    }catch(e){setError(e.message);}
    finally{setLoading(false);}
  }

  async function runEngine(){
    setRunning(true);setError('');
    try{await apiRequest('/api/decision-engine/run',{method:'POST'});await load();}
    catch(e){setError(e.message);}finally{setRunning(false);}
  }

  useEffect(()=>{load();},[]);

  const filtered=candidates.filter(c=>{
    if(filter==='HIGH') return (c.confidence_band||'').includes('HIGH_CONFIDENCE');
    if(filter==='VALUE') return parseFloat(c.true_ev||0)>0.02;
    if(filter==='STEAM') return c.steam_detected==='True'||c.steam_detected===true;
    if(filter==='ACTION') return c.action_required==='True'||c.action_required===true;
    return true;
  }).sort((a,b)=>parseFloat(b.kelly_stake_pct||0)-parseFloat(a.kelly_stake_pct||0));

  const clv=summary?.clv_metrics||{};
  const perf=summary?.performance||{};
  const mc=summary?.monte_carlo||{};

  return(
    <div style={{background:C.bg,minHeight:'100vh',padding:24,fontFamily:"'Inter',sans-serif",color:C.text}}>

      {/* Header */}
      <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:24}}>
        <div>
          <h1 style={{margin:0,fontSize:20,fontWeight:800}}>
            🎯 Decision Engine <span style={{color:C.accent,fontSize:14,fontWeight:400}}>v7.0</span>
          </h1>
          <p style={{margin:'4px 0 0',color:C.muted,fontSize:12}}>
            True EV · CLV · Kelly Fracionado · Sharp Money · Significância Estatística
          </p>
        </div>
        <div style={{display:'flex',gap:8}}>
          <Btn onClick={load} variant='secondary' loading={loading}>↻ Refresh</Btn>
          <Btn onClick={runEngine} loading={running}>▶ Executar Engine</Btn>
        </div>
      </div>

      {error&&<div style={{background:`${C.red}22`,border:`1px solid ${C.red}55`,borderRadius:10,
        padding:'10px 16px',marginBottom:20,color:C.red,fontSize:13}}>⚠ {error}</div>}

      {/* KPIs principais */}
      <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(170px,1fr))',gap:14,marginBottom:20}}>
        <KPI label="Candidatos" value={summary?.total_candidates??'—'}
          sub={`${summary?.high_confidence??0} HIGH CONFIDENCE`}
          color={summary?.high_confidence>0?C.green:C.muted}/>
        <KPI label="CLV 30 dias" value={`${(clv.mean_clv_last_30d_pct||0)>=0?'+':''}${(clv.mean_clv_last_30d_pct||0).toFixed(1)}%`}
          sub={clv.is_beating_market?'✓ Batendo mercado':'Aguardando dados…'}
          color={clv.mean_clv_last_30d_pct>2?C.green:clv.mean_clv_last_30d_pct>=0?C.orange:C.red}/>
        <KPI label="True EV médio" value={summary?.mean_true_ev!=null?`${(summary.mean_true_ev*100).toFixed(1)}%`:'—'}
          sub="Após remoção de vig" color={summary?.mean_true_ev>0?C.green:C.red}/>
        <KPI label="Kelly médio" value={summary?.mean_kelly_pct!=null?`${(summary.mean_kelly_pct*100).toFixed(1)}%`:'—'}
          sub="Fração da banca" color={C.accent}/>
        <KPI label="Score médio" value={summary?.average_score??'—'} sub="0–100" color={C.blue}/>
        <KPI label="Action Required" value={summary?.action_required??0}
          color={summary?.action_required>0?C.orange:C.muted}
          sub={summary?.action_required>0?'Confirmação manual necessária':'Nenhuma ação pendente'}/>
      </div>

      {/* CLV + Perf + Monte Carlo */}
      {(clv.total_tracked>0||perf.total_roi_pct!=null)&&(
        <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(280px,1fr))',gap:14,marginBottom:20}}>
          {clv.total_tracked>0&&<div style={{background:C.card,border:`1px solid ${C.border}`,borderRadius:12,padding:'16px 20px'}}>
            <div style={{color:C.muted,fontSize:11,fontWeight:700,textTransform:'uppercase',marginBottom:10}}>📊 CLV Analytics</div>
            {[
              ['Todas as apostas',`${(clv.mean_clv_all_time_pct||0).toFixed(2)}%`],
              ['Últimos 30 dias',`${(clv.mean_clv_last_30d_pct||0).toFixed(2)}%`],
              ['CLV positivo',`${((clv.positive_clv_rate||0)*100).toFixed(0)}% das apostas`],
              ['Total rastreadas',`${clv.total_tracked} apostas`],
            ].map(([k,v])=><div key={k} style={{display:'flex',justifyContent:'space-between',
              marginBottom:6,fontSize:13}}>
              <span style={{color:C.muted}}>{k}</span>
              <span style={{fontWeight:600,color:parseFloat(v)>0?C.green:C.text}}>{v}</span>
            </div>)}
            {clv.edge_deteriorating&&<div style={{color:C.red,fontSize:11,marginTop:8}}>⚠ Edge deteriorando — reduzir stakes</div>}
          </div>}

          {perf.total_roi_pct!=null&&<div style={{background:C.card,border:`1px solid ${C.border}`,borderRadius:12,padding:'16px 20px'}}>
            <div style={{color:C.muted,fontSize:11,fontWeight:700,textTransform:'uppercase',marginBottom:10}}>🏆 Performance Attribution</div>
            {[
              ['ROI total',`${(perf.total_roi_pct||0).toFixed(2)}%`],
              ['ROI por habilidade',perf.skill_roi_pct!=null?`${perf.skill_roi_pct.toFixed(2)}%`:'Aguardando CLV'],
              ['Win rate',`${((perf.win_rate||0)*100).toFixed(1)}%`],
              ['Recomendação',perf.recommendation||'—'],
            ].map(([k,v])=><div key={k} style={{display:'flex',justifyContent:'space-between',
              marginBottom:6,fontSize:13}}>
              <span style={{color:C.muted}}>{k}</span>
              <span style={{fontWeight:600,color:C.text}}>{v}</span>
            </div>)}
          </div>}

          {mc.median_6m&&<div style={{background:C.card,border:`1px solid ${C.border}`,borderRadius:12,padding:'16px 20px'}}>
            <div style={{color:C.muted,fontSize:11,fontWeight:700,textTransform:'uppercase',marginBottom:10}}>🎲 Monte Carlo 6 meses</div>
            {[
              ['Banca mediana',`R$ ${(mc.median_6m||0).toFixed(0)}`],
              ['Prob. de dobrar',`${mc.prob_doubling_pct||0}%`],
              ['Prob. de ruína',`${mc.ruin_prob_pct||0}%`],
            ].map(([k,v])=><div key={k} style={{display:'flex',justifyContent:'space-between',
              marginBottom:6,fontSize:13}}>
              <span style={{color:C.muted}}>{k}</span>
              <span style={{fontWeight:600,color:C.text}}>{v}</span>
            </div>)}
          </div>}
        </div>
      )}

      {/* Filtros + Tabela */}
      <div style={{background:C.card,border:`1px solid ${C.border}`,borderRadius:14,overflow:'hidden'}}>
        <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',
          padding:'14px 20px',borderBottom:`1px solid ${C.border}`}}>
          <span style={{fontWeight:700,fontSize:14}}>Candidatos ({filtered.length})</span>
          <div style={{display:'flex',gap:6}}>
            {['ALL','HIGH','VALUE','STEAM','ACTION'].map(f=>(
              <button key={f} onClick={()=>setFilter(f)}
                style={{background:filter===f?C.accent:C.surface,color:filter===f?'#fff':C.muted,
                border:`1px solid ${filter===f?C.accent:C.border}`,borderRadius:6,
                padding:'3px 10px',cursor:'pointer',fontSize:11,fontWeight:700}}>
                {f}
              </button>
            ))}
          </div>
        </div>

        {loading?(
          <div style={{padding:'40px 20px',textAlign:'center',color:C.muted}}>Carregando…</div>
        ):filtered.length===0?(
          <div style={{padding:'40px 20px',textAlign:'center',color:C.muted,fontSize:13}}>
            {candidates.length===0
              ?'Nenhum candidato. Execute o Test Lab e depois o Decision Engine.'
              :'Nenhum candidato com este filtro.'}
          </div>
        ):(
          <div style={{overflowX:'auto'}}>
            <table style={{width:'100%',borderCollapse:'collapse',fontSize:12}}>
              <thead>
                <tr style={{background:C.surface}}>
                  {['Jogo / Liga','Mercado','Prob ML','True EV','Kelly','Score','Sharp','Band','Ação'].map(h=>(
                    <th key={h} style={{padding:'9px 12px',color:C.muted,fontWeight:700,
                      fontSize:10,textTransform:'uppercase',letterSpacing:'0.04em',
                      textAlign:h==='True EV'||h==='Prob ML'||h==='Kelly'||h==='Score'?'right':'left',
                      whiteSpace:'nowrap'}}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.slice(0,25).map((c,i)=>{
                  const ev=parseFloat(c.true_ev||0)*100;
                  const kelly=parseFloat(c.kelly_stake_pct||0)*100;
                  const score=parseFloat(c.decision_score||0);
                  const steam=c.steam_detected==='True'||c.steam_detected===true;
                  const band=c.confidence_band||'';
                  const bandColor=band.includes('HIGH')?'HIGH':band.includes('MEDIUM')?'MED':'LOW';
                  const action=c.action_required==='True'||c.action_required===true;
                  const icon=marketIcons[(c.market||'').toLowerCase()]||'📊';
                  return(
                    <tr key={i} style={{borderBottom:`1px solid ${C.border}`}}
                      onMouseEnter={e=>e.currentTarget.style.background=`${C.border}44`}
                      onMouseLeave={e=>e.currentTarget.style.background='transparent'}>
                      <td style={{padding:'10px 12px'}}>
                        <div style={{fontWeight:600,color:C.text}}>{c.home_team||'?'} <span style={{color:C.muted}}>x</span> {c.away_team||'?'}</div>
                        <div style={{color:C.muted,fontSize:10}}>{c.league||'?'} · {(c.date||'').slice(0,10)}</div>
                      </td>
                      <td style={{padding:'10px 12px'}}>
                        <div>{icon} {(c.market||'').toUpperCase()}</div>
                        <div style={{color:C.muted,fontSize:10}}>odds {parseFloat(c.odds||0).toFixed(2)}</div>
                      </td>
                      <td style={{padding:'10px 12px',textAlign:'right',color:C.blue,fontWeight:700}}>
                        {c.ml_probability?`${(parseFloat(c.ml_probability)*100).toFixed(0)}%`:'—'}
                      </td>
                      <td style={{padding:'10px 12px',textAlign:'right',fontWeight:700,
                        color:ev>0?C.green:(ev<0?C.red:C.muted)}}>
                        {c.true_ev?`${ev>=0?'+':''}${ev.toFixed(1)}%`:'—'}
                      </td>
                      <td style={{padding:'10px 12px',textAlign:'right',color:kelly>0?C.accent:C.muted,fontWeight:700}}>
                        {c.kelly_stake_pct?`${kelly.toFixed(1)}%`:'—'}
                      </td>
                      <td style={{padding:'10px 12px',textAlign:'right'}}>
                        <Badge v={score.toFixed(0)} color={score>=70?'HIGH':score>=50?'MED':'LOW'}/>
                      </td>
                      <td style={{padding:'10px 12px',textAlign:'center'}}>
                        {steam?<Badge v="🔥 STEAM" color="STEAM"/>:<span style={{color:C.muted}}>—</span>}
                      </td>
                      <td style={{padding:'10px 12px'}}>
                        <Badge v={band.replace('_SIMULATION','').replace(/_/g,' ')} color={bandColor}/>
                      </td>
                      <td style={{padding:'10px 12px',textAlign:'center'}}>
                        {action?(
                          <button onClick={()=>setShowExplain(showExplain===i?null:i)}
                            style={{background:`${C.orange}22`,color:C.orange,border:`1px solid ${C.orange}55`,
                            borderRadius:6,padding:'3px 8px',cursor:'pointer',fontSize:10,fontWeight:700}}>
                            ⚡ Ver
                          </button>
                        ):<span style={{color:C.muted}}>—</span>}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Painel de explicação */}
        {showExplain!==null&&filtered[showExplain]&&(
          <div style={{margin:16,background:C.surface,border:`1px solid ${C.orange}44`,
            borderRadius:10,padding:16}}>
            <div style={{color:C.orange,fontWeight:700,fontSize:13,marginBottom:8}}>
              ⚡ Explicação — {filtered[showExplain].home_team} x {filtered[showExplain].away_team}
            </div>
            <pre style={{color:C.text,fontSize:12,whiteSpace:'pre-wrap',margin:0,lineHeight:1.6}}>
              {filtered[showExplain].explanation_text||filtered[showExplain].why_selected||'Explicação não disponível.'}
            </pre>
            <div style={{marginTop:10}}>
              <div style={{color:C.muted,fontSize:11}}>✅ Pontos fortes: {filtered[showExplain].strengths_list||'—'}</div>
              <div style={{color:C.muted,fontSize:11}}>⚠ Riscos: {filtered[showExplain].risks_list||filtered[showExplain].risk_flags||'—'}</div>
            </div>
          </div>
        )}

        {filtered.length>25&&(
          <div style={{padding:'10px 20px',color:C.muted,fontSize:11,textAlign:'center'}}>
            Mostrando 25 de {filtered.length} candidatos
          </div>
        )}
      </div>

      <div style={{marginTop:12,color:C.muted,fontSize:11,textAlign:'center'}}>
        MatchFlow v7.0 · Este sistema não executa apostas automaticamente · Confirmação manual obrigatória
      </div>
    </div>
  );
}
