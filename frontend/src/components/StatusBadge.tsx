export function StatusBadge({status}: {status: string}) { return <span className={`status status-${status.toLowerCase()}`}>{status.replaceAll('_', ' ')}</span> }

