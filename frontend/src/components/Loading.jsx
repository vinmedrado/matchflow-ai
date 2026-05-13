import logo from '../assets/brand/matchflow-ai-logo.jpeg';

export default function Loading({ label = 'Loading MatchFlow intelligence...' }) {
  return (
    <div className="loading loading-premium" role="status" aria-live="polite">
      <img src={logo} alt="MatchFlow AI" />
      <div className="loading-grid" aria-hidden="true"><span /><span /><span /></div>
      <strong>{label}</strong>
      <small>Data pulse · AI scanning · Paper mode</small>
    </div>
  );
}
