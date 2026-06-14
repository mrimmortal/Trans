import type { ConnectionState } from "../types/websocket-contract";

interface Props {
  wsUrl: string;
  connectionState: ConnectionState;
  latency: number;
  onUrlChange: (url: string) => void;
  onConnect: () => void;
  onDisconnect: () => void;
}

const STATE_LABELS: Record<ConnectionState, string> = {
  DISCONNECTED: "Disconnected",
  CONNECTING: "Connecting",
  CONNECTED: "Connected",
  READY: "Ready",
  STREAMING: "Streaming",
  STOPPING: "Stopping",
  CLOSED: "Closed",
  ERROR: "Error",
};

export function ConnectionPanel({
  wsUrl,
  connectionState,
  latency,
  onUrlChange,
  onConnect,
  onDisconnect,
}: Props) {
  const isConnected =
    connectionState === "CONNECTED" ||
    connectionState === "READY" ||
    connectionState === "STREAMING" ||
    connectionState === "STOPPING";

  const canConnect =
    connectionState === "DISCONNECTED" ||
    connectionState === "ERROR" ||
    connectionState === "CLOSED";
  const isConnecting = connectionState === "CONNECTING";

  return (
    <div className="panel">
      <h2>Connection</h2>
      <div className="control-stack">
        <label className="input-label">
          WebSocket URL
          <input
            type="text"
            className="text-input"
            value={wsUrl}
            onChange={(e) => onUrlChange(e.target.value)}
            disabled={!canConnect}
            placeholder="ws://127.0.0.1:8020/ws/transcribe"
          />
        </label>
        <div className="button-row">
          {canConnect ? (
            <button
              className="primary"
              type="button"
              onClick={onConnect}
              disabled={isConnecting}
            >
              {isConnecting ? "Connecting..." : "Connect"}
            </button>
          ) : (
            <button
              className="secondary danger"
              type="button"
              onClick={onDisconnect}
            >
              Disconnect
            </button>
          )}
        </div>
        <div className="status-chips">
          <span className="chip">
            <span
              className={`dot ${
                isConnected
                  ? "green"
                  : connectionState === "CONNECTING"
                    ? "amber"
                    : "gray"
              }`}
            />
            {STATE_LABELS[connectionState]}
          </span>
          <span className="chip">
            <span className="dot gray" />
            {latency} ms
          </span>
        </div>
      </div>
    </div>
  );
}
