/**
 * TypeScript type definitions for the application
 */

export interface TranscriptionMessage {
  type: "connected" | "transcription" | "error" | "stats" | "pong" | "control_ack";
  text?: string;
  is_final?: boolean;
  confidence?: number;
  processing_time_ms?: number;
  raw_text?: string;
  timestamp?: string;
  message?: string;
  code?: string;
  config?: {
    expected_sample_rate: number;
    expected_format: string;
    chunk_duration: number;
  };
  data?: Record<string, any>;
}

export interface Macro {
  id: string;
  trigger: string;
  expansion: string;
  category: string;
}

export interface Session {
  id: string;
  title: string;
  content: string;
  plainText: string;
  wordCount: number;
  duration?: number;
  createdAt: string;
  updatedAt?: string;
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
    medicalFormatting: boolean;
  };
  editor: {
    fontSize: number;
    fontFamily: string;
    darkMode: boolean;
    showCommandNotifications: boolean;
  };
}

export interface VoiceCommand {
  type: 'punctuation' | 'format' | 'action' | 'control';
  value?: string;
  action?: string;
}

export interface ProcessedResult {
  text: string;
  commands: VoiceCommand[];
  wasCommand: boolean;
  isMacro?: boolean;
}
