import LanguageSelector from '../components/LanguageSelector.jsx';
import logo from '../assets/brand/matchflow-ai-logo.jpeg';

const pillars = [
  { title: 'Data Engine', text: 'FlashScore internal provider, enrichment, mapping, deduplication and data quality.', tag: 'Internal data core', metric: 'Quality scored' },
  { title: 'Machine Learning', text: 'Random Forest, LightGBM, XGBoost, calibration and drift monitoring.', tag: 'Model intelligence', metric: '3-model ensemble' },
  { title: 'Decision Engine', text: 'AI-powered signal ranking with EV, confidence, risk and bankroll simulation.', tag: 'Paper signals', metric: 'EV + risk' },
  { title: 'Monitoring', text: 'Scheduler, jobs, coverage, health, alerts and production observability.', tag: 'Ops ready', metric: 'Live health' },
  { title: 'Safety', text: 'Paper trading simulation only. No automatic real action.', tag: 'Manual confirmation', metric: 'Safe mode' },
];

const pipelineNodes = [
  ['FlashScore', 'network capture'],
  ['Enrichment', 'Football-Data + Odds'],
  ['Mapping', 'canonical identity'],
  ['ML Ensemble', 'RF · LGBM · XGB'],
  ['Calibration', 'real evidence aware'],
  ['Drift Monitoring', 'PSI · KS · JS'],
  ['Decision Engine', 'EV · confidence · risk'],
  ['Paper Trading', 'simulation only'],
];

const productScreens = [
  { title: 'Decision Engine', label: 'VALUE SIGNAL', value: '0.74', meta: 'confidence · EV · bankroll' },
  { title: 'Monitoring', label: 'HEALTHY', value: 'Live', meta: 'jobs · alerts · coverage' },
  { title: 'ML Calibration', label: 'RELIABILITY', value: 'ECE', meta: 'brier · bins · drift' },
  { title: 'Data Ops', label: 'INTERNAL', value: 'FS', meta: 'mapping · dedup · quality' },
];

const demoFeed = [
  'Demo Activity · Data Engine heartbeat received',
  'Simulation · Calibration dashboard refreshed',
  'Demo Activity · Drift monitor checked feature stability',
  'Simulation · Decision queue preview updated',
];

function TacticalField() {
  const nodes = ['GK', 'CB', 'DM', 'AI', 'EV', 'ML', 'RX'];
  return (
    <div className="landing-field cinematic-field" aria-hidden="true">
      <div className="field-line field-line-mid" />
      <div className="field-line field-box-left" />
      <div className="field-line field-box-right" />
      <div className="data-wave" />
      <div className="signal-trace" />
      <div className="football-dot" />
      <div className="ai-connection connection-one" />
      <div className="ai-connection connection-two" />
      <div className="cinematic-particle p1" /><div className="cinematic-particle p2" /><div className="cinematic-particle p3" />
      {nodes.map((node, index) => (
        <span key={node} className={`player-node node-${index}`}>{node}</span>
      ))}
    </div>
  );
}

function MockDashboard() {
  return (
    <div className="mock-dashboard-panel cinematic-dashboard" aria-label="Product preview">
      <div className="mock-window-bar"><span /><span /><span /><b>MatchFlow AI Live Terminal</b></div>
      <div className="mock-dashboard-grid four">
        {productScreens.map((screen) => (
          <article key={screen.title} className="mock-widget cinematic-widget">
            <small>{screen.title}</small>
            <strong>{screen.value}</strong>
            <span>{screen.label}</span>
            <p>{screen.meta}</p>
            <div className="mock-bars"><i /><i /><i /><i /></div>
          </article>
        ))}
      </div>
      <div className="mock-signal-table">
        {['Data Engine Ops', 'Drift Dashboard', 'Decision Queue', 'Evidence Alerts'].map((row, index) => (
          <div key={row} className="mock-row" style={{ '--row-delay': `${index * 120}ms` }}>
            <span>{row}</span><b>{index === 0 ? 'Ready' : index === 1 ? 'Watching' : index === 2 ? 'Paper only' : 'Demo Safe'}</b>
          </div>
        ))}
      </div>
    </div>
  );
}

function DemoTimeline() {
  return (
    <section className="demo-experience-panel" aria-label="Demo activity timeline">
      <div className="landing-section-copy centered">
        <span className="landing-kicker compact">Public demo mode</span>
        <h2>Live feeling, clearly marked as simulation.</h2>
        <p>Animated activity helps presentations without pretending that demo events are real operations.</p>
      </div>
      <div className="demo-feed">
        {demoFeed.map((item, index) => <div key={item} className="demo-feed-item" style={{ '--feed-delay': `${index * 150}ms` }}><i />{item}</div>)}
      </div>
    </section>
  );
}

function ReliabilityChart() {
  return (
    <div className="landing-chart-card" aria-label="Animated reliability chart">
      <div><span>Calibration Curve</span><b>Reliability</b></div>
      <svg viewBox="0 0 260 120" role="img" aria-label="Calibration curve preview">
        <defs><linearGradient id="chartGlow" x1="0" x2="1"><stop offset="0" stopColor="#22d3ee"/><stop offset="1" stopColor="#22c55e"/></linearGradient></defs>
        <path className="chart-grid-line" d="M20 95H240M20 65H240M20 35H240" />
        <path className="chart-ideal" d="M24 96L238 28" />
        <path className="chart-curve" d="M24 90 C64 78, 84 83, 118 60 S180 34, 238 30" />
        <path className="chart-band" d="M24 102 C64 89, 84 92, 118 70 S180 43, 238 40 L238 64 C180 56, 118 83, 84 101 S64 102, 24 112 Z" />
      </svg>
    </div>
  );
}

export default function LandingPage({ setPage }) {
  return (
    <main className="landing-page premium-brand-page cinematic-page">
      <section className="landing-hero cinematic-hero">
        <div className="landing-orbit orbit-one" />
        <div className="landing-orbit orbit-two" />
        <div className="landing-particle particle-one" />
        <div className="landing-particle particle-two" />
        <div className="cinematic-depth-layer layer-one" />
        <div className="cinematic-depth-layer layer-two" />
        <div className="landing-copy">
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 12 }}><LanguageSelector compact /></div>
          <img className="landing-logo cinematic-logo" src={logo} alt="MatchFlow AI" />
          <span className="landing-kicker">Quant football intelligence · AI-native operations</span>
          <h1>AI-Native Football Intelligence Platform</h1>
          <h2>Advanced data engine, ensemble machine learning, calibration, drift monitoring and decision intelligence.</h2>
          <p>
            MatchFlow AI transforma dados de futebol em uma experiência operacional premium: scraping interno, qualidade de dados,
            ML calibrado, monitoramento quantitativo e sinais finais seguros em PAPER_TRADING_SIMULATION_ONLY.
          </p>
          <div className="landing-actions">
            <button type="button" className="landing-btn primary" onClick={() => setPage('Login')}>Launch Dashboard</button>
            <button type="button" className="landing-btn ghost" onClick={() => document.getElementById('landing-preview')?.scrollIntoView({ behavior: 'smooth', block: 'start' })}>Live Demo</button>
            <button type="button" className="landing-btn ghost" onClick={() => document.getElementById('landing-pipeline')?.scrollIntoView({ behavior: 'smooth', block: 'start' })}>View Architecture</button>
          </div>
          <div className="landing-status-strip" aria-label="Status da plataforma">
            <span><i /> Data Engine</span>
            <span><i /> ML Calibration</span>
            <span><i /> Decision Engine</span>
            <span><i /> Monitoring</span>
          </div>
        </div>
        <div className="landing-visual cinematic-visual">
          <TacticalField />
          <div className="landing-metric-card metric-one floating-card">
            <small>Signal Quality</small>
            <strong>AI Ranked</strong>
            <span>EV · Risk · Bankroll</span>
          </div>
          <div className="landing-metric-card metric-two floating-card">
            <small>Mode</small>
            <strong>Paper Only</strong>
            <span>No automatic real action</span>
          </div>
          <div className="landing-metric-card metric-three floating-card">
            <small>Ops</small>
            <strong>Live Pulse</strong>
            <span>jobs · alerts · drift</span>
          </div>
        </div>
      </section>

      <section id="landing-preview" className="landing-preview-section">
        <div className="landing-section-copy">
          <span className="landing-kicker compact">Product cockpit</span>
          <h2>Built like an enterprise intelligence desk.</h2>
          <p>Decision Engine, Monitoring, Data Engine Ops, ML Calibration and Drift dashboards presented as one operational product.</p>
        </div>
        <MockDashboard />
      </section>

      <section className="landing-chart-section">
        <ReliabilityChart />
        <div className="chart-copy">
          <span className="landing-kicker compact">Advanced chart polish</span>
          <h2>Animated reliability, drift and confidence views.</h2>
          <p>Lightweight SVG motion provides a live quant feel while respecting reduced-motion preferences and keeping the build lean.</p>
        </div>
      </section>

      <section id="landing-pipeline" className="landing-pipeline-section cinematic-pipeline">
        <div className="landing-section-copy centered">
          <span className="landing-kicker compact">Operational pipeline</span>
          <h2>From raw football data to safe paper signals.</h2>
        </div>
        <div className="pipeline-flow" aria-label="MatchFlow AI pipeline">
          {pipelineNodes.map(([node, meta], index) => (
            <div key={node} className="pipeline-node cinematic-node" style={{ '--node-delay': `${index * 90}ms` }}>
              <span>{String(index + 1).padStart(2, '0')}</span>
              <strong>{node}</strong>
              <small>{meta}</small>
            </div>
          ))}
        </div>
      </section>

      <DemoTimeline />

      <section id="landing-demo-sections" className="landing-sections">
        {pillars.map((item, index) => (
          <article className="landing-feature-card" key={item.title} style={{ '--delay': `${index * 70}ms` }}>
            <span>{item.tag}</span>
            <h3>{item.title}</h3>
            <p>{item.text}</p>
            <b>{item.metric}</b>
          </article>
        ))}
      </section>
    </main>
  );
}
