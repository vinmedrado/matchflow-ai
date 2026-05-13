export default function StatusBadge({ok,label}){return <span className={ok?'badge ok':'badge bad'}>{label}: {ok?'OK':'OFF'}</span>}
