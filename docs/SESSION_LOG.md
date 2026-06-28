# Session Log

Keep entries compact and useful for future continuation.

## 2026-06-13 - Bootstrap AI Context Docs

Changed:
- Created initial `AI_CONTEXT.md`, `docs/COMMANDS.md`, and
  `docs/MODULE_MAP.md` for fast Codex routing.
- Documented the current `CoreSTT` Python/FastAPI architecture and the CI
  mismatch with the missing `medical-dictation/` tree.

Validation:
- `python -m unittest discover tests` from `CoreSTT/`: failed because `python`
  is not available in this shell.
- `python3 -m unittest discover tests` from `CoreSTT/`: failed because
  `numpy` is not installed; protocol-only tests loaded before the server import
  failure.
- `python3 -m unittest tests/test_server_protocol.py` from `CoreSTT/`: passed.

Next:
- Verify local `CoreSTT` test commands after dependencies are available.
- Confirm whether `medical-dictation/` should exist in this checkout.

## 2026-06-13 - Prefer `.venv` For Testing

Changed:
- Updated `AI_CONTEXT.md` and `docs/COMMANDS.md` to create `CoreSTT/.venv` and
  run tests through `.venv/bin/python`.

Validation:
- Not run; documentation-only update.

Next:
- Create `CoreSTT/.venv`, install `CoreSTT/requirements.txt`, then run
  `.venv/bin/python -m unittest discover tests` from `CoreSTT/`.

## 2026-06-13 - Run Unit Tests

Changed:
- No runtime code changed.

Validation:
- `.venv/bin/python -m unittest discover tests` from `CoreSTT/`: failed.
- `.venv/bin/python -m unittest tests/test_server_protocol.py` from
  `CoreSTT/`: passed, 5 tests.
- `.venv/bin/python -m unittest tests/test_server_config.py` from `CoreSTT/`:
  failed, 1 failure in
  `test_create_app_serves_index_health_and_config_with_fake_scheduler`.

Next:
- Decide whether the expected index text should be updated in the test or the
  UI should restore `CoreSTT Live Console`.

## 2026-06-13 - Run Server And Smoke Test

Changed:
- No runtime code changed.

Validation:
- Started server with `.venv/bin/python server.py --host 127.0.0.1 --port 8020
  --device cpu --no-model-warmup`; sandboxed bind failed, escalated localhost
  bind succeeded.
- `.venv/bin/python -m unittest discover tests` from `CoreSTT/`: failed on the
  existing index text assertion expecting `CoreSTT Live Console`.
- `GET /`, `GET /health`, `GET /api/config`, and `GET /api/metrics`: passed
  with HTTP 200.
- `WS /ws/transcribe`: passed connection/ping smoke check; observed `status`,
  `hello`, `ready`, then `pong`.
- In-app browser automation was unavailable because `iab` was not available.
- Server was stopped cleanly after testing.

Next:
- Fix or update the stale server config test assertion for the current page
  title `CoreSTT WebSocket Integration`.

## 2026-06-13 - Modularize Server Safe Phases

Changed:
- Added compatibility guard coverage for `CoreSTT/server.py` public exports and
  updated the stale served-index title assertion to the current UI title.
- Extracted server settings/CLI, audio helpers, running stats, timeline state,
  connection tracking, and inference scheduler internals under
  `CoreSTT/CoreSTT/server/`.
- Kept `CoreSTT/server.py` as the public server entrypoint and compatibility
  export surface.
- Updated `AI_CONTEXT.md` and `docs/MODULE_MAP.md` with the new server module
  boundaries.

Validation:
- `.venv/bin/python -m unittest tests/test_server_config.py` from `CoreSTT/`:
  passed, 5 tests.
- `.venv/bin/python -m unittest tests/test_server_protocol.py` from `CoreSTT/`:
  passed, 5 tests.
- `.venv/bin/python -m unittest discover tests` from `CoreSTT/`: passed, 10
  tests.
- Server smoke with `.venv/bin/python server.py --host 127.0.0.1 --port 8020
  --device cpu --no-model-warmup`: passed `/health`, `/api/config`,
  `/api/metrics`, and websocket hello/ready/ping checks.

Next:
- If continuing modularization, extract realtime session/service wiring in
  smaller phases with websocket smoke validation after each phase.

## 2026-06-13 - Add Stress Harness

Changed:
- Added `CoreSTT/tools/stress/harness.py` as a repo-local websocket stress and
  soak test harness with handshake and synthetic audio streaming modes.
- Added focused `unittest` coverage in `CoreSTT/tests/test_stress_harness.py`.
- Updated AI context and command docs for the new harness entrypoint.

Validation:
- `.venv/bin/python -m unittest tests/test_stress_harness.py` from `CoreSTT/`:
  passed, 5 tests.
- `.venv/bin/python -m unittest discover tests` from `CoreSTT/`: passed, 15
  tests.
- `.venv/bin/python -m tools.stress.harness --url ws://127.0.0.1:8020/ws/transcribe --clients 3 --duration 2 --mode handshake --ping-interval 1 --metrics`:
  passed against the live server with 3/3 connects, hello, ready, and pong.
- `.venv/bin/python -m tools.stress.harness --url ws://127.0.0.1:8020/ws/transcribe --clients 1 --duration 2 --mode stream --ping-interval 1`:
  passed against the live server with successful hello, ready, and short audio
  streaming.

Next:
- Use handshake mode first to find session-limit or websocket-admission issues,
  then scale stream mode gradually to measure queue and transcript latency
  degradation.

## 2026-06-14 - Add WebSocket Client Contract

Changed:
- Added `docs/WEBSOCKET_CLIENT_CONTRACT.md` to standardize client-to-server
  WebSocket integration.
- Documented JSON control messages, binary audio packet format, metadata
  schema, platform integration notes, and server response types.
- Updated `AI_CONTEXT.md` and `docs/MODULE_MAP.md` with the new integration
  contract pointer.

Validation:
- Docs-only change; tests not run.
- Checked packet format against `CoreSTT/protocol.py`.
- Checked control messages against `CoreSTT/static/index.html` and
  `CoreSTT/server.py`.
- Checked audio metadata validation rules against `CoreSTT/server.py`.

## 2026-06-28 - Add Deployment Scripts

Changed:
- Rewrote deployment scripts as simple OS-specific entrypoints:
  `deploy-macos.sh`, `deploy-linux.sh`, and `deploy-windows.ps1`.
- Removed the shared Python runner and Node handling.
- Kept the scripts aligned with `docs/COMMANDS.md`: check Python, create
  `CoreSTT/.venv` when missing, install `requirements.txt`, and run
  `server.py`.
- Updated focused deployment script tests and documented script commands.

Validation:
- `python3 -m unittest tests/test_deploy_script.py` from repo root: passed, 5
  tests.

Next:
- Run a full setup with the relevant OS script when dependency downloads are
  approved.
