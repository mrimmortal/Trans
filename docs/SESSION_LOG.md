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
