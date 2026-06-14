export type ConnectionState =
  | "DISCONNECTED"
  | "CONNECTING"
  | "CONNECTED"
  | "READY"
  | "STREAMING"
  | "STOPPING"
  | "CLOSED"
  | "ERROR";

export type ClientCommandType = "start" | "stop" | "clear" | "ping" | "metrics";

export interface ClientCommand {
  type: ClientCommandType;
}

export interface AudioMetadata {
  sampleRate: number;
  channels: number;
  format: string;
  frames?: number;
  sentAt?: number;
  clientPlatform?: string;
  clientProtocolVersion?: string;
  sequence?: number;
}

export interface HelloMessage {
  type: "hello";
  clientId?: string;
  sessionId?: string;
  settings?: Record<string, unknown>;
  limits?: Record<string, unknown>;
  supportedEngines?: string[];
  runtimeSettings?: Record<string, unknown>;
}

export interface ReadyMessage {
  type: "ready";
  sessionId?: string;
  ok?: boolean;
  settings?: Record<string, unknown>;
  limits?: Record<string, unknown>;
  runtimeSettings?: Record<string, unknown>;
}

export interface StatusMessage {
  type: "status";
  sessionId?: string;
  state?: string;
  activeClientId?: string | null;
  queueDepth?: number;
  droppedChunks?: number;
  coalescedRealtime?: number;
  staleRealtimeDiscarded?: number;
  activeSessions?: number;
  activeSpeakers?: number;
  wakeWordEnabled?: boolean;
}

export interface RealtimeMessage {
  type: "realtime";
  sessionId?: string;
  segmentId?: number;
  sequence?: number;
  text?: string;
  displayText?: string;
  stableText?: string;
  unstableText?: string;
  timestamp?: number;
  timestampIso?: string;
  queueDelayMs?: number;
  inferenceMs?: number;
  latencyMs?: number;
}

export interface FinalMessage {
  type: "final";
  sessionId?: string;
  segmentId?: number;
  text?: string;
  timestamp?: number;
  timestampIso?: string;
  queueDelayMs?: number;
  inferenceMs?: number;
  latencyMs?: number;
}

export interface TimelineMessage {
  type: "timeline";
  sessionId?: string;
  event?: string;
  segmentId?: number;
  timestamp?: number;
  timestampIso?: string;
}

export interface ClearMessage {
  type: "clear";
  sessionId?: string;
}

export interface WarningMessage {
  type: "warning";
  sessionId?: string;
  message?: string;
}

export interface ErrorMessage {
  type: "error";
  sessionId?: string;
  where?: string;
  message?: string;
}

export interface PongMessage {
  type: "pong";
  sessionId?: string;
  serverTime?: number;
}

export interface MetricsMessage {
  type: "metrics";
  sessionId?: string;
  metrics?: Record<string, unknown>;
}

export type ServerMessage =
  | HelloMessage
  | ReadyMessage
  | StatusMessage
  | RealtimeMessage
  | FinalMessage
  | TimelineMessage
  | ClearMessage
  | WarningMessage
  | ErrorMessage
  | PongMessage
  | MetricsMessage;

export type ServerMessageHandler = (message: ServerMessage) => void;

export type EventType =
  | "connected"
  | "disconnected"
  | "hello"
  | "ready"
  | "status"
  | "realtime"
  | "final"
  | "timeline"
  | "clear"
  | "warning"
  | "error"
  | "pong"
  | "metrics"
  | "start"
  | "stop"
  | "start_sent"
  | "stop_sent"
  | "clear_sent"
  | "ping_sent"
  | "metrics_sent"
  | "mic_permission_denied"
  | "mic_error"
  | "ws_error"
  | "ws_closed";
