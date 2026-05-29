# AI Context: Transcription Template

Use this file first to reduce context and avoid hallucinated architecture.

## Product

Transcription Template is a vanilla, wrapper-ready real-time transcription app. The browser records microphone audio, streams 16 kHz mono PCM to a FastAPI backend over WebSocket, receives vanilla transcript events, and inserts text into a TipTap editor. Domain wrappers should extend the adapter/config seams instead of changing the core audio pipeline.

## Read These First

Frontend entry:

- `frontend/src/app/page.tsx`
- `frontend/src/lib/appConfig.ts`
- `frontend/src/lib/constants.ts`
- `frontend/src/hooks/useAudioRecorder.ts`
- `frontend/src/hooks/useWebSocket.ts`
- `frontend/src/hooks/useVoiceCommands.ts`

Backend entry:

- `backend/app/main.py`
- `backend/app/audio_config.py`
- `backend/app/infrastructure/cuda_bootstrap.py`
- `backend/app/services/audio_processing.py`
- `backend/app/services/transcription_engine.py`
- `backend/app/services/transcription_text.py`
- `backend/app/domains/base.py`
- `backend/app/domains/general.py`
- `backend/app/domains/registry.py`
- `backend/app/services/command_processor.py`

For WebSocket/audio changes, read `backend/app/websocket/README.md` first, then the focused files in `backend/app/websocket/`.

For the full map, read `ARCHITECTURE_GRAPH.md`.

For durable architecture rationale, read the relevant records in `docs/adr/`.

For Mac, Windows, and UAT setup, read `ENVIRONMENTS.md`.

## Fixed Facts

- Backend framework: FastAPI.
- Frontend framework: Next.js/React.
- Editor: TipTap.
- Speech engine: Faster-Whisper through `TranscriptionEngine`.
- WebSocket endpoint: `/ws/audio`.
- Browser audio format expected by backend: 16-bit PCM, 16 kHz, mono.
- Audio chunks are sent from frontend to backend as WebSocket binary messages.
- Control messages are sent as WebSocket JSON text messages.
- Transcription responses are sent from backend to frontend as WebSocket JSON messages.
- Built-in backend domain: `general` only.
- Unknown `domain` query values fall back to `general`.
- `general` is vanilla transcription with no domain formatting, templates, or server-side commands.
- Wrapper-ready backend seams: `backend/app/domains/*`, `CommandProcessor`, and `AudioConfig.get_initial_prompt()`.
- Wrapper-ready frontend seam: `frontend/src/lib/appConfig.ts`.
- Sessions, snippets, settings, and autosave are browser `localStorage` concerns.
- Frontend URLs come from `NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_WS_URL`.
- Backend CORS origins come from `CORS_ORIGINS`.
- Do not hardcode temporary tunnel URLs in source code.

## Current Runtime Flow

1. User starts recording in `frontend/src/app/page.tsx`.
2. `useWebSocket(WS_URL)` connects to backend `/ws/audio`.
3. `useAudioRecorder` captures microphone audio.
4. Audio is downsampled/converted to 16-bit PCM.
5. Frontend sends audio chunks as binary WebSocket messages.
6. `backend/app/main.py` receives chunks in `websocket_audio_stream`.
7. `backend/app/websocket/audio_stream_handler.py` runs speech detection and buffers useful audio.
8. On pause/max buffer/flush, `TranscriptionEngine` transcribes audio using `audio_processing.py` and `transcription_text.py` helpers.
9. The selected domain adapter processes transcript text; built-in `general` returns text unchanged.
10. `backend/app/websocket/responses.py` builds `{ type: "transcription", text, domain, commands }`.
11. Frontend processes local snippets/voice commands and inserts text into the editor.

## Common Change Targets

- Change frontend branding/wrapper toggles: update `frontend/src/lib/appConfig.ts`.
- Change backend wrapper behavior: update `backend/app/domains/*` and `backend/app/domains/registry.py`.
- Change backend endpoint/protocol: update `backend/app/main.py`, `backend/app/websocket/control_messages.py`, `backend/app/websocket/responses.py`, `frontend/src/hooks/useWebSocket.ts`, `frontend/src/lib/constants.ts`, and `ARCHITECTURE_GRAPH.md`.
- Change audio format/chunking: update `frontend/src/hooks/useAudioRecorder.ts`, `backend/app/audio_config.py`, `backend/app/websocket/audio_stream_handler.py`, and docs.
- Change backend runtime env defaults: update `backend/app/audio_config.py`, `backend/.env.example`, setup docs, and tests.
- Change generic voice commands: update `backend/app/services/command_processor.py` and `frontend/src/hooks/useVoiceCommands.ts`.
- Change editor insertion behavior: update `frontend/src/app/page.tsx` and `frontend/src/components/Editor/DictationEditor.tsx`.

## Hallucination Guards

- Do not refer to old medical-specific behavior as built in.
- Do not add clinical prompts, clinical templates, or domain-specific defaults to the vanilla template.
- Do not invent alternate endpoints. The backend WebSocket endpoint is `/ws/audio`.
- Do not assume backend persistence exists. User snippets, sessions, settings, and autosave use `localStorage`.
- Do not assume template CRUD exists in vanilla. Add it only inside a wrapper-specific change.
- Do not add a second transcription pipeline unless explicitly requested.

## Last Updated Notes

- 2026-05-26: Converted the project to a vanilla transcription template. Removed built-in medical formatter/domain/template storage and made UI branding/config wrapper-ready.
- 2026-05-30: Split backend WebSocket audio pipeline internals out of `backend/app/main.py` into `backend/app/websocket/audio_stream_handler.py`, `control_messages.py`, and `responses.py` while preserving `/ws/audio`.
- 2026-05-30: Centralized Windows CUDA bootstrap, replaced tracked backend `.env*` files with `backend/.env.example`, pruned stale backend schemas, and split audio/text helpers out of `TranscriptionEngine`.
