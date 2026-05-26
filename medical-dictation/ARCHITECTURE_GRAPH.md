# Architecture Graph: Transcription Template

This file is for AI agents and maintainers. It keeps future changes aligned with the vanilla transcription template.

## System Graph

```mermaid
flowchart LR
  User[User]

  subgraph Frontend["Frontend: Next.js + React"]
    Page["src/app/page.tsx\nMain coordinator"]
    AppConfig["src/lib/appConfig.ts\nBranding, storage keys, wrapper toggles"]
    Constants["src/lib/constants.ts\nAPI_URL / WS_URL / audio constants"]
    Recorder["src/hooks/useAudioRecorder.ts\nMicrophone -> PCM chunks"]
    WS["src/hooks/useWebSocket.ts\nWebSocket client"]
    VoiceCommands["src/hooks/useVoiceCommands.ts\nLocal commands + snippets"]
    Editor["src/components/Editor/DictationEditor.tsx\nTipTap editor"]
    Sidebar["src/components/Sidebar/*\nSnippets / history"]
    LocalStorage[("Browser localStorage\nsnippets / sessions / settings / autosave")]
  end

  subgraph Backend["Backend: FastAPI"]
    App["backend/app/main.py\nFastAPI app + /ws/audio"]
    Handler["AudioStreamHandler\nVAD buffering + flush"]
    Config["backend/app/audio_config.py\nAudio/model/server config"]
    Engine["services/transcription_engine.py\nSilero VAD + Faster-Whisper"]
    Domains["domains/*\nGeneral adapter + wrapper seam"]
    Commands["services/command_processor.py\nReusable command parser"]
  end

  User --> Page
  Page --> AppConfig
  Page --> Recorder
  Page --> WS
  Page --> VoiceCommands
  Page --> Editor
  Page --> Sidebar
  Page --> LocalStorage
  Sidebar --> LocalStorage
  Constants --> Page
  Constants --> WS

  Recorder -- "binary PCM audio chunks" --> WS
  WS -- "ws://.../ws/audio" --> App
  App --> Handler
  Handler --> Config
  Handler --> Engine
  Handler --> Domains
  Domains --> Commands
  Engine --> Config
  App -- "JSON transcription events" --> WS
  WS --> Page
  VoiceCommands --> Editor
  Page --> Editor
```

## Runtime Sequence

```mermaid
sequenceDiagram
  participant U as User
  participant P as page.tsx
  participant R as useAudioRecorder
  participant W as useWebSocket
  participant B as FastAPI /ws/audio
  participant H as AudioStreamHandler
  participant E as TranscriptionEngine
  participant D as DomainAdapter
  participant T as TipTap Editor

  U->>P: Click record
  P->>W: connect()
  W->>B: WebSocket open /ws/audio
  B-->>W: { type: "connected", config }
  P->>R: startRecording()
  R->>W: onAudioData(ArrayBuffer)
  W->>B: binary PCM chunk
  B->>H: add_audio_chunk(bytes)
  H->>E: detect_speech(bytes)
  H-->>H: buffer speech, skip silence
  H->>E: transcribe_audio_bytes(buffer)
  E-->>H: raw text
  H->>D: process_transcript(text)
  D-->>H: vanilla text, no commands
  B-->>W: { type: "transcription", text, domain, commands }
  W-->>P: lastTranscription / lastCommands
  P->>T: insert processed text
```

## Protocol Facts

WebSocket endpoint:

```text
/ws/audio
```

Client to server:

```text
Binary message: raw 16-bit PCM audio, 16 kHz, mono
Text message: JSON control command
```

Common client JSON control messages:

```json
{ "type": "ping" }
{ "type": "flush" }
{ "type": "reset" }
{ "type": "stats" }
{ "type": "enable_commands" }
{ "type": "disable_commands" }
{ "type": "get_commands" }
{ "type": "register_command", "pattern": "my phrase", "replacement": "expanded text", "action": "custom_action" }
```

Server to client:

```json
{ "type": "connected", "message": "...", "config": {} }
{ "type": "transcription", "text": "...", "domain": "general", "commands": [], "is_final": true, "processing_time_ms": 123.4, "audio_duration_seconds": 1.2, "flush_reason": "natural_pause" }
{ "type": "control_ack", "action": "flush" }
{ "type": "available_commands", "commands_list": {} }
{ "type": "stats", "data": {} }
{ "type": "error", "message": "...", "code": "..." }
{ "type": "pong", "timestamp": "..." }
```

REST endpoints:

```text
GET /
GET /health
GET /config
```

## Persistence Graph

```mermaid
flowchart TD
  subgraph Browser
    Snippets["transcriptionTemplateMacros"]
    Sessions["transcriptionTemplateSessions"]
    Settings["transcriptionTemplateSettings"]
    AutoSave["transcriptionTemplateAutoSave"]
  end

  Page["frontend/src/app/page.tsx"] --> Snippets
  Page --> Sessions
  Page --> AutoSave
  SettingsHook["frontend/src/hooks/useSettings.ts"] --> Settings
  SnippetManager["frontend/src/components/Sidebar/MacroManager.tsx"] --> Snippets
```

## Architecture Rules

- Keep `/ws/audio` synchronized across backend, frontend constants, README/docs, and this graph.
- Keep audio format assumptions synchronized across `useAudioRecorder.ts`, `audio_config.py`, and `AudioStreamHandler`.
- Keep the built-in domain vanilla. Add domain-specific behavior through wrapper adapters rather than editing `TranscriptionEngine`.
- Keep frontend wrapper branding and feature toggles in `frontend/src/lib/appConfig.ts`.
- Keep user-local snippets/sessions/settings/autosave in localStorage unless a backend storage change is explicitly requested.
- If adding a new cross-boundary message, document its JSON shape here.

## Last Updated Notes

- 2026-05-26: Removed built-in domain-specific formatter/template storage and documented the vanilla wrapper-ready runtime.
