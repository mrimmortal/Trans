import type { RealtimePreviewState } from "../types/transcript";

interface Props {
  preview: RealtimePreviewState;
}

export function RealtimePreview({ preview }: Props) {
  if (!preview.text) {
    return null;
  }

  return (
    <div className="panel realtime-preview">
      <h2>Realtime Preview</h2>
      <div className="realtime-text">{preview.text}</div>
      <div className="realtime-meta">
        {preview.segmentId !== null && (
          <span className="meta-item">Segment {preview.segmentId}</span>
        )}
        {preview.queueDelayMs > 0 && (
          <span className="meta-item">Queue {preview.queueDelayMs.toFixed(0)}ms</span>
        )}
        {preview.inferenceMs > 0 && (
          <span className="meta-item">Infer {preview.inferenceMs.toFixed(0)}ms</span>
        )}
        {preview.latencyMs > 0 && (
          <span className="meta-item">Latency {preview.latencyMs.toFixed(0)}ms</span>
        )}
      </div>
    </div>
  );
}
