import type { ConnectionState } from "../types/websocket-contract";

interface Props {
  connectionState: ConnectionState;
  hasContent: boolean;
  onStart: () => void;
  onStop: () => void;
  onClear: () => void;
}

export function TranscriptionControls({
  connectionState,
  hasContent,
  onStart,
  onStop,
  onClear,
}: Props) {
  const canStart = connectionState === "READY";
  const canStop =
    connectionState === "STREAMING" || connectionState === "STOPPING";
  const canClear = hasContent;

  return (
    <div className="panel">
      <h2>Controls</h2>
      <div className="control-stack">
        <button
          className={`primary ${canStop ? "active" : ""}`}
          type="button"
          onClick={canStop ? onStop : canStart ? onStart : undefined}
          disabled={!canStart && !canStop}
        >
          {canStop ? "Stop Transcription" : "Start Transcription"}
        </button>
        <button
          className="secondary"
          type="button"
          onClick={onClear}
          disabled={!canClear}
        >
          Clear Transcript
        </button>
      </div>
    </div>
  );
}
