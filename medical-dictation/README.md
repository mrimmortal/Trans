# Transcription Template

A vanilla, wrapper-ready real-time transcription app.

The browser records microphone audio, streams 16 kHz mono PCM to a FastAPI backend over `/ws/audio`, receives transcript events, and inserts text into a TipTap editor. The built-in backend domain is `general`, which returns transcription text unchanged.

## Stack

- Backend: FastAPI, Faster-Whisper, Silero VAD
- Frontend: Next.js, React, TipTap
- Transport: WebSocket binary audio plus JSON control/transcription messages
- Persistence: browser localStorage for snippets, sessions, settings, and autosave

## Run Locally

macOS:

```bash
cd medical-dictation
./scripts/run.sh mac-dev
```

Windows:

```powershell
cd medical-dictation
.\scripts\run.ps1 win-dev
```

Default URLs:

```text
Frontend: http://localhost:3000
Backend:  http://127.0.0.1:8000
WebSocket: ws://127.0.0.1:8000/ws/audio
```

## Wrapper Points

- Backend domain wrappers: `backend/app/domains/*`
- Backend command parsing helpers: `backend/app/services/command_processor.py`
- Backend transcription prompt/config: `backend/app/audio_config.py`
- Frontend branding and feature toggles: `frontend/src/lib/appConfig.ts`
- Frontend default snippets: `frontend/src/lib/defaultMacros.ts`

Keep the core audio pipeline vanilla. Domain-specific formatting, storage, templates, or workflows should live in wrapper-specific modules and be documented in `AI_CONTEXT.md` and `ARCHITECTURE_GRAPH.md`.

## Core Protocol

Client to server:

```text
Binary: raw 16-bit PCM audio, 16 kHz, mono
JSON:   control messages such as ping, flush, reset, stats
```

Server to client:

```json
{ "type": "transcription", "text": "...", "domain": "general", "commands": [] }
```

## AI Context

Before changing the project, read:

1. `AI_CONTEXT.md`
2. `ENVIRONMENTS.md` for setup/deployment changes
3. `ARCHITECTURE_GRAPH.md` for architecture, protocol, storage, or cross-module changes
