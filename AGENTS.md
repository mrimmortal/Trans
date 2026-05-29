Project-specific architecture rules:

Core stack:
- Frontend: Next.js + React + TipTap
- Backend: FastAPI
- Speech engine: Faster-Whisper
- WebSocket endpoint: /ws/audio
- Audio format: 16-bit PCM, 16 kHz, mono
- Default transcription domain: general
- Sessions, snippets/macros, settings, and autosave use browser localStorage

Architecture direction:
- Keep the app modular and wrapper-ready.
- Keep the core transcription pipeline stable.
- Keep domain-specific behavior outside the vanilla core.
- Keep frontend and backend contracts explicit and documented.
- Keep audio capture, WebSocket transport, transcription, command processing, and editor insertion as separate concerns.

Backend rules:
- Keep FastAPI routes thin.
- Keep WebSocket protocol handling clear and isolated.
- Keep transcription logic inside service modules.
- Keep domain behavior inside backend/app/domains/.
- Keep audio/model configuration inside backend/app/audio_config.py.
- Do not scatter environment variable reads across the codebase.
- Avoid mixing VAD, buffering, transcription, domain formatting, and WebSocket response creation in one large module when refactoring is requested.

Frontend rules:
- Keep visual components separate from audio/WebSocket logic.
- Keep audio recording inside hooks/services.
- Keep WebSocket logic inside hooks/services.
- Keep editor insertion behavior separate from transport logic.
- Keep branding and wrapper toggles in frontend/src/lib/appConfig.ts.
- Keep storage keys centralized.

Do not:
- Do not add medical-specific behavior to the vanilla core unless explicitly requested.
- Do not add clinical prompts, diagnosis logic, medical templates, or medical formatting by default.
- Do not change /ws/audio unless explicitly requested.
- Do not create a second transcription pipeline unless explicitly requested.
- Do not hardcode tunnel URLs.
- Do not assume backend database persistence exists.
- Do not add template CRUD unless explicitly requested.
- Do not make broad UI redesigns unless explicitly requested.
- Do not change audio format assumptions unless explicitly requested.

Preferred extension points:
- Backend domains: backend/app/domains/
- Commands: CommandProcessor
- Audio/model config: backend/app/audio_config.py
- Frontend branding/config: frontend/src/lib/appConfig.ts
- WebSocket logic: frontend/src/hooks/useWebSocket.ts
- Audio capture: frontend/src/hooks/useAudioRecorder.ts

Development priority:
- Clean architecture.
- Small focused modules.
- CPU-only compatibility.
- Mac, Windows, and Raspberry Pi compatibility.
- Small targeted fixes over broad refactors.
- Avoid unnecessary GPU/CUDA assumptions unless the task is GPU-specific.