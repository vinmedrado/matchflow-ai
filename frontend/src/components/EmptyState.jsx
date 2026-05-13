export default function EmptyState({ message = 'No data available yet', detail = 'Run the pipeline or refresh the operational source to populate this panel.' }) {
  return (
    <div className="empty empty-premium">
      <div className="empty-orb" aria-hidden="true" />
      <strong>{message}</strong>
      <span>{detail}</span>
    </div>
  );
}
