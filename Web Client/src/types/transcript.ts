export interface TranscriptSegment {
  segmentId: number;
  text: string;
  timestamp?: number;
}

export interface RealtimePreviewState {
  text: string;
  segmentId: number | null;
  queueDelayMs: number;
  inferenceMs: number;
  latencyMs: number;
}

export interface ExportOptions {
  format: "txt" | "md";
  text: string;
}
