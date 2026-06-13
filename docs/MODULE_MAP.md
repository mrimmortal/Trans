# Module Map

Use this file to avoid scanning the full repo.

## Work Area Map

| Work area | Start here | Related tests | Notes |
|---|---|---|---|
| Public recorder API | `CoreSTT/CoreSTT/audio_recorder.py`, `CoreSTT/CoreSTT/__init__.py` | To verify | Keep the constructor signature stable unless explicitly changing the public API. |
| Recorder internals | `CoreSTT/CoreSTT/core/` | To verify | Lifecycle, VAD, buffering, realtime callbacks, wake-word, text formatting, and transcription orchestration. |
| ASR engine adapters | `CoreSTT/CoreSTT/transcription_engines/` | To verify | Use the existing factory/adapter pattern before adding engines or options. |
| FastAPI server public entrypoint | `CoreSTT/server.py` | `CoreSTT/tests/test_server_config.py`, `CoreSTT/tests/test_server_protocol.py` | Public compatibility surface, HTTP endpoints, websocket sessions, service wiring, and script entrypoint. |
| Server settings and CLI | `CoreSTT/CoreSTT/server/settings.py`, `CoreSTT/CoreSTT/server/cli.py` | `CoreSTT/tests/test_server_config.py` | `ServerSettings`, runtime config contracts, CLI parsing, and argument-to-settings conversion. Re-exported by `CoreSTT/server.py`. |
| Server audio helpers | `CoreSTT/CoreSTT/server/audio.py` | `CoreSTT/tests/test_server_config.py`, `CoreSTT/tests/test_server_protocol.py` | WAV loading, resampling, audio data containers, and effective device selection used by scheduler/session paths. |
| Server timeline/metrics helpers | `CoreSTT/CoreSTT/server/timeline.py`, `CoreSTT/CoreSTT/server/stats.py`, `CoreSTT/CoreSTT/server/connection.py` | `CoreSTT/tests/test_server_config.py`, `CoreSTT/tests/test_server_protocol.py` | Segment timeline state, running statistics, and websocket connection tracking. |
| Server inference scheduler | `CoreSTT/CoreSTT/server/inference.py` | `CoreSTT/tests/test_server_config.py`, `CoreSTT/tests/test_server_protocol.py` | Fair inference queue, shared engine worker, scheduler, and transcription executor. Preserve queue and threading behavior. |
| Browser audio protocol | `CoreSTT/protocol.py` | `CoreSTT/tests/test_server_protocol.py`, `CoreSTT/tests/test_server_config.py` | Binary packet helpers and JSON/config parsing used by server and UI. |
| Browser console UI | `CoreSTT/static/index.html` | `CoreSTT/tests/test_server_config.py` covers serving index | Microphone console for live transcript, session state, events, metrics, and config display. |
| Stress testing harness | `CoreSTT/tools/stress/harness.py` | `CoreSTT/tests/test_stress_harness.py` | Standalone websocket load generator for handshake-only or synthetic audio streaming sessions. Does not change server runtime behavior. |
| Setup/runtime docs | `CoreSTT/README.md`, `CoreSTT/requirements.txt` | To verify | README is the current source for setup, run, endpoints, and package usage. |
| CI/deployment | `.github/workflows/medical-dictation-pipeline.yml` | To verify | Workflow targets `medical-dictation/`, which is not present in this checkout. |

## Do-Not-Break Boundaries

- Public APIs: `CoreSTT.__all__`, lazy exports in `CoreSTT/CoreSTT/__init__.py`,
  and `AudioToTextRecorder` constructor arguments.
- Protocols/message contracts: `CoreSTT/protocol.py`, `WS /ws/transcribe`, and
  server runtime config request/response behavior.
- Config/env names: server CLI options and runtime setting names in
  `CoreSTT/server.py` and `CoreSTT/CoreSTT/server/settings.py`.
- Server compatibility: imports from `CoreSTT/server.py` for
  `create_app`, `parse_args`, `settings_from_args`, `main`, `ServerSettings`,
  scheduler classes, and settings constants must continue to work.
- Storage/schema: no persistent storage schema detected.
- Runtime behavior: recorder lifecycle, VAD/wake-word timing, scheduler queue
  limits, and engine selection/defaults.

## Documentation Pointers

- Start with `AI_CONTEXT.md` for repo orientation.
- Use `docs/COMMANDS.md` for local setup/run/test commands.
- Use `CoreSTT/README.md` for user-facing package/server examples.
