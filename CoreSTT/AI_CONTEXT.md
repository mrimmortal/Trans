# AI Context

## Project Summary

`CoreSTT` is a standalone speech-to-text package plus browser streaming server.
The server is a CoreSTT-adapted FastAPI version of the richer RealtimeSTT
browser server.

## Current App

- Package: `CoreSTT/`
- Server entrypoint: `server.py`
- Browser UI: `static/index.html`
- Browser audio packet helpers: `protocol.py`
- Warmup audio: `CoreSTT/assets/warmup_audio.wav`
- macOS client: `../MacOS/` SwiftUI Swift Package that streams microphone
  audio to `WS /ws/transcribe`.

## Run Command

From this folder:

```bash
python server.py --host 127.0.0.1 --port 8020 --device cpu
```

Open:

```text
http://127.0.0.1:8020
```

## Server Endpoints

- `GET /`: browser console.
- `GET /health`: readiness and scheduler health.
- `GET /api/config`: public settings, limits, supported engines, runtime setting contract.
- `PATCH /api/config`: update supported runtime settings.
- `GET /api/metrics`: sessions, queues, inference latency, and limits.
- `WS /ws/transcribe`: binary browser audio stream plus JSON commands.

## Validation

Run focused server tests:

```bash
.venv/bin/python -m unittest tests/test_server_config.py tests/test_server_protocol.py
```

Compile the standalone package and server:

```bash
.venv/bin/python -m compileall CoreSTT server.py protocol.py
```

Run the macOS client validation from `../MacOS`:

```bash
swift test
swift build
```
