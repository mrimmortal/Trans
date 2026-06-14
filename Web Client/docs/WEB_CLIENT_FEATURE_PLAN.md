# Web Client Feature Plan

## Purpose

A standalone web transcription editor that consumes the CoreSTT WebSocket API
(`/ws/transcribe`) following `docs/WEBSOCKET_CLIENT_CONTRACT.md`.

## Architecture

```
src/
  main.tsx                  Entry point
  App.tsx                   Layout composition

  config/
    defaults.ts             Default WS URL, ping interval, localStorage keys

  types/
    websocket-contract.ts   TypeScript interfaces for all server/client messages
    transcript.ts           TranscriptSegment, RealtimePreviewState, ExportOptions

  services/
    websocketClient.ts      Browser WebSocket wrapper
    audioCapture.ts         Microphone capture via getUserMedia
    audioPacketEncoder.ts   Float32→Int16 conversion and binary packet encoding
    transcriptStorage.ts    localStorage persistence for WS URL and draft

  hooks/
    useTranscriptionSession.ts  State machine, connection, streaming, event log

  components/
    ConnectionPanel.tsx     URL input, connect/disconnect, connection state, latency
    TranscriptionControls.tsx   Start/Stop/Clear with state-driven disabled logic
    RealtimePreview.tsx     Interim text display with segment ID and timing
    TranscriptEditor.tsx    Editable textarea with word/char count, autosave
    TranscriptToolbar.tsx   Copy, Export .txt, Export .md
    EventLog.tsx            Scrollable event history with type coloring
    ServerStatusPanel.tsx   Server config and session status display

  styles/
    app.css                 Dark theme CSS
```

## State Machine

```
DISCONNECTED → CONNECTING → CONNECTED → READY → STREAMING → STOPPING → READY
                                                              ↓
                                                           CLOSED → DISCONNECTED
ERROR → DISCONNECTED
```

## Component Responsibilities

### ConnectionPanel
- WebSocket URL text input (editable when disconnected)
- Connect button (disabled while connecting)
- Disconnect button (visible when connected)
- Connection state chip
- Latency chip

### TranscriptionControls
- Start button (enabled when READY)
- Stop button (enabled when STREAMING/STOPPING)
- Clear button (enabled when transcript is non-empty)

### RealtimePreview
- Shows latest `realtime` message text
- Shows segmentId, queueDelayMs, inferenceMs, latencyMs
- Hidden when no realtime text

### TranscriptEditor
- Plain textarea (v1 choice over contenteditable)
- Final segments appended with newline separator
- Manual edits never overwritten by realtime
- Word count and character count
- Autosave to localStorage (500ms debounce)

### TranscriptToolbar
- Copy to clipboard
- Export as .txt (plain text)
- Export as .md (`# Transcript\n\n<text>`)

### EventLog
- Scrollable list of recent events (max 200)
- Type-based color coding (green/amber/red/cyan/gray)
- Events: connected, disconnected, hello, ready, realtime, final, warning, error, pong, timeline, clear, start_sent, stop_sent, mic_error, ws_error, etc.

### ServerStatusPanel
- Displays from server messages: sessionId, model, realtimeModel, engine, device, queueDepth, state, activeSessions, activeSpeakers, wakeWordEnabled

## Key Design Decisions

1. No heavy editor libraries — plain textarea is sufficient for v1
2. Real-time preview and editor are separate state — realtime never touches editor
3. Final segments append only — no in-place editing of existing text
4. localStorage autosave with debounce (500ms)
5. beforeunload warning when transcript is non-empty
6. Little-endian packet encoding via DataView.setUint32(..., true)
7. AudioWorklet with ScriptProcessor fallback for maximum browser compatibility
8. Minimal dependencies — only React, Vite, TypeScript

## Future Improvements

- Contenteditable editor with per-segment formatting
- Automatic reconnection with exponential backoff
- Audio visualizer
- Wake-word configuration UI
- Multiple session tabs
- Dark/light theme toggle
- Keyboard shortcuts
