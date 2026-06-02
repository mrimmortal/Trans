// types/index.ts

// ═══════════════════════════════════════════════════════════════
// MACRO TYPES (localStorage based)
// ═══════════════════════════════════════════════════════════════

export interface Macro {
  id: string;
  name?: string;
  trigger: string;
  text: string;
  category?: string;
}

export interface AppSettings {
  audio: {
    deviceId: string;
    noiseSuppression: boolean;
    echoCancellation: boolean;
    autoGainControl: boolean;
    silenceSensitivity: number;
  };
  transcription: {
    language: string;
    autoPunctuation: boolean;
    domainFormatting: boolean;
  };
  editor: {
    fontSize: number;
    fontFamily: string;
    darkMode: boolean;
    showCommandNotifications: boolean;
  };
}

// ═══════════════════════════════════════════════════════════════
// VOICE COMMAND TYPES
// ═══════════════════════════════════════════════════════════════

export interface VoiceCommand {
  type: string;
  action: string;
  original_text: string;
  replacement: string;
}

export interface ProcessedCommand {
  type: 'punctuation' | 'format' | 'action' | 'control';
  value?: string;
  action?: string;
}

export interface ProcessedResult {
  text: string;
  commands: ProcessedCommand[];
  wasCommand: boolean;
  isMacro?: boolean;
}

// ═══════════════════════════════════════════════════════════════
// WEBSOCKET TYPES
// ═══════════════════════════════════════════════════════════════

export interface TranscriptionMessage {
  type:
    | 'connected'
    | 'transcription'
    | 'error'
    | 'pong'
    | 'stats'
    | 'control_ack'
    | 'available_commands'
    | 'command_history';
  message?: string;
  config?: ServerConfig;
  text?: string;
  domain?: string;
  is_final?: boolean;
  confidence?: number;
  processing_time_ms?: number;
  audio_duration_seconds?: number;
  real_time_factor?: number;
  flush_reason?: string;
  timestamp?: number | string;
  commands?: VoiceCommand[];
  code?: string;
  data?: SessionStats;
  action?: string;
  commands_list?: AvailableCommands;
  history?: CommandHistoryItem[];
}

export interface ServerConfig {
  sample_rate: number;
  channels: number;
  sample_width: number;
  min_chunk_bytes: number;
  max_chunk_bytes: number;
  overlap_bytes: number;
  model: string;
  device: string;
  language?: string;
  accent_support_enabled?: boolean;
  domain?: string;
  available_domains?: string[];
  vad_enabled: boolean;
  commands_enabled?: boolean;
  available_commands?: AvailableCommands;
}

export interface SessionStats {
  session_duration_seconds: number;
  audio_duration_seconds: number;
  audio_received_bytes: number;
  chunks_received: number;
  transcriptions_count: number;
  total_words: number;
  buffer_size_bytes: number;
  silence_chunks_skipped: number;
  efficiency_percent: number;
  commands_executed?: number;
}

export interface AvailableCommands {
  punctuation: string[];
  formatting: string[];
  editing: string[];
  navigation: string[];
  control: string[];
  custom: string[];
}

export interface CommandHistoryItem {
  type: string;
  action: string;
  original_text: string;
}

export interface CustomCommandRegistration {
  pattern: string;
  replacement: string;
  action?: string;
}

// ═══════════════════════════════════════════════════════════════
// LOCAL ASSISTANT TYPES
// ═══════════════════════════════════════════════════════════════

export interface LLMRespondRequest {
  text: string;
  system_prompt?: string;
}

export interface LLMRespondResponse {
  response: string;
  model: string;
  provider: string;
  request_id?: string;
}

export type AssistantApiErrorCode = 'LM_STUDIO_UNAVAILABLE' | 'REQUEST_FAILED';

export interface TTSSynthesizeRequest {
  text: string;
  voice?: string;
  lang?: string;
}

export type TTSApiErrorCode = 'TTS_UNAVAILABLE' | 'REQUEST_FAILED';

export interface TTSSynthesizeResult {
  audioUrl: string;
  request_id?: string;
}

export type LocalAssistantErrorCode =
  | 'LM_STUDIO_UNAVAILABLE'
  | 'TTS_UNAVAILABLE'
  | 'REQUEST_FAILED';

export type AssistantStage = 'idle' | 'generating-response' | 'generating-speech' | 'playing';

export interface SttMetrics {
  model_size?: string;
  device?: string;
  compute_type?: string;
  vad_enabled?: boolean;
  sample_rate?: number;
  channels?: number;
  chunks_received?: number;
  silence_chunks_skipped?: number;
  silence_skipped_percent?: number;
  transcriptions_count?: number;
  empty_transcription_count?: number;
  last_audio_duration_seconds?: number;
  last_processing_time_ms?: number;
  last_real_time_factor?: number;
  last_flush_reason?: string;
  average_processing_time_ms?: number;
  average_real_time_factor?: number;
}

export interface SafeSttSettings {
  transcription_profile?: string;
  model_size?: string;
  device?: string;
  compute_type?: string;
  language?: string;
  sample_rate?: number;
  channels?: number;
  sample_width?: number;
  min_chunk_duration_seconds?: number;
  max_chunk_duration_seconds?: number;
  overlap_duration_seconds?: number;
  silence_timeout_seconds?: number;
  beam_size?: number;
  temperature?: number[];
  compression_ratio_threshold?: number;
  log_prob_threshold?: number;
  no_speech_threshold?: number;
  min_transcription_confidence?: number;
  hallucination_max_no_speech_prob?: number;
  vad_filter?: boolean;
  vad_parameters?: {
    threshold?: number;
    min_speech_duration_ms?: number;
    max_speech_duration_s?: number;
    min_silence_duration_ms?: number;
    speech_pad_ms?: number;
  };
  hallucination_silence_threshold_enabled?: boolean;
}

export interface BackendConfigResponse {
  audio?: {
    sample_rate?: number;
    channels?: number;
    sample_width?: number;
    min_chunk_duration_seconds?: number;
    max_chunk_duration_seconds?: number;
    overlap_duration_seconds?: number;
    min_chunk_bytes?: number;
    max_chunk_bytes?: number;
    overlap_bytes?: number;
  };
  model?: {
    size?: string;
    device?: string;
    compute_type?: string;
    language?: string;
    accent_support_enabled?: boolean;
  };
  stt?: SafeSttSettings;
  domains?: {
    default?: string;
    available?: string[];
  };
  vad_enabled?: boolean;
}

export interface ProviderDiagnostics {
  status: 'healthy' | 'degraded' | 'unhealthy';
  provider?: string;
  configured?: boolean;
  loaded?: boolean;
  reachable?: boolean;
  available?: boolean;
  model?: string;
  model_size?: string;
  device?: string;
  compute_type?: string;
  transcription_profile?: string;
  vad_enabled?: boolean;
  last_error?: string | null;
  settings?: SafeSttSettings;
  metrics?: SttMetrics;
}

export interface DiagnosticsResponse {
  status?: 'healthy' | 'degraded' | 'unhealthy';
  request_id: string;
  backend?: {
    status: 'healthy' | 'degraded' | 'unhealthy';
    service: string;
    environment: string;
  };
  stt?: ProviderDiagnostics;
  llm?: ProviderDiagnostics;
  tts?: ProviderDiagnostics;
}
