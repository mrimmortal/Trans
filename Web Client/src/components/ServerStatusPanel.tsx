import type { ServerStatusState } from "../hooks/useTranscriptionSession";

interface Props {
  status: ServerStatusState;
}

interface StatusRow {
  label: string;
  value: string | number | boolean;
}

export function ServerStatusPanel({ status }: Props) {
  const rows: StatusRow[] = [
    { label: "Session", value: status.sessionId || "--" },
    { label: "State", value: status.state || "--" },
    { label: "Model", value: status.model || "--" },
    { label: "Realtime", value: status.realtimeModel || "--" },
    { label: "Engine", value: status.engine || "--" },
    { label: "Device", value: status.device || "--" },
    { label: "Queue Depth", value: status.queueDepth.toFixed(2) },
    { label: "Active Sessions", value: status.activeSessions },
    { label: "Active Speakers", value: status.activeSpeakers },
    { label: "Wake Word", value: status.wakeWordEnabled ? "Enabled" : "Disabled" },
  ];

  return (
    <div className="panel server-status-panel">
      <h2>Server Status</h2>
      <div className="kv-list">
        {rows.map((row) => (
          <div key={row.label} className="kv-row">
            <span className="kv-label">{row.label}</span>
            <span className="kv-value">{String(row.value)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
