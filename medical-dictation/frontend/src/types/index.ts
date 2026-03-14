// types/index.ts

export interface VoiceCommand {
  type: string;
  action: string;
  original_text: string;
  replacement: string;
}

export interface TranscriptionMessage {
  type: 'connected' | 'transcription' | 'error' | 'pong' | 'stats' | 'control_ack' | 'available_commands' | 'command_history';
  message?: string;
  config?: ServerConfig;
  text?: string;
  is_final?: boolean;
  confidence?: number;
  processing_time_ms?: number;
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
  templates: string[];
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