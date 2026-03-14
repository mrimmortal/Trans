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

// ═══════════════════════════════════════════════════════════════
// TEMPLATE TYPES (SQLite backend based)
// ═══════════════════════════════════════════════════════════════

export interface Template {
  id: number;
  name: string;
  trigger_phrases: string[];
  content: string;
  category: string;
  description: string;
  author: string;
  created_at: string;
  updated_at: string;
  is_active: boolean;
}

export interface TemplateCreate {
  name: string;
  trigger_phrases: string[];
  content: string;
  category?: string;
  description?: string;
  author?: string;
}

export interface TemplateUpdate {
  trigger_phrases?: string[];
  content?: string;
  category?: string;
  description?: string;
  author?: string;
}

export interface TemplateListResponse {
  templates: Template[];
  total: number;
  categories: string[];
}

export interface TemplateTestResponse {
  original_text: string;
  processed_text: string;
  commands_executed: CommandExecuted[];
}

export interface CommandExecuted {
  type: string;
  action: string;
  original_text: string;
  replacement?: string;
  replacement_preview?: string;
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
    | 'command_history'
    | 'templates_list';
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
  templates?: TemplateListItem[];
}

export interface TemplateListItem {
  name: string;
  trigger_phrases: string[];
  category: string;
  description: string;
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