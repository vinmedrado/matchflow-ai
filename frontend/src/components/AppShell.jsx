import { useEffect, useRef, useState } from 'react';
import Topbar from './Topbar.jsx';
import NavigationHub from './NavigationHub.jsx';
import CommandPalette from './CommandPalette.jsx';
import CinematicOnboarding from './CinematicOnboarding.jsx';
import PremiumToasts from './PremiumToasts.jsx';
import LiveOpsStrip from './LiveOpsStrip.jsx';

const SHORTCUTS = {
  d: 'Dashboard',
  m: 'Monitoring',
  c: 'Decision Engine',
  r: 'System Status',
  o: 'Data Operations',
  l: 'ML Intelligence',
  j: 'Jobs Center',
  x: 'Demo Mode',
  p: 'Jobs Center',
};

export default function AppShell({ page, setPage, children }) {
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [tourOpen, setTourOpen] = useState(false);
  const [toasts, setToasts] = useState([]);
  const sequenceRef = useRef('');

  function notify(toast) {
    const id = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
    setToasts((items) => [...items.slice(-2), { id, ...toast }]);
    window.setTimeout(() => setToasts((items) => items.filter((item) => item.id !== id)), 5600);
  }

  useEffect(() => {
    const seen = window.localStorage.getItem('matchflow_ai_onboarding_seen');
    if (!seen) setTourOpen(true);
  }, []);

  useEffect(() => {
    const onKey = (event) => {
      const target = event.target;
      const typing = target && ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName);
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        setPaletteOpen((open) => !open);
        return;
      }
      if (typing || event.metaKey || event.ctrlKey || event.altKey) return;
      const key = event.key.toLowerCase();
      if (key === 'g') {
        sequenceRef.current = 'g';
        window.setTimeout(() => { sequenceRef.current = ''; }, 900);
        return;
      }
      if (sequenceRef.current === 'g' && SHORTCUTS[key]) {
        setPage(SHORTCUTS[key]);
        notify({ type: 'success', title: 'Keyboard navigation', message: `Opened ${SHORTCUTS[key]} with G+${key.toUpperCase()}.` });
        sequenceRef.current = '';
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [setPage]);

  function closeTour() {
    window.localStorage.setItem('matchflow_ai_onboarding_seen', 'true');
    setTourOpen(false);
    notify({ type: 'success', title: 'Workspace ready', message: 'Onboarding completed. Use CMD/CTRL+K anytime.' });
  }

  return (
    <div className="premium-shell">
      <Topbar page={page} />
      <div className="premium-shell-inner">
        <NavigationHub page={page} setPage={setPage} />
        <main className="premium-main">
          <LiveOpsStrip openPalette={() => setPaletteOpen(true)} replayTour={() => setTourOpen(true)} />
          <div className="content premium-content">{children}</div>
        </main>
      </div>
      <CommandPalette open={paletteOpen} setOpen={setPaletteOpen} setPage={setPage} onNotify={notify} onReplayTour={() => setTourOpen(true)} />
      <CinematicOnboarding open={tourOpen} onClose={closeTour} />
      <PremiumToasts toasts={toasts} dismiss={(id) => setToasts((items) => items.filter((item) => item.id !== id))} />
    </div>
  );
}
