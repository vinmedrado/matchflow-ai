const signals = [
  ['Data Engine', 'heartbeat', 'healthy'],
  ['ML Calibration', 'watching', 'stable'],
  ['Drift Monitor', 'streaming', 'low'],
  ['Decision Queue', 'paper only', 'safe'],
];

export default function LiveOpsStrip({ openPalette, replayTour }) {
  return (
    <div className="live-ops-strip">
      <div className="live-ops-left">
        <span className="operational-heartbeat" />
        <b>Live Operational Feel</b>
        <small>Demo activity is always marked; no automatic real action.</small>
      </div>
      <div className="live-ops-signals">
        {signals.map(([label, value, status]) => <span key={label}><i />{label}<b>{value}</b><em>{status}</em></span>)}
      </div>
      <div className="live-ops-actions">
        <button type="button" onClick={openPalette}>⌘K</button>
        <button type="button" onClick={replayTour}>Tour</button>
      </div>
    </div>
  );
}
