import { useState, useCallback } from 'react';
import { apiRequest } from '../api/client';

const C={bg:'#0f1117',surface:'#1a1d2e',card:'#232640',border:'#2e3356',
  text:'#e2e8f0',muted:'#8892b0',accent:'#7c6aff',green:'#22c55e',
  red:'#ef4444',orange:'#f59e0b',blue:'#3b82f6'};

function Input({label,value,onChange,min,max,step,suffix}){
  return(
    <div style={{marginBottom:14}}>
      <label style={{display:'block',color:C.muted,fontSize:11,fontWeight:700,
        textTransform:'uppercase',marginBottom:6}}>{label}</label>
      <div style={{display:'flex',alignItems:'center',gap:8}}>
        <input type="number" value={value} onChange={e=>onChange(parseFloat(e.target.value)||0)}
          min={min} max={max} step={step||0.01}
          style={{background:C.surface,color:C.text,border:`1px solid ${C.border}`,borderRadius:8,
          padding:'8px 12px',fontSize:13,width:'100%',outline:'none'}}/>
        {suffix&&<span style={{color:C.muted,fontSize:12,whiteSpace:'nowrap'}}>{suffix}</span>}
      </div>
    </div>
  );
}

function FanChart({data,initial}){
  if(!data) return null;
  const {p10,p25,p50_median,p75,p90}=data;
  const vals=[p10,p25,p50_median,p75,p90].filter(Boolean);
  if(!vals.length) return null;
  const w=540,h=140,pl=56,pr=16,pt=10,pb=28;
  const W=w-pl-pr,H=h-pt-pb;
  const all=[initial,...vals];
  const mn=Math.min(...all)*0.92, mx=Math.max(...all)*1.05;
  const range=mx-mn||1;
  const x=(i,total)=>pl+i/(total-1)*W;
  const y=v=>pt+(1-(v-mn)/range)*H;
  const n=6; // initial + 5 percentis
  const xs=[0,1,2,3,4,5];
  const ys=[initial,p10,p25,p50_median,p75,p90];

  const line=(pts)=>pts.map((p,i)=>`${i===0?'M':'L'}${x(i,pts.length)},${y(p)}`).join(' ');
  const area=(top,bot)=>{
    const fwd=top.map((p,i)=>`${x(i,top.length)},${y(p)}`).join(' ');
    const bwd=[...bot].reverse().map((p,i)=>`${x(bot.length-1-i,bot.length)},${y(p)}`).join(' ');
    return `M ${fwd} L ${bwd} Z`;
  };

  // Fan bands (5 pontos: percentis p10..p90, x=1..5)
  const fanPts=[[p10,p25,p50_median,p75,p90]]; // array para mapear

  return(
    <svg width="100%" viewBox={`0 0 ${w} ${h}`} style={{display:'block'}}>
      <defs>
        <linearGradient id="fg1" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={C.accent} stopOpacity={0.25}/>
          <stop offset="100%" stopColor={C.accent} stopOpacity={0.03}/>
        </linearGradient>
        <linearGradient id="fg2" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={C.blue} stopOpacity={0.15}/>
          <stop offset="100%" stopColor={C.blue} stopOpacity={0.02}/>
        </linearGradient>
      </defs>
      {/* Grid */}
      {[0,0.25,0.5,0.75,1].map(t=>(
        <line key={t} x1={pl} x2={w-pr} y1={pt+t*H} y2={pt+t*H}
          stroke={C.border} strokeWidth={0.5}/>
      ))}
      {/* Banda P10–P90 */}
      {p10&&p90&&<path d={`M ${pl},${y(initial)} L ${x(5,6)},${y(p90)} L ${x(5,6)},${y(p10)} Z`}
        fill="url(#fg1)" opacity={0.5}/>}
      {/* Banda P25–P75 */}
      {p25&&p75&&<path d={`M ${pl},${y(initial)} L ${x(5,6)},${y(p75)} L ${x(5,6)},${y(p25)} Z`}
        fill="url(#fg2)" opacity={0.7}/>}
      {/* Linha mediana */}
      {p50_median&&<path d={`M ${pl},${y(initial)} L ${x(5,6)},${y(p50_median)}`}
        stroke={C.accent} strokeWidth={2.5} fill="none" strokeLinecap="round"/>}
      {/* Linhas P10 e P90 */}
      {p10&&<path d={`M ${pl},${y(initial)} L ${x(5,6)},${y(p10)}`}
        stroke={C.red} strokeWidth={1} fill="none" strokeDasharray="4,3" opacity={0.7}/>}
      {p90&&<path d={`M ${pl},${y(initial)} L ${x(5,6)},${y(p90)}`}
        stroke={C.green} strokeWidth={1} fill="none" strokeDasharray="4,3" opacity={0.7}/>}
      {/* Linha de banca inicial */}
      <line x1={pl} x2={w-pr} y1={y(initial)} y2={y(initial)}
        stroke={C.muted} strokeWidth={0.8} strokeDasharray="6,4" opacity={0.5}/>
      {/* Y labels */}
      {[mn,mx].map((v,i)=>(
        <text key={i} x={pl-4} y={i===0?pt+H:pt+8} textAnchor="end" fontSize={9} fill={C.muted}>
          {v.toFixed(0)}
        </text>
      ))}
      {/* X labels */}
      {['Hoje','1m','2m','3m','4m','5m','6m'].slice(0,6).map((l,i)=>(
        <text key={i} x={x(i,6)} y={h-8} textAnchor="middle" fontSize={9} fill={C.muted}>{l}</text>
      ))}
      {/* Legend */}
      <g>
        <line x1={pl} y1={h-5} x2={pl+16} y2={h-5} stroke={C.accent} strokeWidth={2}/>
        <text x={pl+20} y={h-2} fontSize={9} fill={C.muted}>Mediana</text>
        <line x1={pl+80} y1={h-5} x2={pl+96} y2={h-5} stroke={C.green} strokeWidth={1} strokeDasharray="4,3"/>
        <text x={pl+100} y={h-2} fontSize={9} fill={C.muted}>P90</text>
        <line x1={pl+130} y1={h-5} x2={pl+146} y2={h-5} stroke={C.red} strokeWidth={1} strokeDasharray="4,3"/>
        <text x={pl+150} y={h-2} fontSize={9} fill={C.muted}>P10</text>
      </g>
    </svg>
  );
}

const SCENARIOS=[
  {clv:-0.01,label:'Sem edge (-1%)'},
  {clv:0.0, label:'Neutro (0%)'},
  {clv:0.02,label:'Marginal (+2%)'},
  {clv:0.03,label:'Bom (+3%)'},
  {clv:0.05,label:'Forte (+5%)'},
  {clv:0.08,label:'Excepcional (+8%)'},
];

export default function BankrollProjection(){
  const [clv,setClv]=useState(3);
  const [betsPerWeek,setBetsPerWeek]=useState(5);
  const [kelly,setKelly]=useState(25);
  const [initial,setInitial]=useState(1000);
  const [result,setResult]=useState(null);
  const [loading,setLoading]=useState(false);
  const [error,setError]=useState('');

  const run=useCallback(async()=>{
    setLoading(true);setError('');
    try{
      const res=await apiRequest('/api/performance/monte-carlo',{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({
          edge_per_bet:clv/100,
          bets_per_week:betsPerWeek,
          kelly_fraction:kelly/100,
          initial_bankroll:initial,
          simulations:5000,
          weeks:26,
        }),
      });
      setResult(res.data||res);
    }catch(e){
      // Fallback: calcular localmente com fórmula simplificada
      const win_prob=(1+clv/100)/1.85;
      const p10=initial*Math.pow(1+clv/100*kelly/100,betsPerWeek*26*0.3);
      const p50=initial*Math.pow(1+clv/100*kelly/100,betsPerWeek*26*0.8);
      const p90=initial*Math.pow(1+clv/100*kelly/100,betsPerWeek*26*1.4);
      setResult({
        projections:{p10:Math.max(0,p10).toFixed(2),p25:(p10*1.15).toFixed(2),
          p50_median:Math.max(0,p50).toFixed(2),p75:(p50*1.15).toFixed(2),p90:Math.max(0,p90).toFixed(2)},
        risk:{ruin_probability_pct:clv<0?35:clv<2?12:3,prob_doubling:(clv>3?.35:.12)},
        kelly:{optimal_quarter:(clv/100*0.25).toFixed(4),used_fraction:kelly/100},
        note:'Calculado localmente (API offline)',
      });
    }
    setLoading(false);
  },[clv,betsPerWeek,kelly,initial]);

  const proj=result?.projections;
  const risk=result?.risk;
  const kellyData=result?.kelly;

  return(
    <div style={{background:C.bg,minHeight:'100vh',padding:24,
      fontFamily:"'Inter',sans-serif",color:C.text}}>
      <div style={{marginBottom:24}}>
        <h1 style={{margin:0,fontSize:20,fontWeight:800}}>🎲 Projeção de Banca</h1>
        <p style={{margin:'4px 0 0',color:C.muted,fontSize:12}}>
          Monte Carlo · 5.000 simulações · Horizonte 6 meses
        </p>
      </div>

      <div style={{display:'grid',gridTemplateColumns:'300px 1fr',gap:20,flexWrap:'wrap'}}>

        {/* Inputs */}
        <div style={{background:C.card,border:`1px solid ${C.border}`,borderRadius:14,padding:20}}>
          <div style={{color:C.muted,fontSize:11,fontWeight:700,textTransform:'uppercase',marginBottom:16}}>
            Parâmetros
          </div>
          <Input label="CLV estimado (%)" value={clv} onChange={setClv} min={-5} max={20} step={0.5} suffix="%"/>
          <Input label="Apostas por semana" value={betsPerWeek} onChange={setBetsPerWeek} min={1} max={30} step={1}/>
          <Input label="Kelly fraction (%)" value={kelly} onChange={setKelly} min={5} max={50} step={5} suffix="%"/>
          <Input label="Banca inicial (R$)" value={initial} onChange={setInitial} min={100} max={100000} step={100} suffix="R$"/>

          <button onClick={run} disabled={loading}
            style={{width:'100%',background:C.accent,color:'#fff',border:'none',borderRadius:8,
            padding:'10px',cursor:loading?'default':'pointer',fontSize:13,fontWeight:700,
            marginTop:4,opacity:loading?.7:1}}>
            {loading?'Simulando…':'▶ Simular 5.000 cenários'}
          </button>

          {/* Cenários rápidos */}
          <div style={{marginTop:16}}>
            <div style={{color:C.muted,fontSize:10,fontWeight:700,textTransform:'uppercase',marginBottom:8}}>
              Cenários rápidos
            </div>
            <div style={{display:'flex',flexWrap:'wrap',gap:6}}>
              {SCENARIOS.map(s=>(
                <button key={s.clv} onClick={()=>{setClv(s.clv*100);run();}}
                  style={{background:C.surface,color:parseFloat(s.clv)>0?C.green:C.red,
                  border:`1px solid ${C.border}`,borderRadius:6,padding:'4px 8px',
                  cursor:'pointer',fontSize:10,fontWeight:600}}>
                  {s.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Resultado */}
        <div>
          {!result?(
            <div style={{background:C.card,border:`1px solid ${C.border}`,borderRadius:14,
              padding:'60px 20px',textAlign:'center',color:C.muted,fontSize:13}}>
              Configure os parâmetros e clique em "Simular" para ver a projeção de banca.
            </div>
          ):(
            <>
              {/* Fan Chart */}
              <div style={{background:C.card,border:`1px solid ${C.border}`,borderRadius:14,
                padding:'16px 20px',marginBottom:16}}>
                <div style={{fontWeight:700,fontSize:14,marginBottom:12}}>
                  📈 Distribuição de Resultados — {betsPerWeek * 26} apostas em 26 semanas
                </div>
                <FanChart data={proj} initial={initial}/>
                <div style={{display:'flex',gap:20,marginTop:12,flexWrap:'wrap'}}>
                  {[
                    {label:'P10 (pessimista)',v:proj?.p10,c:C.red},
                    {label:'P25',v:proj?.p25,c:C.orange},
                    {label:'P50 (mediana)',v:proj?.p50_median,c:C.accent},
                    {label:'P75',v:proj?.p75,c:C.blue},
                    {label:'P90 (otimista)',v:proj?.p90,c:C.green},
                  ].map(({label,v,c})=>(
                    <div key={label} style={{textAlign:'center'}}>
                      <div style={{color:C.muted,fontSize:10}}>{label}</div>
                      <div style={{color:c,fontWeight:700,fontSize:14}}>
                        R$ {parseFloat(v||0).toFixed(0)}
                      </div>
                      <div style={{color:C.muted,fontSize:10}}>
                        {((parseFloat(v||0)/initial-1)*100).toFixed(1)}%
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Risk metrics */}
              <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(160px,1fr))',gap:12,marginBottom:16}}>
                {[
                  {label:'Prob. de Ruína',v:`${risk?.ruin_probability_pct||0}%`,
                    c:risk?.ruin_probability_pct>15?C.red:risk?.ruin_probability_pct>5?C.orange:C.green,
                    sub:'Banca < 10% inicial'},
                  {label:'Prob. de Dobrar',v:`${((risk?.prob_doubling||0)*100).toFixed(0)}%`,
                    c:(risk?.prob_doubling||0)>.3?C.green:C.orange,sub:'Banca ≥ 2x inicial'},
                  {label:'Kelly Ótimo',v:`${((kellyData?.optimal_quarter||0)*100).toFixed(1)}%`,
                    c:C.accent,sub:'Quarter Kelly recomendado'},
                  {label:'Banca Mediana',v:`R$ ${parseFloat(proj?.p50_median||initial).toFixed(0)}`,
                    c:parseFloat(proj?.p50_median||0)>=initial?C.green:C.red,
                    sub:'50% das simulações'},
                ].map((k,i)=>(
                  <div key={i} style={{background:C.card,border:`1px solid ${C.border}`,
                    borderRadius:12,padding:'14px 16px'}}>
                    <div style={{color:C.muted,fontSize:10,fontWeight:700,textTransform:'uppercase',marginBottom:4}}>
                      {k.label}
                    </div>
                    <div style={{color:k.c,fontSize:20,fontWeight:700}}>{k.v}</div>
                    <div style={{color:C.muted,fontSize:10,marginTop:2}}>{k.sub}</div>
                  </div>
                ))}
              </div>

              {/* Aviso de interpretação */}
              <div style={{background:`${C.orange}11`,border:`1px solid ${C.orange}33`,
                borderRadius:10,padding:'12px 16px',fontSize:12,color:C.muted}}>
                <strong style={{color:C.orange}}>⚠ Interpretação:</strong>{' '}
                Projeções assumem que o CLV de {clv}% se mantém constante.
                Na prática, o edge pode variar. CLV médio positivo só é confiável após 300+ apostas com significância p{'<'}0.05.
                {result?.note&&<span style={{color:C.muted,fontStyle:'italic'}}> ({result.note})</span>}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
