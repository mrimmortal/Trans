# Module Map

Use this file to avoid scanning the full repo.

## Work Area Map

| Work area | Start here | Related tests | Notes |
|---|---|---|---|
| Public recorder API | `CoreSTT/CoreSTT/audio_recorder.py`, `CoreSTT/CoreSTT/__init__.py` | To verify | Keep the constructor signature stable unless explicitly changing the public API. |
| Recorder internals | `CoreSTT/CoreSTT/core/` | To verify | Lifecycle, VAD, buffering, realtime callbacks, wake-word, text formatting, and transcription orchestration. |
| ASR engine adapters | `CoreSTT/CoreSTT/transcription_engines/` | To verify | Use the existing factory/adapter pattern before adding engines or options. |
| FastAPI server | `CoreSTT/server.py` | `CoreSTT/tests/test_server_config.py` | HTTP endpoints, websocket sessions, scheduler settings, runtime config updates, metrics. |
| Browser audio protocol | `CoreSTT/protocol.py` | `CoreSTT/tests/test_server_protocol.py`, `CoreSTT/tests/test_server_config.py` | Binary packet helpers and JSON/config parsing used by server and UI. |
| Browser console UI | `CoreSTT/static/index.html` | `CoreSTT/tests/test_server_config.py` covers serving index | Microphone console for live transcript, session state, events, metrics, and config display. |
| Setup/runtime docs | `CoreSTT/README.md`, `CoreSTT/requirements.txt` | To verify | README is the current source for setup, run, endpoints, and package usage. |
| CI/deployment | `.github/workflows/medical-dictation-pipeline.yml` | To verify | Workflow targets `medical-dictation/`, which is not present in this checkout. |

## Do-Not-Break Boundaries

- Public APIs: `CoreSTT.__all__`, lazy exports in `CoreSTT/CoreSTT/__init__.py`,
  and `AudioToTextRecorder` constructor arguments.
- Protocols/message contracts: `CoreSTT/protocol.py`, `WS /ws/transcribe`, and
  server runtime config request/response behavior.
- Config/env names: server CLI options and runtime setting names in
  `CoreSTT/server.py`.
- Storage/schema: no persistent storage schema detected.
- Runtime behavior: recorder lifecycle, VAD/wake-word timing, scheduler queue
  limits, and engine selection/defaults.

## Documentation Pointers

- Start with `AI_CONTEXT.md` for repo orientation.
- Use `docs/COMMANDS.md` for local setup/run/test commands.
- Use `CoreSTT/README.md` for user-facing package/server examples.
