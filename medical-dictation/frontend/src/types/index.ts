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
