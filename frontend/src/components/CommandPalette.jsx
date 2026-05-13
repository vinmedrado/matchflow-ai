import { useEffect, useMemo, useRef, useState } from 'react';
import { api } from '../api/client.js';
import { useApp } from '../store/AppContext.jsx';

const MAX_RECENTS = 6;
const FAVORITES_KEY = 'matchflow_ai_command_favorites';
const RECENTS_KEY = 'matchflow_ai_command_recents';

const NAV_ACTIONS = [
  { id: 'nav-dashboard', type: 'navigation', group: 'Navigation', icon: '⌁', page: 'Dashboard', label: 'Open Dashboard', hint: 'Executive KPIs and platform overview', shortcut: 'G D', keywords: 'home dashboard overview kpi' },
  { id: 'nav-monitoring', type: 'navigation', group: 'Navigation', icon: '◌', page: 'Monitoring', label: 'Open Monitoring', hint: 'Drift, alerts, jobs and model health', shortcut: 'G M', keywords: 'monitor drift alerts health jobs' },
  { id: 'nav-candidates', type: 'navigation', group: 'Navigation', icon: '◇', page: 'Decision Engine', label: 'Open Decision Candidates', hint: 'Signals, EV, risk and bankroll simulation', shortcut: 'G C', keywords: 'decision candidates signal ev risk' },
  { id: 'nav-drift', type: 'navigation', group: 'Navigation', icon: '≋', page: 'Monitoring', label: 'Open Drift Monitoring', hint: 'Drift severity and model/data stability', shortcut: 'G M', keywords: 'drift monitoring psi ks js' },
  { id: 'nav-calibration', type: 'navigation', group: 'Navigation', icon: '◍', page: 'ML Intelligence', label: 'Open ML Calibration', hint: 'Reliability, Brier, ECE/MCE and calibration quality', shortcut: 'G L', keywords: 'ml calibration reliability brier ece mce' },
  { id: 'nav-dataops', type: 'navigation', group: 'Navigation', icon: '▣', page: 'Data Operations', label: 'Open Data Engine Ops', hint: 'FlashScore, providers, mapping, deduplication and quality', shortcut: 'G O', keywords: 'data engine flashscore provider quality' },
  { id: 'nav-coverage', type: 'navigation', group: 'Navigation', icon: '▤', page: 'Data Operations', label: 'Open Coverage Report', hint: 'Odds, stats, xG, events and parser coverage', shortcut: 'G O', keywords: 'coverage report odds stats xg events' },
  { id: 'nav-architecture', type: 'navigation', group: 'Navigation', icon: '⌬', page: 'Operational Guide', label: 'Open Architecture', hint: 'System architecture, operational guide and release docs', shortcut: 'G R', keywords: 'architecture docs guide system' },
  { id: 'nav-pipelines', type: 'navigation', group: 'Navigation', icon: '▶', page: 'Jobs Center', label: 'Open Pipelines', hint: 'Scheduler jobs and execution history', shortcut: 'G P', keywords: 'pipeline jobs scheduler run' },
];

const JOB_ACTIONS = [
  { id: 'job-data-engine', requiredPermission: 'run_data_engine', group: 'Pipeline Actions', icon: '↻', label: 'Run Data Engine Sync', hint: 'Sync internal FlashScore/Data Engine provider.', jobName: 'data_engine_sync', nextPage: 'Data Operations', successTarget: 'Open Data Engine Ops' },
  { id: 'job-future-matches', requiredPermission: 'run_jobs', group: 'Pipeline Actions', icon: '⧉', label: 'Run Future Matches Pipeline', hint: 'Generate or refresh future match snapshot.', jobName: 'future_matches_pipeline', nextPage: 'Data Operations', successTarget: 'Open Future Matches' },
  { id: 'job-future-features', requiredPermission: 'run_jobs', group: 'Pipeline Actions', icon: 'ƒ', label: 'Run Future Features', hint: 'Build future match feature set.', jobName: 'future_features', nextPage: 'ML Intelligence', successTarget: 'Open ML Intelligence' },
  { id: 'job-future-predictions', requiredPermission: 'run_jobs', group: 'Pipeline Actions', icon: 'π', label: 'Run Future Predictions', hint: 'Generate ensemble predictions for future matches.', jobName: 'future_predictions', nextPage: 'ML Intelligence', successTarget: 'Open Predictions' },
  { id: 'job-full-pipeline', requiredPermission: 'run_jobs', group: 'Pipeline Actions', icon: '⚡', label: 'Run Full Decision Pipeline', hint: 'Run the complete safe PAPER_TRADING_SIMULATION_ONLY pipeline.', jobName: 'full_decision_pipeline', nextPage: 'Decision Engine', successTarget: 'Open Decision Candidates', sensitive: true },
  { id: 'job-drift', requiredPermission: 'run_jobs', group: 'Pipeline Actions', icon: '≋', label: 'Run Drift Analysis', hint: 'Refresh drift report, alerts and monitoring state.', jobName: 'drift_analysis', nextPage: 'Monitoring', successTarget: 'Open Drift Report' },
  { id: 'job-calibration', requiredPermission: 'run_jobs', group: 'Pipeline Actions', icon: '◍', label: 'Run Calibration Refresh', hint: 'Refresh calibration and reliability metrics.', jobName: 'calibration_refresh', nextPage: 'ML Intelligence', successTarget: 'Open Calibration Report' },
  { id: 'job-coverage', requiredPermission: 'run_jobs', group: 'Pipeline Actions', icon: '▤', label: 'Run Coverage Report', hint: 'Recalculate FlashScore odds/stats/events coverage.', jobName: 'coverage_report', nextPage: 'Data Operations', successTarget: 'Open Coverage Report' },
];

const CHECK_ACTIONS = [
  { id: 'check-provider-health', requiredPermission: 'view_data_engine', group: 'Monitoring', icon: '●', label: 'Check Provider Health', hint: 'Fetch Data Engine provider health.', call: () => api.dataEngineProviders(), nextPage: 'Data Operations', resultTitle: 'Provider health checked' },
  { id: 'check-data-quality', requiredPermission: 'view_data_engine', group: 'Monitoring', icon: '◈', label: 'Check Data Quality', hint: 'Fetch Data Engine quality report.', call: () => api.dataEngineQualityReport(), nextPage: 'Data Operations', resultTitle: 'Data quality checked' },
  { id: 'check-drift-status', requiredPermission: 'view_monitoring', group: 'Monitoring', icon: '≋', label: 'Check Drift Status', hint: 'Fetch latest drift report.', call: () => api.monitoringDrift(), nextPage: 'Monitoring', resultTitle: 'Drift status checked' },
  { id: 'check-model-health', requiredPermission: 'view_ml', group: 'Monitoring', icon: '◍', label: 'Check Model Health', hint: 'Fetch source-aware model health.', call: () => api.modelHealth(), nextPage: 'ML Intelligence', resultTitle: 'Model health checked' },
  { id: 'check-jobs', requiredPermission: 'view_reports', group: 'Monitoring', icon: '▦', label: 'Check Scheduler Jobs', hint: 'Fetch job registry and history.', call: () => api.jobsHistory(), nextPage: 'Jobs Center', resultTitle: 'Scheduler jobs checked' },
  { id: 'check-alerts', requiredPermission: 'view_monitoring', group: 'Monitoring', icon: '!', label: 'Check Alerts', hint: 'Fetch monitoring and evidence alerts.', call: async () => ({ monitoring: await api.monitoringAlerts(), evidence: await api.evidenceAlerts().catch(() => null) }), nextPage: 'Monitoring', resultTitle: 'Alerts checked' },
];

const REPORT_ACTIONS = [
  { id: 'report-drift', group: 'Reports', icon: '≋', label: 'Open Latest Drift Report', hint: 'Navigate to drift monitoring and fetch report state.', page: 'Monitoring', call: () => api.monitoringDrift(), keywords: 'latest drift report' },
  { id: 'report-calibration', group: 'Reports', icon: '◍', label: 'Open Latest Calibration Report', hint: 'Navigate to ML calibration and fetch reliability report.', page: 'ML Intelligence', call: () => api.calibrationReport(), keywords: 'latest calibration report reliability' },
  { id: 'report-coverage', group: 'Reports', icon: '▤', label: 'Open Latest Coverage Report', hint: 'Navigate to Data Engine Ops and fetch coverage report.', page: 'Data Operations', call: () => api.flashscoreCoverage(), keywords: 'coverage report odds stats events' },
  { id: 'report-candidates', group: 'Reports', icon: '◇', label: 'Open Latest Decision Candidates', hint: 'Navigate to candidates and refresh current list.', page: 'Decision Engine', call: () => api.decisionEngineCandidates(), keywords: 'decision candidates latest' },
];

const UTILITY_ACTIONS = [
  { id: 'tour-replay', group: 'Workspace', icon: '?', label: 'Replay Product Tour', hint: 'Review the platform walkthrough.', type: 'tour', keywords: 'tour onboarding walkthrough help' },
  { id: 'shortcuts', group: 'Workspace', icon: '⌨', label: 'Keyboard Shortcuts', hint: 'Show navigation shortcuts.', type: 'shortcuts', keywords: 'keyboard shortcuts hotkeys help' },
];

const ALL_ACTIONS = [...NAV_ACTIONS, ...JOB_ACTIONS, ...CHECK_ACTIONS, ...REPORT_ACTIONS, ...UTILITY_ACTIONS];

function loadList(key) {
  try {
    const value = JSON.parse(window.localStorage.getItem(key) || '[]');
    return Array.isArray(value) ? value : [];
  } catch {
    return [];
  }
}

function saveList(key, values) {
  window.localStorage.setItem(key, JSON.stringify(values.slice(0, MAX_RECENTS)));
}

function fuzzyScore(action, query, favorites, recents) {
  const haystack = `${action.label} ${action.hint} ${action.group} ${action.keywords || ''} ${action.jobName || ''}`.toLowerCase();
  const q = query.trim().toLowerCase();
  let score = 0;
  if (favorites.includes(action.id)) score += 22;
  const recentIndex = recents.indexOf(action.id);
  if (recentIndex >= 0) score += 16 - recentIndex;
  if (!q) return score;
  if (haystack.includes(q)) score += 90;
  let cursor = 0;
  for (const char of q) {
    const idx = haystack.indexOf(char, cursor);
    if (idx === -1) return -1;
    score += 2;
    cursor = idx + 1;
  }
  return score;
}

function summarizePayload(payload) {
  if (!payload || typeof payload !== 'object') return 'Action completed.';
  const fields = [];
  const status = payload.status || payload.provider_health || payload.drift_level || payload.operational_status || payload.state;
  if (status) fields.push(`status: ${status}`);
  const count = payload.total ?? payload.count ?? payload.matches_saved ?? payload.candidates_count ?? payload.jobs?.length;
  if (count !== undefined) fields.push(`items: ${count}`);
  const warnings = payload.warnings?.length || payload.provider_warnings?.length || payload.alerts?.length;
  if (warnings) fields.push(`warnings: ${warnings}`);
  return fields.length ? fields.join(' · ') : 'Result received from API.';
}

export default function CommandPalette({ open, setOpen, setPage, onNotify, onReplayTour }) {
  const { user } = useApp();
  const userPermissions = new Set(user?.permissions || []);
  const userRole = String(user?.role || '').toLowerCase();
  const canUseAction = (action) => {
    if (userRole === 'admin' || userPermissions.has('view_all')) return true;
    if (action.jobName && userRole === 'viewer') return false;
    if (userRole === 'demo' && action.jobName && !['future_matches_pipeline','future_features','future_predictions','full_decision_pipeline','drift_monitoring','coverage_report'].includes(action.jobName)) return false;
    if (!action.requiredPermission) return true;
    return userPermissions.has(action.requiredPermission);
  };
  const [query, setQuery] = useState('');
  const [favorites, setFavorites] = useState(() => loadList(FAVORITES_KEY));
  const [recents, setRecents] = useState(() => loadList(RECENTS_KEY));
  const [selected, setSelected] = useState(0);
  const [confirmAction, setConfirmAction] = useState(null);
  const [activeOperation, setActiveOperation] = useState(null);
  const [lastResult, setLastResult] = useState(null);
  const [showShortcuts, setShowShortcuts] = useState(false);
  const inputRef = useRef(null);
  const runningRef = useRef(false);

  const items = useMemo(() => {
    const scored = ALL_ACTIONS.filter(canUseAction).map((action) => ({ action, score: fuzzyScore(action, query, favorites, recents) }))
      .filter((item) => item.score >= 0)
      .sort((a, b) => b.score - a.score || a.action.group.localeCompare(b.action.group) || a.action.label.localeCompare(b.action.label));
    return scored.map((item) => item.action);
  }, [query, favorites, recents, user]);

  const groupedItems = useMemo(() => {
    const groups = new Map();
    for (const item of items) {
      if (!groups.has(item.group)) groups.set(item.group, []);
      groups.get(item.group).push(item);
    }
    return Array.from(groups.entries());
  }, [items]);

  useEffect(() => {
    if (open) {
      setQuery('');
      setSelected(0);
      window.setTimeout(() => inputRef.current?.focus(), 40);
    }
  }, [open]);

  useEffect(() => {
    setSelected(0);
  }, [query]);

  useEffect(() => {
    if (!open) return;
    const onKey = (event) => {
      if (event.key === 'Escape') {
        if (confirmAction) setConfirmAction(null);
        else if (showShortcuts) setShowShortcuts(false);
        else setOpen(false);
        return;
      }
      if (confirmAction || showShortcuts) return;
      if (event.key === 'ArrowDown') {
        event.preventDefault();
        setSelected((index) => Math.min(index + 1, Math.max(items.length - 1, 0)));
      }
      if (event.key === 'ArrowUp') {
        event.preventDefault();
        setSelected((index) => Math.max(index - 1, 0));
      }
      if (event.key === 'Enter' && items[selected]) {
        event.preventDefault();
        void handleAction(items[selected]);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, items, selected, confirmAction, showShortcuts, setOpen]);

  function remember(action) {
    const next = [action.id, ...recents.filter((id) => id !== action.id)].slice(0, MAX_RECENTS);
    setRecents(next);
    saveList(RECENTS_KEY, next);
  }

  function toggleFavorite(event, action) {
    event.stopPropagation();
    const next = favorites.includes(action.id) ? favorites.filter((id) => id !== action.id) : [action.id, ...favorites].slice(0, MAX_RECENTS);
    setFavorites(next);
    saveList(FAVORITES_KEY, next);
  }

  async function runJobAction(action) {
    if (runningRef.current) {
      onNotify?.({ type: 'warning', title: 'Operation already running', message: 'Wait for the current command to finish before starting another one.' });
      return;
    }
    runningRef.current = true;
    const startedAt = Date.now();
    setActiveOperation({ label: action.label, status: 'running', jobName: action.jobName, startedAt });
    onNotify?.({ type: 'info', title: 'Pipeline started', message: `${action.label} queued safely.` });
    try {
      const result = await api.runJob(action.jobName);
      const duration = Math.max(1, Math.round((Date.now() - startedAt) / 1000));
      const jobId = result?.job_id || result?.id || result?.job?.id || action.jobName;
      setActiveOperation({ label: action.label, status: result?.status || 'completed', jobName: action.jobName, jobId, duration });
      setLastResult({ title: `${action.label} completed`, message: summarizePayload(result), page: action.nextPage, cta: action.successTarget });
      onNotify?.({ type: 'success', title: 'Operation completed', message: `${action.label} finished in ${duration}s.` });
      if (action.nextPage) setPage(action.nextPage);
    } catch (error) {
      setActiveOperation({ label: action.label, status: 'failed', jobName: action.jobName, error: error.message });
      onNotify?.({ type: 'error', title: 'Operation failed', message: error.message });
    } finally {
      runningRef.current = false;
    }
  }

  async function runCheckAction(action) {
    if (runningRef.current) {
      onNotify?.({ type: 'warning', title: 'Operation already running', message: 'Wait for the current command to finish before starting another one.' });
      return;
    }
    runningRef.current = true;
    setActiveOperation({ label: action.label, status: 'running' });
    try {
      const result = await action.call();
      setActiveOperation({ label: action.label, status: 'completed' });
      setLastResult({ title: action.resultTitle || `${action.label} completed`, message: summarizePayload(result), page: action.nextPage, cta: action.nextPage ? `Open ${action.nextPage}` : null });
      onNotify?.({ type: 'success', title: action.resultTitle || 'Command completed', message: summarizePayload(result) });
      if (action.nextPage) setPage(action.nextPage);
    } catch (error) {
      setActiveOperation({ label: action.label, status: 'failed', error: error.message });
      onNotify?.({ type: 'error', title: 'Command failed', message: error.message });
    } finally {
      runningRef.current = false;
    }
  }

  async function handleAction(action) {
    remember(action);
    if (action.type === 'navigation' || action.page) {
      setPage(action.page);
      onNotify?.({ type: 'success', title: 'Navigation', message: `${action.label.replace(/^Open /, '')} opened.` });
      if (action.call) {
        void runCheckAction({ ...action, nextPage: action.page, resultTitle: `${action.label.replace(/^Open /, '')} refreshed` });
      }
      setOpen(false);
      return;
    }
    if (action.type === 'tour') {
      onReplayTour?.();
      setOpen(false);
      return;
    }
    if (action.type === 'shortcuts') {
      setShowShortcuts(true);
      return;
    }
    if (action.jobName) {
      setConfirmAction(action);
      return;
    }
    if (action.call) {
      await runCheckAction(action);
    }
  }

  async function confirmRun() {
    const action = confirmAction;
    setConfirmAction(null);
    if (!action) return;
    await runJobAction(action);
  }

  if (!open) return null;
  return (
    <div className="command-backdrop" role="presentation" onMouseDown={() => setOpen(false)}>
      <section className="command-palette operational-command" role="dialog" aria-modal="true" aria-label="Command Palette" onMouseDown={(event) => event.stopPropagation()}>
        <div className="command-input-row">
          <span>⌘K</span>
          <input ref={inputRef} value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Run jobs, open reports, check health, search features..." />
          <button className="shortcut-trigger" type="button" onClick={() => setShowShortcuts(true)}>Shortcuts</button>
        </div>

        {activeOperation && (
          <div className={`command-operation operation-${activeOperation.status}`}>
            <span className="operation-spinner" />
            <div><b>{activeOperation.label}</b><small>{activeOperation.status}{activeOperation.duration ? ` · ${activeOperation.duration}s` : ''}{activeOperation.jobId ? ` · ${activeOperation.jobId}` : ''}</small></div>
          </div>
        )}

        {lastResult && (
          <div className="command-result-card">
            <div><b>{lastResult.title}</b><small>{lastResult.message}</small></div>
            {lastResult.page && <button type="button" onClick={() => { setPage(lastResult.page); setOpen(false); }}>{lastResult.cta || 'Open'}</button>}
          </div>
        )}

        <div className="command-list command-list-operational">
          {groupedItems.length === 0 && (
            <div className="command-empty"><b>No command found</b><small>Try “drift”, “pipeline”, “calibration”, “health” or “candidates”.</small></div>
          )}
          {groupedItems.map(([group, groupItems]) => (
            <div className="command-group" key={group}>
              <div className="command-group-title">{group}</div>
              {groupItems.map((item) => {
                const globalIndex = items.findIndex((entry) => entry.id === item.id);
                const active = globalIndex === selected;
                return (
                  <button key={item.id} type="button" className={active ? 'selected' : ''} onMouseEnter={() => setSelected(globalIndex)} onClick={() => { void handleAction(item); }}>
                    <span className={`command-orb ${item.jobName ? 'job' : ''}`}>{item.icon}</span>
                    <span><b>{item.label}</b><small>{item.hint}</small></span>
                    <span className="command-meta">
                      <button type="button" className={`favorite-command ${favorites.includes(item.id) ? 'active' : ''}`} aria-label="Favorite command" onClick={(event) => toggleFavorite(event, item)}>★</button>
                      <kbd>{item.shortcut || (item.jobName ? 'RUN' : 'API')}</kbd>
                    </span>
                  </button>
                );
              })}
            </div>
          ))}
        </div>

        {confirmAction && (
          <div className="command-confirm" role="alertdialog" aria-modal="true">
            <div className="confirm-panel">
              <span className="confirm-icon">⚡</span>
              <h3>{confirmAction.label}?</h3>
              <p>{confirmAction.hint}</p>
              <small>Safe execution: backend locking is respected, no destructive action is exposed, and this stays in PAPER_TRADING_SIMULATION_ONLY operations.</small>
              <div>
                <button type="button" onClick={() => setConfirmAction(null)}>Cancel</button>
                <button type="button" className="run" onClick={() => { void confirmRun(); }}>Run Pipeline</button>
              </div>
            </div>
          </div>
        )}

        {showShortcuts && (
          <div className="command-confirm" role="dialog" aria-modal="true">
            <div className="confirm-panel shortcuts-panel">
              <h3>Keyboard Shortcuts</h3>
              <div className="shortcut-grid">
                {[['CMD/CTRL + K', 'Open command palette'], ['G + D', 'Dashboard'], ['G + M', 'Monitoring'], ['G + C', 'Decision Candidates'], ['G + R', 'Reports / System Status'], ['G + P', 'Pipelines / Jobs']].map(([keys, label]) => (
                  <div key={keys}><kbd>{keys}</kbd><span>{label}</span></div>
                ))}
              </div>
              <div><button type="button" className="run" onClick={() => setShowShortcuts(false)}>Close</button></div>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
