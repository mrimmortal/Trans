# AI Context: Medical Dictation

Use this file first to reduce context and avoid hallucinated architecture.

## Product

Medical Dictation is a real-time clinical dictation web app. The browser records microphone audio, streams it to a FastAPI backend over WebSocket, receives transcribed/formatted medical text plus command events, and inserts/acts on those results in a TipTap editor.

## Read These First

Frontend entry:

- `frontend/src/app/page.tsx`
- `frontend/src/lib/constants.ts`
- `frontend/src/hooks/useAudioRecorder.ts`
- `frontend/src/hooks/useWebSocket.ts`

Backend entry:

- `backend/app/main.py`
- `backend/app/audio_config.py`
- `backend/app/services/transcription_engine.py`
- `backend/app/services/medical_formatter.py`
- `backend/app/services/command_processor.py`
- `backend/app/services/template_manager.py`
- `backend/app/api/template_routes.py`

For the full map, read `ARCHITECTURE_GRAPH.md`.

For Mac, Windows, and UAT setup, read `ENVIRONMENTS.md`.

## Fixed Facts

- Backend framework: FastAPI.
- Frontend framework: Next.js/React.
- Editor: TipTap.
- Speech engine: Faster-Whisper through `TranscriptionEngine`.
- WebSocket endpoint: `/ws/audio`.
- Template REST API prefix: `/api/templates`.
- Browser audio format expected by backend: 16-bit PCM, 16kHz, mono.
- Audio chunks are sent from frontend to backend as WebSocket binary messages.
- `TranscriptionEngine.detect_speech` may receive chunks larger than Silero's 512-sample model window and must frame them internally before scoring.
- Default transcription profile is `balanced_realtime`: roughly 0.6s minimum speech buffer, 0.7s silence pause trigger, 6s max forced buffer, and Whisper beam size 2.
- WebSocket transcription responses include actual backend `processing_time_ms`, `audio_duration_seconds`, and `flush_reason` for latency diagnosis.
- Control messages are sent as WebSocket JSON text messages.
- Transcription responses are sent from backend to frontend as WebSocket JSON messages.
- Frontend transcription insertion is event-based: `page.tsx` wraps processed text with an id, `DictationEditor` inserts it once, then clears the pending text.
- Sessions, macros, settings, and autosave are primarily browser `localStorage` concerns.
- Custom templates are backend/SQLite concerns.
- Each WebSocket `AudioStreamHandler` owns a session `CommandProcessor` and must register active SQLite templates so phrases like `insert assessment` trigger template insertion during dictation.
- Supported environments: DEV-MAC, DEV-WINDOWS, hosted UAT-WIN, and hosted PROD-WIN.
- Frontend URLs come from `NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_WS_URL`.
- Backend CORS origins come from `CORS_ORIGINS`.

## Current Runtime Flow

1. User starts recording in `frontend/src/app/page.tsx`.
2. `useWebSocket(WS_URL)` connects to backend `/ws/audio`.
3. `useAudioRecorder` captures microphone audio.
4. Audio is downsampled/converted to 16-bit PCM.
5. Frontend sends audio chunks as binary WebSocket messages.
6. `backend/app/main.py` receives chunks in `websocket_audio_stream`.
7. `AudioStreamHandler` runs speech detection and buffers useful audio.
8. On pause/max buffer/flush, `TranscriptionEngine` transcribes audio.
9. `MedicalFormatter` applies medical text cleanup.
10. `CommandProcessor` extracts punctuation, editing, formatting, control, custom, and template commands.
11. Punctuation and template commands produce insertable text; formatting, editing, navigation, and control commands are editor/app actions and should not insert literal marker text.
12. Backend sends `{ type: "transcription", text, commands }`.
13. Frontend inserts text into the editor and executes supported commands.

## Common Change Targets

- Change environment setup: update `ENVIRONMENTS.md`, relevant `.env.*` files, scripts under `scripts/`, and this file.
- Change backend endpoint/protocol: update `backend/app/main.py`, `frontend/src/hooks/useWebSocket.ts`, `frontend/src/lib/constants.ts`, and `ARCHITECTURE_GRAPH.md`.
- Change audio format/chunking: update `frontend/src/hooks/useAudioRecorder.ts`, `backend/app/audio_config.py`, backend handler expectations, and docs.
- Change voice commands: update `backend/app/services/command_processor.py`; if frontend action is needed, update command handling in `frontend/src/app/page.tsx`.
- Change medical formatting: update `backend/app/services/medical_formatter.py`.
- Change templates: update `backend/app/services/template_manager.py`, `backend/app/api/template_routes.py`, frontend template hooks/components, and docs.
- Change editor behavior: update `frontend/src/components/Editor/DictationEditor.tsx` and command insertion logic in `frontend/src/app/page.tsx`.

## Hallucination Guards

- Do not refer to the old dictate WebSocket path; current backend endpoint is `/ws/audio`.
- Do not assume all persistence is backend database. Local user macros/sessions/settings/autosave use `localStorage`.
- Do not assume template CRUD is frontend-only. Template CRUD is exposed by backend REST routes under `/api/templates`.
- Do not assume the app uses server-sent events or HTTP polling for transcription. It uses WebSocket.
- Do not add a second transcription pipeline unless explicitly requested.
- Do not hardcode dev tunnel URLs in `frontend/src/lib/constants.ts`.

## Environments And Pipeline

DEV-MAC:

- Backend env: `backend/.env.mac`
- Backend dependencies: `backend/requirements-mac.txt` installed into `backend/venv` by `scripts/run.sh mac-dev`
- Frontend env: `frontend/.env.local.mac`
- Startup command: `scripts/run.sh mac-dev`
- Default WebSocket: `ws://127.0.0.1:8000/ws/audio`

DEV-WINDOWS:

- Backend env: `backend/.env.windows`
- Backend dependencies: `backend/requirements.txt` installed into `backend/venv` by `scripts/run.ps1 win-dev`
- Frontend env: `frontend/.env.local.windows`
- Startup command: `scripts/run.ps1 win-dev`
- Default WebSocket: `ws://127.0.0.1:8000/ws/audio`

UAT:

- Backend env: `backend/.env.uat`
- Frontend env: `frontend/.env.uat`
- Validation command: `scripts/run.sh uat-check`
- Must use HTTPS/WSS and restricted CORS origins.
- Deployment target: GitHub environment `UAT` on self-hosted Windows runner labels `self-hosted`, `Windows`, `uat-win`.

PROD-WIN:

- Backend env: `backend/.env.prod`
- Frontend env: `frontend/.env.prod`
- Must use HTTPS/WSS and restricted CORS origins.
- Deployment target: GitHub environment `Production` on self-hosted Windows runner labels `self-hosted`, `Windows`, `prod-win`.

Pipeline:

- Workflow: `.github/workflows/medical-dictation-pipeline.yml`
- Script entry points: `scripts/run.sh` and `scripts/run.ps1`
- Service restart is handled inside `scripts/run.ps1`.
- UAT secrets: `UAT_BACKEND_ENV`, `UAT_FRONTEND_ENV`
- Production secrets: `PROD_BACKEND_ENV`, `PROD_FRONTEND_ENV`
