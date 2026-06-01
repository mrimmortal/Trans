# ADR 0001: Backend WebSocket Module Boundaries

## Status

Accepted.

## Context

The backend WebSocket path is the core transcription runtime. It accepts browser microphone audio, buffers and transcribes speech, handles JSON control messages, and returns transcription events to the frontend. Keeping all of that behavior in `backend/app/main.py` made the route harder to review and increased the risk of accidental protocol changes during refactors.

The project is a vanilla, wrapper-ready transcription template. Domain-specific behavior must stay outside the core pipeline, and the `/ws/audio` contract must remain stable for frontend and wrapper compatibility.

## Decision

Keep the public WebSocket endpoint in `backend/app/main.py`, but keep the implementation responsibilities in focused backend WebSocket modules:

- `backend/app/main.py` owns FastAPI app setup, REST routes, and `/ws/audio` orchestration.
- `backend/app/websocket/audio_stream_handler.py` owns per-client buffering, VAD decisions, transcription flushing, domain adapter calls, and session stats.
- `backend/app/websocket/stream_text.py` owns streaming overlap text cleanup and repeated boundary text suppression.
- `backend/app/websocket/control_messages.py` owns JSON control message handling for reset, flush, stats, ping, and command-related controls.
- `backend/app/websocket/responses.py` owns connection and transcription response payload construction.

## Preserved Contracts

- WebSocket endpoint remains `/ws/audio`.
- Browser audio remains raw 16-bit PCM, 16 kHz, mono.
- Unknown backend domains continue to fall back to `general`.
- The built-in `general` domain remains vanilla transcription with no domain formatting.
- Existing transcription, control, error, stats, and connection response shapes are preserved unless a future change explicitly updates the protocol and docs.

## Consequences

- Future audio buffering or VAD changes should start in `audio_stream_handler.py`.
- Future streaming text overlap cleanup changes should start in `stream_text.py`.
- Future control message changes should start in `control_messages.py`.
- Future WebSocket payload shape changes should start in `responses.py` and must update `ARCHITECTURE_GRAPH.md`.
- `main.py` should stay thin and should not regain transcription, buffering, or control-message internals.
