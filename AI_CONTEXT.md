# AI Context

## Project Summary

This checkout currently contains `CoreSTT`, a standalone Python speech-to-text
core with a reusable package, FastAPI demo server, browser microphone console,
binary audio packet helpers, and focused server/protocol tests.

The GitHub Actions workflow references a separate `medical-dictation/` tree
that is not present in this checkout. Treat that as `To verify` before using CI
commands as local validation.

## Active Modules

- `CoreSTT/CoreSTT/`: reusable Python package.
- `CoreSTT/CoreSTT/audio_recorder.py`: public `AudioToTextRecorder` facade and
  historical constructor signature.
- `CoreSTT/CoreSTT/core/`: recorder lifecycle, VAD, buffering, realtime
  processing, text formatting, wake-word, and transcription flow helpers.
- `CoreSTT/CoreSTT/server/`: internal modules extracted from the FastAPI
  server for settings/CLI parsing, audio helpers, timeline tracking,
  connection tracking, statistics, domain profile loading, and inference
  scheduling.
- `CoreSTT/CoreSTT/transcription_engines/`: ASR adapter implementations and
  factory.
- `CoreSTT/server.py`: public FastAPI/uvicorn browser streaming server,
  compatibility exports, and script entrypoint.
- `CoreSTT/protocol.py`: binary browser audio packet and config parsing helpers.
- `CoreSTT/domain_profiles.json`: server-owned transcription domain profiles
  for per-session prompt and faster-whisper hotword biasing.
- `CoreSTT/static/index.html`: browser console UI.
- `docs/WEBSOCKET_CLIENT_CONTRACT.md`: standardized client request/input
  contract for `WS /ws/transcribe`; read before building non-browser clients.
- `CoreSTT/tools/stress/harness.py`: repo-local websocket stress and soak test
  harness for concurrent handshake or synthetic audio streaming load.
- `CoreSTT/tests/`: `unittest` coverage for server config and protocol behavior.

## Key Entrypoints

- Package import: `from CoreSTT import AudioToTextRecorder`
- Server: `cd CoreSTT && python server.py --host 127.0.0.1 --port 8020 --device cpu`
- Server HTTP endpoints: `/`, `/health`, `/api/config`, `/api/metrics`
- Domain profile HTTP endpoint: `/api/domain-profiles`
- Streaming endpoint: `WS /ws/transcribe`
- Optional domain-biased streaming: send `{"type":"start","domain":"medical"}`
  after the WebSocket is ready.

## What To Read First

1. `AGENTS.md`
2. `AI_CONTEXT.md`
3. `docs/MODULE_MAP.md`
4. `docs/COMMANDS.md`
5. Relevant `.ai-rules/*.md`
6. Relevant source files only

## Runtime / Integration Notes

- Python dependencies are listed in `CoreSTT/requirements.txt`.
- Deployment helpers live in `scripts/`: `deploy-macos.sh`,
  `deploy-linux.sh`, and `deploy-windows.ps1` follow `docs/COMMANDS.md` setup
  and run commands for each OS.
- Create and use `CoreSTT/.venv` for local setup and testing. Run tests through
  `.venv/bin/python` after installing requirements instead of relying on a
  global `python` executable.
- Default README server configuration uses final model `small.en`, realtime
  model `tiny.en`, backend `faster_whisper`, and CUDA with fallback to CPU.
  Model roles are fixed; device and compute type remain configurable.
- Production WebSocket sessions use `RealtimeSession`; the recorder-backed
  session is opt-in. Realtime audio uses WebRTC speech detection, a bounded
  five-second ring buffer, and Faster-Whisper VAD disabled. Final jobs retain
  the complete utterance and enable Faster-Whisper VAD.
- Final and realtime engines load once at startup. Final jobs have scheduler
  priority, cancel queued realtime work for the same segment, and suppress late
  realtime results after finalization.
- Faster-Whisper startup controls include `cpu_threads`, `num_workers`, and a
  same-GPU inference gate. The gate is enabled by default only for effective
  CUDA scheduling and blocks new realtime inference while final work is queued
  or active.
- `realtime_transcription_enabled` defaults to true. Disabling it stops
  the interim realtime transcription pipeline but keeps speech detection,
  final-utterance buffering, and final transcription active.
- `/api/metrics` includes additive resource and diagnostic fields for the
  browser diagnostics dashboard. The dashboard polls every two seconds and can
  export local JSON, JSONL, or CSV samples.
- PyAudio may require PortAudio on macOS before installing requirements.
- `.venv`, `__pycache__`, generated assets, model downloads, and secrets are
  not AI-edit targets unless explicitly requested.

## Validation Starting Point

See `docs/COMMANDS.md`.

## Important Boundaries

- Preserve the public `AudioToTextRecorder` constructor signature unless the
  user explicitly asks for a breaking API change.
- Preserve binary packet behavior in `CoreSTT/protocol.py` and websocket server
  expectations unless intentionally changing the browser/server contract.
- Preserve domain profile selection semantics: profiles are server-owned,
  selected on `start`, and unknown domains are rejected before streaming.
- Domain profile edits are exposed through `/api/domain-profiles`; they affect
  future streams and should preserve validation/persistence behavior.
- Use `docs/WEBSOCKET_CLIENT_CONTRACT.md` as the integration contract for
  browser, desktop, mobile, CLI, and backend websocket clients.
- Preserve `CoreSTT/server.py` compatibility exports including
  `create_app`, `parse_args`, `settings_from_args`, `main`, and
  `ServerSettings`; internal server modules are implementation details.
- Do not weaken runtime config validation, queue limits, session limits, auth or
  secret handling if added later, or error reporting.
- Do not edit generated caches, virtualenvs, model downloads, or local `.env`
  files.

## Unknowns / To Verify

- Whether the missing `medical-dictation/` tree is expected in this checkout.
- Whether all tests pass after installing `CoreSTT/requirements.txt` in
  `CoreSTT/.venv`.
