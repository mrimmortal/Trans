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
- `frontend/src/hooks/useLocalAssistant.ts`
- `frontend/src/services/assistantApi.ts`
- `frontend/src/services/ttsApi.ts`
- `frontend/src/components/Assistant/LocalAssistantPanel.tsx`

Backend entry:

- `backend/app/main.py`
- `backend/app/dependencies.py`
- `backend/app/audio_config.py`
- `backend/app/infrastructure/cuda_bootstrap.py`
- `backend/app/services/audio_processing.py`
- `backend/app/services/stt/service.py`
- `backend/app/services/stt/faster_whisper.py`
- `backend/app/services/transcription_text.py`
- `backend/app/websocket/stream_text.py`
- `backend/app/api/llm_routes.py`
- `backend/app/services/llm/service.py`
- `backend/app/services/llm/lm_studio.py`
- `backend/app/api/tts_routes.py`
- `backend/app/services/tts/service.py`
- `backend/app/services/tts/supertonic.py`
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
- Speech engine: Faster-Whisper through the backend STT service/provider boundary.
- WebSocket endpoint: `/ws/audio`.
- Browser audio format expected by backend: 16-bit PCM, 16 kHz, mono.
- Audio chunks are sent from frontend to backend as WebSocket binary messages.
- Control messages are sent as WebSocket JSON text messages.
- Transcription responses are sent from backend to frontend as WebSocket JSON messages.
- Built-in backend domain: `general` only.
- Unknown `domain` query values fall back to `general`.
- `general` is vanilla transcription with no domain formatting, templates, or server-side commands.
- Domain adapters are registered through `backend/app/domains/registry.py`; `get_available_domains()` drives backend config and WebSocket welcome metadata.
- Backend service construction is centralized in `backend/app/dependencies.py`.
- Wrapper-ready backend seams: `backend/app/domains/*`, `CommandProcessor`, `AudioConfig.get_initial_prompt()`, and backend provider factories in `dependencies.py`.
- Wrapper-ready frontend seam: `frontend/src/lib/appConfig.ts`.
- Sessions, snippets, settings, and autosave are browser `localStorage` concerns.
- Frontend URLs come from `NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_WS_URL`.
- Frontend local assistant calls `POST /llm/respond`, displays the response, calls `POST /tts/synthesize`, and plays returned WAV audio through a browser object URL.
- Backend CORS origins come from `CORS_ORIGINS`.
- `scripts/run.sh mac-dev`, `scripts/run.sh uat-check`, and `scripts/run.sh prod-check` fall back to `backend/.env.example` when local backend env files are absent.
- Optional local LLM responses use `POST /llm/respond`, backed by LM Studio's OpenAI-compatible `/chat/completions` API.
- LM Studio config comes from `LM_STUDIO_BASE_URL`, `LM_STUDIO_MODEL`, and `LM_STUDIO_TIMEOUT_SECONDS`.
- `POST /llm/respond` is independent of `/ws/audio` and does not change transcription behavior.
- Backend LLM code is split between generic service/provider boundaries in `backend/app/services/llm/`, centralized service construction in `backend/app/dependencies.py`, and the LM Studio provider implementation.
- Optional local TTS uses `POST /tts/synthesize`, backed by Supertonic 3 through the Python SDK.
- TTS config comes from `TTS_PROVIDER`, `SUPERTONIC_VOICE`, `SUPERTONIC_LANG`, and optional `TTS_OUTPUT_DIR`.
- `POST /tts/synthesize` is independent of `/ws/audio`, STT, and the LM Studio flow.
- Backend TTS code is split between generic service/provider boundaries in `backend/app/services/tts/`, centralized service construction in `backend/app/dependencies.py`, and the Supertonic provider implementation.
- Backend STT code is split between the generic service/provider boundary in `backend/app/services/stt/`, centralized service construction in `backend/app/dependencies.py`, and the Faster-Whisper/Silero provider implementation.
- Streaming transcript overlap cleanup lives in `backend/app/websocket/stream_text.py`; `AudioStreamHandler` coordinates buffering and flush decisions.
- Do not hardcode temporary tunnel URLs in source code.

## Current Runtime Flow

1. User starts recording in `frontend/src/app/page.tsx`.
2. `useWebSocket(WS_URL)` connects to backend `/ws/audio`.
3. `useAudioRecorder` captures microphone audio.
4. Audio is downsampled/converted to 16-bit PCM.
5. Frontend sends audio chunks as binary WebSocket messages.
6. `backend/app/main.py` receives chunks in `websocket_audio_stream`.
7. `backend/app/websocket/audio_stream_handler.py` calls the STT service for speech detection and buffers useful audio.
8. On pause/max buffer/flush, the STT service delegates to the Faster-Whisper/Silero provider, which transcribes audio using `audio_processing.py` and `transcription_text.py` helpers.
9. `AudioStreamHandler` uses `websocket/stream_text.py` to remove overlap artifacts before domain processing.
10. The selected domain adapter processes transcript text; built-in `general` returns text unchanged.
11. `backend/app/websocket/responses.py` builds `{ type: "transcription", text, domain, commands }`.
12. Frontend processes local snippets/voice commands and inserts text into the editor.

## Local Assistant Flow

1. User clicks Local Assistant in `frontend/src/components/Assistant/LocalAssistantPanel.tsx`.
2. `frontend/src/app/page.tsx` reads current TipTap plain text.
3. `frontend/src/hooks/useLocalAssistant.ts` calls `assistantApi.requestAssistantResponse()`.
4. `frontend/src/services/assistantApi.ts` sends `POST /llm/respond`.
5. The assistant response is shown in the panel.
6. `useLocalAssistant` calls `ttsApi.synthesizeSpeech()` with the response text.
7. `frontend/src/services/ttsApi.ts` sends `POST /tts/synthesize` and creates an audio object URL.
8. `useLocalAssistant` plays the returned WAV through browser audio.

This flow is independent of `/ws/audio`, `useWebSocket`, `useAudioRecorder`, and the STT insertion path.

## Common Change Targets

- Change frontend branding/wrapper toggles: update `frontend/src/lib/appConfig.ts`.
- Change frontend local assistant behavior: update `frontend/src/hooks/useLocalAssistant.ts`, `frontend/src/services/assistantApi.ts`, `frontend/src/services/ttsApi.ts`, `frontend/src/components/Assistant/LocalAssistantPanel.tsx`, and `ARCHITECTURE_GRAPH.md`.
- Change backend wrapper behavior: update `backend/app/domains/*` and register adapters through `backend/app/domains/registry.py`.
- Change backend endpoint/protocol: update `backend/app/main.py`, `backend/app/websocket/control_messages.py`, `backend/app/websocket/responses.py`, `frontend/src/hooks/useWebSocket.ts`, `frontend/src/lib/constants.ts`, and `ARCHITECTURE_GRAPH.md`.
- Change audio format/chunking: update `frontend/src/hooks/useAudioRecorder.ts`, `backend/app/audio_config.py`, `backend/app/websocket/audio_stream_handler.py`, and docs.
- Change backend service construction: update `backend/app/dependencies.py` and focused route/service tests.
- Change backend STT behavior: update `backend/app/dependencies.py`, `backend/app/services/stt/service.py`, `backend/app/services/stt/faster_whisper.py`, `backend/app/services/audio_processing.py`, `backend/app/services/transcription_text.py`, `backend/app/audio_config.py`, focused STT/WebSocket tests, and `ARCHITECTURE_GRAPH.md`.
- Change backend runtime env defaults: update `backend/app/audio_config.py`, `backend/.env.example`, setup docs, and tests.
- Change shell startup env loading: update `scripts/run.sh`, `ENVIRONMENTS.md`, and script tests.
- Change local LLM behavior: update `backend/app/dependencies.py`, `backend/app/api/llm_routes.py`, `backend/app/services/llm/service.py`, `backend/app/services/llm/lm_studio.py`, `backend/app/models/schemas.py`, `backend/app/audio_config.py`, and `ARCHITECTURE_GRAPH.md`.
- Change local TTS behavior: update `backend/app/dependencies.py`, `backend/app/api/tts_routes.py`, `backend/app/services/tts/service.py`, `backend/app/services/tts/supertonic.py`, `backend/app/models/schemas.py`, `backend/app/audio_config.py`, and `ARCHITECTURE_GRAPH.md`.
- Change generic voice commands: update `backend/app/services/command_processor.py` and `frontend/src/hooks/useVoiceCommands.ts`.
- Change editor insertion behavior: update `frontend/src/app/page.tsx` and `frontend/src/components/Editor/DictationEditor.tsx`.

## Hallucination Guards

- Do not refer to old medical-specific behavior as built in.
- Do not add clinical prompts, clinical templates, or domain-specific defaults to the vanilla template.
- Do not invent alternate endpoints. The backend WebSocket endpoint is `/ws/audio`.
- Do not assume backend persistence exists. User snippets, sessions, settings, and autosave use `localStorage`.
- Do not assume template CRUD exists in vanilla. Add it only inside a wrapper-specific change.
- Do not add a second transcription pipeline unless explicitly requested.
- Do not route LM Studio calls through `/ws/audio`; keep `POST /llm/respond` as a separate REST integration.
- Do not route TTS through `/ws/audio`; keep `POST /tts/synthesize` as a separate REST integration.
- Do not mix frontend assistant fetch/audio playback logic into `useWebSocket` or `useAudioRecorder`.

## Last Updated Notes

- 2026-05-26: Converted the project to a vanilla transcription template. Removed built-in medical formatter/domain/template storage and made UI branding/config wrapper-ready.
- 2026-05-30: Split backend WebSocket audio pipeline internals out of `backend/app/main.py` into `backend/app/websocket/audio_stream_handler.py`, `control_messages.py`, and `responses.py` while preserving `/ws/audio`.
- 2026-05-30: Centralized Windows CUDA bootstrap, replaced tracked backend `.env*` files with `backend/.env.example`, pruned stale backend schemas, and split audio/text helpers out of the STT implementation.
- 2026-05-30: Added backend-only LM Studio integration through `POST /llm/respond` with config in `AudioConfig`; it is independent of `/ws/audio`.
- 2026-05-30: Added backend-only Supertonic 3 TTS integration through `POST /tts/synthesize`; it returns `audio/wav` and is independent of STT, LM Studio, and `/ws/audio`.
- 2026-05-30: Updated `scripts/run.sh` so macOS dev and local UAT checks fall back to `backend/.env.example` when local backend env files are absent.
- 2026-05-30: Added macOS/Linux `prod-check` support for local production build validation.
- 2026-05-30: Added frontend Local Assistant flow that sends editor text to LM Studio, displays the response, synthesizes speech, and plays WAV audio without changing STT or `/ws/audio`.
- 2026-05-31: Refactored backend LM Studio and Supertonic integrations into generic LLM/TTS service/provider boundaries while preserving `POST /llm/respond` and `POST /tts/synthesize` behavior.
- 2026-06-01: Refactored backend STT into generic service/provider boundaries with Faster-Whisper/Silero as the provider while preserving `/ws/audio` behavior.
- 2026-06-01: Added centralized backend service construction in `backend/app/dependencies.py`, map-based domain registration, typed STT result contracts, and `websocket/stream_text.py` overlap cleanup while preserving public endpoints and `/ws/audio` message shapes.
