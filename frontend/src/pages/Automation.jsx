import { useEffect, useState } from 'react';
import { api } from '../api/client.js';

const C={bg:'#0f1117',surface:'#1a1d2e',card:'#232640',border:'#2e3356',
  text:'#e2e8f0',muted:'#8892b0',accent:'#7c6aff',green:'#22c55e',
  red:'#ef4444',orange:'#f59e0b',blue:'#3b82f6'};

const statusColor=s=>{
  if(!s) return C.muted;
  const u=s.toUpperCase();
  if(u==='SUCCESS'||u==='OK'||u==='ONLINE') return C.green;
  if(u==='FAILED'||u==='ERROR') return C.red;
  if(u==='PARTIAL'||u==='WARNING') return C.orange;
  return C.muted;
};

function StatusDot({status}){
  const c=statusColor(status);
  return <span style={{display:'inline-block',width:8,height:8,borderRadius:'50%',
    background:c,marginRight:6,boxShadow:`0 0 6px ${c}`}}/>;
}

function IntegrationCard({label,configured,detail,icon}){
  return(
    <div style={{background:C.surface,border:`1px solid ${configured?C.green+'44':C.border}`,
      borderRadius:10,padding:'12px 16px',display:'flex',alignItems:'center',gap:12}}>
      <span style={{fontSize:20}}>{icon}</span>
      <div style={{flex:1}}>
        <div style={{fontWeight:600,fontSize:13,color:C.text}}>{label}</div>
        <div style={{fontSize:11,color:C.muted,marginTop:1}}>{detail}</div>
      </div>
      <span style={{fontSize:11,fontWeight:700,color:configured?C.green:C.muted}}>
        {configured?'✓ Configurado':'Não configurado'}
      </span>
    </div>
  );
}

function JobRow({job}){
  const c=statusColor(job.status);
  const elapsed=job.started_at&&job.finished_at
    ?`${Math.round((new Date(job.finished_at)-new Date(job.started_at))/1000)}s`:'—';
  return(
    <tr style={{borderBottom:`1px solid ${C.border}`}}>
      <td style={{padding:'9px 12px'}}>
        <StatusDot status={job.status}/>
        <span style={{color:c,fontWeight:600,fontSize:12}}>{job.status}</span>
      </td>
      <td style={{padding:'9px 12px',color:C.text,fontSize:12}}>{job.job}</td>
      <td style={{padding:'9px 12px',color:C.muted,fontSize:11}}>{(job.started_at||'').replace('T',' ').slice(0,19)}</td>
      <td style={{padding:'9px 12px',color:C.muted,fontSize:11,textAlign:'right'}}>{elapsed}</td>
    </tr>
  );
}

export default function Automation(){
  const [status,setStatus]=useState(null);
  const [history,setHistory]=useState(null);
  const [loading,setLoading]=useState(true);
  const [running,setRunning]=useState(false);
  const [error,setError]=useState('');

  async function load(){
    setLoading(true);setError('');
    try{
      const [s,h]=await Promise.all([api.automationStatus(),api.automationHistory()]);
      setStatus(s.data||s);
      setHistory(h.data||h);
    }catch(e){setError(e.message);}
    finally{setLoading(false);}
  }

  async function runPipeline(){
    setRunning(true);setError('');
    try{await api.automationRun();await load();}
    catch(e){setError(e.message);}finally{setRunning(false);}
  }

  useEffect(()=>{load();},[]);

  if(loading&&!status) return(
    <div style={{display:'flex',justifyContent:'center',alignItems:'center',
      height:'60vh',color:C.muted,fontSize:14}}>Carregando…</div>
  );

  const st=status||{};
  const integrations=st.integrations||{};
  const edgeHealth=st.edge_health||{};
  const runs=(history?.runs||[]).slice().reverse().slice(0,15);
  const overallStatus=st.overall_status||'NOT_RUN';
  const lastRun=st.last_run_at?(new Date(st.last_run_at)).toLocaleString('pt-BR'):'Nunca';
  const clv=edgeHealth.clv_last_30d_pct||0;
  const beating=edgeHealth.beating_market;
  const rec=edgeHealth.recommendation||'—';

  return(
    <div style={{background:C.bg,minHeight:'100vh',padding:24,
      fontFamily:"'Inter',sans-serif",color:C.text}}>

      {/* Header */}
      <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:24}}>
        <div>
          <h1 style={{margin:0,fontSize:20,fontWeight:800}}>
            ⚙ Automation
            <span style={{fontSize:12,fontWeight:400,color:C.muted,marginLeft:10}}>
              Modo: {st.app_mode||'PAPER_TRADING_SIMULATION_ONLY'}
            </span>
          </h1>
          <p style={{margin:'4px 0 0',color:C.muted,fontSize:12}}>
            Pipeline completo · Scheduler {integrations.apscheduler_available?'APScheduler':'manual'} ·
            TZ {st.scheduler_timezone||'America/Sao_Paulo'} · {st.scheduler_run_hours||'7,13,19'}h
          </p>
        </div>
        <div style={{display:'flex',gap:8}}>
          <button onClick={load} style={{background:C.surface,color:C.muted,
            border:`1px solid ${C.border}`,borderRadius:8,padding:'8px 14px',cursor:'pointer',fontSize:12}}>
            ↻ Refresh
          </button>
          <button onClick={runPipeline} disabled={running}
            style={{background:C.accent,color:'#fff',border:'none',borderRadius:8,
            padding:'8px 16px',cursor:running?'default':'pointer',fontSize:13,fontWeight:600,opacity:running?.7:1}}>
            {running?'Executando…':'▶ Executar Pipeline'}
          </button>
        </div>
      </div>

      {error&&<div style={{background:`${C.red}22`,border:`1px solid ${C.red}55`,
        borderRadius:10,padding:'10px 16px',marginBottom:20,color:C.red,fontSize:13}}>
        ⚠ {error}
      </div>}

      {/* Status geral */}
      <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(200px,1fr))',gap:14,marginBottom:20}}>
        {[
          {label:'Status do Pipeline',value:<><StatusDot status={overallStatus}/>{overallStatus}</>,sub:`Última: ${lastRun}`},
          {label:'CLV 30 dias',value:`${clv>=0?'+':''}${clv.toFixed(1)}%`,sub:beating?'✓ Batendo mercado':'Coletando dados…',
            color:clv>2?C.green:clv>=0?C.orange:C.red},
          {label:'Exportados hoje',value:st.exported_candidates_count??0,sub:'Candidatos exportados'},
          {label:'Alertas Telegram',value:st.alerts_dispatched_count??0,
            sub:integrations.telegram_configured?'Bot configurado':'Bot não configurado',
            color:integrations.telegram_configured?C.green:C.muted},
        ].map((k,i)=>(
          <div key={i} style={{background:C.card,border:`1px solid ${C.border}`,borderRadius:12,padding:'16px 20px'}}>
            <div style={{color:C.muted,fontSize:11,fontWeight:700,textTransform:'uppercase',marginBottom:4}}>{k.label}</div>
            <div style={{fontSize:20,fontWeight:700,color:k.color||C.text}}>{k.value}</div>
            {k.sub&&<div style={{color:C.muted,fontSize:11,marginTop:2}}>{k.sub}</div>}
          </div>
        ))}
      </div>

      {/* Edge health */}
      <div style={{background:C.card,border:`1px solid ${edgeHealth.edge_deteriorating?C.red+'55':C.border}`,
        borderRadius:12,padding:'16px 20px',marginBottom:20}}>
        <div style={{color:C.muted,fontSize:11,fontWeight:700,textTransform:'uppercase',marginBottom:10}}>
          🔬 Saúde do Edge
        </div>
        <div style={{display:'flex',gap:24,flexWrap:'wrap',alignItems:'center'}}>
          <div>
            <span style={{color:C.muted,fontSize:12}}>CLV 30d: </span>
            <span style={{fontWeight:700,color:clv>0?C.green:C.red}}>{clv.toFixed(2)}%</span>
          </div>
          <div>
            <span style={{color:C.muted,fontSize:12}}>Batendo mercado: </span>
            <span style={{fontWeight:700,color:beating?C.green:C.orange}}>{beating?'SIM':'NÃO'}</span>
          </div>
          {edgeHealth.edge_deteriorating&&(
            <span style={{background:`${C.red}22`,color:C.red,border:`1px solid ${C.red}55`,
              borderRadius:6,padding:'3px 10px',fontSize:11,fontWeight:700}}>
              ⚠ EDGE DETERIORANDO
            </span>
          )}
          <div style={{color:C.muted,fontSize:12}}>
            Recomendação: <span style={{color:C.text,fontWeight:600}}>{rec}</span>
          </div>
        </div>
      </div>

      {/* Integrações */}
      <div style={{marginBottom:20}}>
        <div style={{color:C.muted,fontSize:11,fontWeight:700,textTransform:'uppercase',
          letterSpacing:'0.05em',marginBottom:10}}>🔌 Integrações</div>
        <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(280px,1fr))',gap:10}}>
          <IntegrationCard icon="⚽" label="Football-Data.org" detail="Dados históricos reais"
            configured={integrations.football_data_api}/>
          <IntegrationCard icon="📊" label="The Odds API" detail="Odds em tempo real"
            configured={integrations.odds_api}/>
          <IntegrationCard icon="✈" label="Telegram Bot" detail={`${st.alerts_dispatched_count||0} alertas enviados`}
            configured={integrations.telegram_configured}/>
          <IntegrationCard icon="🤖" label="Groq AI (Llama 3.3 70B)" detail="Assistente analítico"
            configured={integrations.groq_ai_configured}/>
          <IntegrationCard icon="🕐" label="APScheduler" detail={`${st.scheduler_run_hours||'7,13,19'}h · ${st.scheduler_timezone}`}
            configured={integrations.apscheduler_available}/>
        </div>
      </div>

      {/* Histórico de runs */}
      <div style={{background:C.card,border:`1px solid ${C.border}`,borderRadius:14,overflow:'hidden',marginBottom:20}}>
        <div style={{padding:'14px 20px',borderBottom:`1px solid ${C.border}`,fontWeight:700,fontSize:14}}>
          📋 Histórico de Execuções ({runs.length})
        </div>
        {runs.length===0?(
          <div style={{padding:'32px 20px',textAlign:'center',color:C.muted,fontSize:13}}>
            Nenhuma execução registrada. Execute o pipeline.
          </div>
        ):(
          <>
            <div style={{overflowX:'auto'}}>
              <table style={{width:'100%',borderCollapse:'collapse',fontSize:12}}>
                <thead>
                  <tr style={{background:C.surface}}>
                    {['Status Geral','Início','Jobs OK / Total','Jobs com Falha'].map(h=>(
                      <th key={h} style={{padding:'9px 12px',color:C.muted,fontWeight:700,
                        fontSize:10,textTransform:'uppercase',letterSpacing:'0.04em',textAlign:'left'}}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {runs.map((run,i)=>{
                    const jobs=run.jobs||[];
                    const ok=jobs.filter(j=>j.status==='SUCCESS').length;
                    const failed=run.failed_jobs||[];
                    return(
                      <tr key={i} style={{borderBottom:`1px solid ${C.border}`}}>
                        <td style={{padding:'9px 12px'}}>
                          <StatusDot status={run.status}/>
                          <span style={{color:statusColor(run.status),fontWeight:600}}>{run.status}</span>
                        </td>
                        <td style={{padding:'9px 12px',color:C.muted,fontSize:11}}>
                          {(run.started_at||'').replace('T',' ').slice(0,19)}
                        </td>
                        <td style={{padding:'9px 12px',color:C.text}}>
                          {ok}/{jobs.length}
                        </td>
                        <td style={{padding:'9px 12px',color:failed.length?C.red:C.muted,fontSize:11}}>
                          {failed.length?failed.join(', '):'—'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            {/* Detalhe do último run: jobs individuais */}
            {runs[0]?.jobs?.length>0&&(
              <div style={{padding:'0 0 4px'}}>
                <div style={{padding:'10px 20px',color:C.muted,fontSize:11,borderTop:`1px solid ${C.border}`}}>
                  Jobs da última execução:
                </div>
                <table style={{width:'100%',borderCollapse:'collapse',fontSize:11}}>
                  <thead>
                    <tr style={{background:C.surface}}>
                      {['Status','Job','Início','Duração'].map(h=>(
                        <th key={h} style={{padding:'7px 12px',color:C.muted,fontWeight:700,
                          fontSize:10,textTransform:'uppercase',textAlign:h==='Duração'?'right':'left'}}>
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>{runs[0].jobs.map((j,i)=><JobRow key={i} job={j}/>)}</tbody>
                </table>
              </div>
            )}
          </>
        )}
      </div>

      <div style={{color:C.muted,fontSize:11,textAlign:'center',paddingBottom:8}}>
        MatchFlow v7.0 · Sistema não executa apostas automáticas · Confirmação manual obrigatória
      </div>
    </div>
  );
}
