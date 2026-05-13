import { useI18n } from '../i18n.js';
import { useApp } from '../store/AppContext.jsx';

const SECTIONS = [
  { label:'ERP', items:[
    { page:'Home', icon:'⌂', key:'home' },
    { page:'Dashboard', icon:'◇', key:'dashboard' },
    { page:'Competitions', icon:'▦', key:'competitions' },
  ]},
  { label:'AI Platform', items:[
    { page:'AI Copilot Premium', icon:'✦', key:'aiCopilotPremium' },
    { page:'Agentic Intelligence', icon:'✧', key:'agenticIntelligence' },
    { page:'Autonomous Workspace', icon:'◆', key:'autonomousWorkspace' },
    { page:'Cognitive Workspace', icon:'◈', key:'cognitiveWorkspace' },
    { page:'Executive Cockpit', icon:'⬡', key:'executiveCockpit' },
    { page:'Evolution Cockpit', icon:'⬢', key:'evolutionCockpit' },
    { page:'Live Center', icon:'◉', key:'liveCenter' },
    { page:'AI Explainability', icon:'◬', key:'aiExplainability' },
    { page:'Paper Trading Premium', icon:'◍', key:'paperTradingPremium' },
    { page:'Premium Analytics', icon:'▥', key:'premiumAnalytics' },
  ]},
  { label:'Inteligência', items:[
    { page:'Decision Engine', icon:'◎', key:'decision' },
    { page:'Bankroll Projection', icon:'◍', key:'bankroll' },
    { page:'Backtest Lab', icon:'▣', key:'backtest' },
    { page:'ML Lab', icon:'✦', key:'ml' },
  ]},
  { label:'Operação', items:[
    { page:'Data Operations', icon:'⚙', key:'operations' },
    { page:'Test Lab', icon:'▧', key:'testLab' },
    { page:'Monitoring', icon:'◌', key:'monitoring' },
    { page:'Automation', icon:'↻', key:'automation' },
  ]},
  { label:'Governança', items:[
    { page:'Data Quality', icon:'✓', key:'quality' },
    { page:'Team Analytics', icon:'♟', key:'teams' },
    { page:'System Status', icon:'◈', key:'system' },
    { page:'Assistant', icon:'✎', key:'assistant' },
  ]},
];

export default function Sidebar({ page, setPage }) {
  const { t } = useI18n();
  const { user } = useApp();
  const perms = new Set(user?.permissions || []);
  const role = String(user?.role || '').toLowerCase();
  const canSeePage = (p) => {
    if (role === 'admin' || perms.has('view_all')) return true;
    if (p === 'System Status') return perms.has('view_system_status');
    if (['Automation'].includes(p)) return role !== 'viewer';
    return true;
  };
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="brand-mark">MF</div>
        <div>
          <h1>Match<span>Flow</span></h1>
          <p>{t('appSubtitle')}</p>
        </div>
      </div>

      <nav className="sidebar-nav">
        {SECTIONS.map(({ label, items }) => (
          <div key={label}>
            <div className="sidebar-section-label">{label}</div>
            {items.filter((item) => canSeePage(item.page)).map(({ page: p, icon, key }) => (
              <button
                key={p}
                className={`sidebar-item${page === p ? ' active' : ''}`}
                onClick={() => setPage(p)}
              >
                <span className="sidebar-icon">{icon}</span>
                <span>{t(key)}</span>
              </button>
            ))}
          </div>
        ))}
      </nav>

      <div className="sidebar-footer">
        <strong>{user?.is_demo ? 'DEMO PAPER MODE' : 'PAPER MODE'}</strong><br />
        {t('noAutoBet')}
      </div>
    </aside>
  );
}
