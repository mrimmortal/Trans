# Architecture Graph: Transcription Template

This file is for AI agents and maintainers. It keeps future changes aligned with the vanilla transcription template.

Durable architecture rationale lives in `docs/adr/`; keep this file focused on current runtime flow and protocol facts.

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
    LLMRoutes["api/llm_routes.py\nPOST /llm/respond"]
    LMStudio["services/lm_studio_client.py\nLM Studio chat client"]
    TTSRoutes["api/tts_routes.py\nPOST /tts/synthesize"]
    SupertonicTTS["services/supertonic_tts_client.py\nSupertonic 3 TTS client"]
    Handler["websocket/audio_stream_handler.py\nVAD buffering + flush"]
    WSControl["websocket/control_messages.py\nJSON control messages"]
    WSResponses["websocket/responses.py\nConnection/transcription payloads"]
    Config["backend/app/audio_config.py\nAudio/model/server config"]
    Engine["services/transcription_engine.py\nSilero VAD + Faster-Whisper"]
    AudioProcessing["services/audio_processing.py\nAudio conversion/preprocessing"]
    TextProcessing["services/transcription_text.py\nHallucination filtering/text cleanup"]
    CudaBootstrap["infrastructure/cuda_bootstrap.py\nWindows CUDA path setup"]
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
  App --> LLMRoutes
  LLMRoutes --> LMStudio
  LLMRoutes --> Config
  App --> TTSRoutes
  TTSRoutes --> SupertonicTTS
  TTSRoutes --> Config
  App --> WSControl
  App --> WSResponses
  Handler --> Config
  Handler --> Engine
  Handler --> Domains
  WSControl --> Handler
  Engine --> AudioProcessing
  Engine --> TextProcessing
  Engine --> CudaBootstrap
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
  B-->>W: responses.py builds { type: "transcription", text, domain, commands }
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
POST /llm/respond
POST /tts/synthesize
```

`POST /llm/respond` accepts `{ "text": "...", "system_prompt": "..." }`, calls the configured LM Studio OpenAI-compatible `/chat/completions` endpoint, and returns `{ "response": "...", "model": "...", "provider": "lmstudio" }`. It is independent of `/ws/audio` and does not alter the transcription pipeline.

`POST /tts/synthesize` accepts `{ "text": "...", "voice": "M1", "lang": "en" }`, calls Supertonic 3 through the backend TTS service, and returns playable `audio/wav` bytes. It is independent of `/ws/audio`, STT, and the LM Studio flow.

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
- Keep backend WebSocket buffering in `backend/app/websocket/audio_stream_handler.py`, control message handling in `backend/app/websocket/control_messages.py`, and response payload construction in `backend/app/websocket/responses.py`.
- Keep Windows CUDA path setup centralized in `backend/app/infrastructure/cuda_bootstrap.py`.
- Keep audio conversion/preprocessing in `backend/app/services/audio_processing.py` and transcription text cleanup in `backend/app/services/transcription_text.py`.
- Keep the built-in domain vanilla. Add domain-specific behavior through wrapper adapters rather than editing `TranscriptionEngine`.
- Keep the LM Studio REST integration in `backend/app/api/llm_routes.py` and `backend/app/services/lm_studio_client.py`; do not route it through `/ws/audio`.
- Keep the Supertonic TTS integration in `backend/app/api/tts_routes.py` and `backend/app/services/supertonic_tts_client.py`; do not route it through `/ws/audio`.
- Keep frontend wrapper branding and feature toggles in `frontend/src/lib/appConfig.ts`.
- Keep user-local snippets/sessions/settings/autosave in localStorage unless a backend storage change is explicitly requested.
- If adding a new cross-boundary message, document its JSON shape here.

## Last Updated Notes

- 2026-05-26: Removed built-in domain-specific formatter/template storage and documented the vanilla wrapper-ready runtime.
- 2026-05-30: Split backend WebSocket audio pipeline internals into focused `backend/app/websocket/` modules while keeping `/ws/audio` in `backend/app/main.py`.
- 2026-05-30: Centralized backend CUDA bootstrap and split audio/text helper responsibilities out of `TranscriptionEngine`.
- 2026-05-30: Added backend-only `POST /llm/respond` for LM Studio responses, separate from the WebSocket transcription flow.
- 2026-05-30: Added backend-only `POST /tts/synthesize` for Supertonic 3 `audio/wav` synthesis, separate from STT and the WebSocket transcription flow.
