# Backend WebSocket Package

This package contains the backend internals for the `/ws/audio` transcription stream. Read this file before changing WebSocket audio behavior, control messages, response payloads, or buffering rules.

## Responsibilities

- `audio_stream_handler.py`
  - Per-client audio buffer state.
  - VAD-triggered buffering and silence handling.
  - Manual, pause, and max-buffer transcription flushes.
  - Domain adapter post-processing and session stats.

- `stream_text.py`
  - Streaming transcript overlap cleanup.
  - Repeated boundary text suppression.

- `control_messages.py`
  - JSON control messages received over `/ws/audio`.
  - Reset, flush, stats, ping, command enable/disable, command registration, and command history actions.
  - Control acknowledgements and control error responses.

- `responses.py`
  - Connected-message config payloads.
  - Transcription event payloads.
  - Shared timestamp and default field construction for WebSocket responses.

- `../main.py`
  - FastAPI app setup.
  - REST routes.
  - Public `/ws/audio` route orchestration.
  - Connection accept, receive loop, disconnect cleanup, and active connection count.

## Contract Rules

- Keep the WebSocket endpoint as `/ws/audio`.
- Keep browser audio input as raw 16-bit PCM, 16 kHz, mono.
- Keep unknown domains falling back to `general`.
- Keep the built-in `general` domain vanilla.
- Keep response shapes synchronized with `ARCHITECTURE_GRAPH.md`.
- Do not add a second transcription pipeline.

## Change Rules

- Put buffering, VAD, flush, and stats changes in `audio_stream_handler.py`.
- Put streaming overlap text cleanup changes in `stream_text.py`.
- Put JSON control message behavior in `control_messages.py`.
- Put WebSocket response shape construction in `responses.py`.
- Keep `main.py` thin; it should coordinate modules rather than own their internals.
- If a WebSocket message shape changes, update `ARCHITECTURE_GRAPH.md` in the same change.
- If module boundaries or runtime flow change, update `AI_CONTEXT.md` and the relevant ADR.
- Do not add domain-specific formatting here; use `backend/app/domains/`.

## Relevant Tests

- `backend/tests/test_audio_stream_handler_domains.py`
- `backend/tests/test_audio_stream_handler_latency.py`
- `backend/tests/test_websocket_pipeline_modules.py`
- `backend/tests/test_voice_command_contract.py`

For documentation-only changes, `git diff --check` is enough. For code changes in this package, run:

```bash
cd medical-dictation/backend
venv/bin/python -m unittest discover -s tests -v
```
