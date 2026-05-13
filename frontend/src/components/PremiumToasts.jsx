export default function PremiumToasts({ toasts = [], dismiss }) {
  return (
    <div className="toast-stack" aria-live="polite">
      {toasts.map((toast) => (
        <article key={toast.id} className={`premium-toast toast-${toast.type || 'info'}`}>
          <button type="button" onClick={() => dismiss?.(toast.id)} aria-label="Dismiss notification">×</button>
          <span className="toast-pulse" />
          <div><b>{toast.title}</b><small>{toast.message}</small></div>
        </article>
      ))}
    </div>
  );
}
