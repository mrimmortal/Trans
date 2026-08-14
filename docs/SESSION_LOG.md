# Session Log

Keep entries compact and useful for future continuation.

## 2026-07-09 - Update Radiology Domain Profile

Changed:
- Enriched `medical_radiology` hotwords and prompts with imaging modalities,
  report sections, views, comparison terms, anatomy, findings, and impression
  language while keeping composed profile size within limits.

Validation:
- Parsed and loaded `CoreSTT/domain_profiles.json`; confirmed
  `medical_radiology` has 48 domain hotwords, 90 final composed hotwords,
  48 realtime hotwords, no duplicates, and prompt sizes within limits.
- `.venv/bin/python -m unittest tests/test_server_config.py` from `CoreSTT/`:
  passed, 19 tests.

## 2026-07-09 - Use Domain-Only Realtime Biasing

Changed:
- Split domain profile composition so final transcription keeps `global +
  domain`, while realtime transcription uses only the selected domain profile's
  realtime prompt and hotwords.
- Added focused server config assertions for domain-only realtime prompt and
  realtime hotwords.

Validation:
- `.venv/bin/python -m unittest tests/test_server_config.py` from `CoreSTT/`:
  passed, 19 tests.
- Measured composed profiles to confirm final hotwords stay composed while
  realtime hotwords are domain-only.

## 2026-07-09 - Trim Composed Profile Sizes

Changed:
- Trimmed `medical_en_clinical` and `medical_prescription` hotwords so
  effective `global + domain` compositions stay at or below 90 active hotwords.

Validation:
- Parsed and loaded `CoreSTT/domain_profiles.json`; confirmed no composed
  domain profile exceeds 90 active hotwords and no profile has duplicate
  hotwords.
- `.venv/bin/python -m unittest tests/test_server_config.py` from `CoreSTT/`:
  passed, 19 tests.

## 2026-07-09 - Enrich Medical Domain Profiles

Changed:
- Added 20 medical specialty/document profiles to `CoreSTT/domain_profiles.json`
  including pediatrics, dermatology, ENT, ophthalmology, urology, nephrology,
  endocrinology, psychiatry, dentistry, surgery, anesthesia, ICU, infectious
  disease, rheumatology, physiotherapy, pathology, procedure note, referral
  letter, follow-up note, and operative note.
- Kept each new profile on the existing `hotwords`, `initial_prompt`, and
  `initial_prompt_realtime` schema.

Validation:
- Parsed `CoreSTT/domain_profiles.json`, confirmed all 20 profiles exist, each
  has at least 25 hotwords, no duplicate hotwords within profiles, and loading
  through `load_domain_profiles` succeeds.
- `.venv/bin/python -m unittest tests/test_server_config.py` from `CoreSTT/`:
  passed, 19 tests.

## 2026-07-09 - Clean Domain Profile Duplicates

Changed:
- Removed redundant `command_only` profile because `global` already owns shared
  command hotwords.
- Cleared duplicate command hotwords from `medical_command_en` while preserving
  its medical-command prompt.

Validation:
- Parsed `CoreSTT/domain_profiles.json` and checked duplicate JSON keys,
  duplicate hotwords within profiles, and key command-profile overlaps.
- Loaded profiles through `load_domain_profiles` and composed `global` with
  `medical_command_en`.

## 2026-07-09 - Compose Global And Domain Profiles

Changed:
- Added reserved `global` domain profile composition so sessions use global
  command prompt/hotwords alone or prepend them to a selected domain profile.
- Moved command vocabulary in `CoreSTT/domain_profiles.json` into `global` and
  kept `medical_en_clinical` focused on medical terminology.
- Added focused server config tests for global-only, global-plus-domain,
  duplicate hotword handling, and missing-global compatibility.

Validation:
- `.venv/bin/python -m unittest tests/test_server_config.py` from `CoreSTT/`:
  passed, 19 tests.

## 2026-07-08 - Add Audio Processing Context Doc

Changed:
- Added `docs/AUDIO_PROCESSING.md` with the current audio packet flow,
  internal sample assumptions, realtime/final paths, tuning knobs, validation
  commands, and boundaries.
- Expanded `docs/AUDIO_PROCESSING.md` with project-specific audio terminology.
- Narrowed `docs/AUDIO_PROCESSING.md` to terminology and settings used by the
  current faster-whisper flow.
- Updated `docs/WEBSOCKET_CLIENT_CONTRACT.md` examples and error handling to
  show domain profile fields consistently.
- Added domain profile management API support with `GET`, `PUT`, and `DELETE`
  `/api/domain-profiles`, persisted profile updates, and
  `domain_profiles_updated` websocket broadcasts.
- Updated `AI_CONTEXT.md`, `docs/MODULE_MAP.md`, and
  `docs/WEBSOCKET_CLIENT_CONTRACT.md` for the profile management API.

Validation:
- `.venv/bin/python -m unittest tests/test_server_config.py` from `CoreSTT/`:
  passed, 16 tests.

## 2026-07-01 - Add Domain Prompt And Hotword Profiles

Changed:
- Added server-owned domain profile loading from `CoreSTT/domain_profiles.json`.
- Added WebSocket `start.domain` selection for per-session prompt and
  faster-whisper hotword biasing.
- Exposed available domain profile names through config/handshake payloads.
- Included selected domain names in status, metrics, and timeline diagnostic
  payloads.
- Added browser console domain selection populated from WebSocket
  `domainProfiles`; selected domains are sent in the `start` command and shown
  in runtime/event diagnostics.
- Added an INFO startup log through the uvicorn terminal logger for each stream
  showing `domain=<name>` or `domain=default`.
- Wired `faster_whisper` `hotwords` passthrough and documented the contract.

Validation:
- `.venv/bin/python -m unittest tests/test_server_config.py` from `CoreSTT/`:
  passed, 13 tests.
- `.venv/bin/python -m unittest tests/test_server_protocol.py` from `CoreSTT/`:
  passed, 5 tests.
- `.venv/bin/python -m unittest tests/test_faster_whisper_engine.py` from
  `CoreSTT/`: passed, 3 tests.
- `.venv/bin/python -m unittest tests/test_inference_worker.py` from `CoreSTT/`:
  passed, 1 test.
- `.venv/bin/python -m unittest discover tests` from `CoreSTT/`: passed, 27
  tests.

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

## 2026-07-13 - Separate Realtime and Final Transcription

Changed:
- Made `RealtimeSession` the default WebSocket production pipeline and retained
  `RecorderBackedRealtimeSession` as an explicit opt-in.
- Fixed realtime/final model roles to `tiny.en`/`small.en`, split their
  Faster-Whisper VAD settings, and applied the requested latency defaults.
- Added a bounded realtime ring buffer, complete final buffer, targeted
  realtime cancellation, final-priority scheduling, late-result suppression,
  and per-job performance logging.
- Preserved WebSocket message and audio packet contracts, including a
  deprecated shared VAD settings alias.

Validation:
- Focused inference, server configuration, and protocol tests passed (37
  tests).
- Full `.venv/bin/python -m unittest discover tests` passed (45 tests).

## 2026-07-14 - Add Faster-Whisper Startup Speed Controls

Changed:
- Added startup-only `cpu_threads`, `num_workers`, and
  `single_gpu_inference_gate` settings with CLI flags.
- Passed thread/worker controls into Faster-Whisper model construction.
- Added a same-GPU inference gate so queued or active final work blocks new
  realtime inference while allowing running realtime inference to finish.
- Added focused config, scheduler, gate, and Faster-Whisper adapter tests.

Validation:
- `.venv/bin/python -m unittest tests.test_server_config tests.test_inference_worker tests.test_faster_whisper_engine`
  from `CoreSTT/`: passed, 40 tests.
- `.venv/bin/python -m unittest discover tests` from `CoreSTT/`: passed, 50
  tests.

## 2026-07-14 - Add Realtime Transcription Disable Flag

Changed:
- Added `realtime_transcription_enabled` with CLI
  `--realtime-transcription`/`--no-realtime-transcription`.
- Disabling realtime transcription stops the interim realtime pipeline while
  preserving WebRTC speech detection, final-utterance buffering, and final
  transcription.
- Covered direct and recorder-backed session suppression paths, including
  disabled direct-session realtime ring buffering.

Validation:
- `.venv/bin/python -m unittest tests.test_server_config` from `CoreSTT/`:
  passed, 31 tests.
- `.venv/bin/python -m unittest discover tests` from `CoreSTT/`: passed, 54
  tests.

## 2026-07-14 - Forward Compute Type Through Deploy Scripts

Changed:
- Confirmed CLI and scheduler already pass `compute_type` into both final and
  realtime model configs at startup.
- Added `COMPUTE_TYPE` support to macOS/Linux deploy scripts and `-ComputeType`
  support to the Windows deploy script.
- Updated deploy/run docs and tests so script-based launches no longer fall
  back silently to `compute_type=default`.

Validation:
- `python3 -m unittest tests.test_deploy_script` from repo root: passed, 5
  tests.
- `.venv/bin/python -m unittest tests.test_server_config tests.test_inference_worker`
  from `CoreSTT/`: passed, 40 tests.
- `.venv/bin/python -m unittest discover tests` from `CoreSTT/`: passed, 54
  tests.

## 2026-07-14 - Make Server CLI Defaults Follow ServerSettings

Changed:
- Updated server CLI parser defaults to derive from `ServerSettings()` instead
  of hardcoded argparse defaults.
- Added a regression test so changing `ServerSettings.compute_type` changes the
  default startup compute type when `--compute-type` is omitted.
- Explicit CLI arguments still override `settings.py` defaults.

Validation:
- `.venv/bin/python -m unittest tests.test_server_config tests.test_inference_worker`
  from `CoreSTT/`: passed, 41 tests.
- `python3 -m unittest tests.test_deploy_script` from repo root: passed, 5
  tests.
- `.venv/bin/python -m unittest discover tests` from `CoreSTT/`: passed, 55
  tests.

## 2026-07-14 - Add Diagnostics Dashboard and Resource Metrics

Changed:
- Added resource monitoring for process CPU/RAM, system memory/load, and
  CUDA memory with graceful fallback.
- Added `resources`, `thresholds`, and deterministic `diagnostics` to
  `/api/metrics`.
- Added resource fields and gate wait timing to per-inference logs.
- Added an in-browser diagnostics dashboard with threshold coloring,
  bottleneck hints, and local JSON/JSONL/CSV exports.
- Added monitoring settings for resource collection and log interval.

Validation:
- `.venv/bin/python -m unittest tests.test_monitoring tests.test_server_config tests.test_inference_worker`
  from `CoreSTT/`: passed, 46 tests.
- `.venv/bin/python -m unittest discover tests` from `CoreSTT/`: passed, 60
  tests.

## 2026-07-14 - Show Realtime Dashboard Log and Category Availability

Changed:
- Added a realtime diagnostics log table to the browser dashboard.
- Each dashboard category now shows live values plus explicit availability or
  unavailable reasons.
- The log keeps the latest browser-collected diagnostics samples visible while
  exports still include the full capped sample set.

Validation:
- `.venv/bin/python -m unittest tests.test_server_config` from `CoreSTT/`:
  passed, 33 tests.
- `.venv/bin/python -m unittest discover tests` from `CoreSTT/`: passed, 60
  tests.

## 2026-07-14 - Add Diagnostic Logging Toggle

Changed:
- Added `diagnostic_logging_enabled`, default false.
- Added CLI `--diagnostic-logging`/`--no-diagnostic-logging`.
- Dashboard and `/api/metrics` remain available with the flag off.
- Startup/periodic resource logs and per-inference CPU/RAM/CUDA log fields are
  emitted only when diagnostic logging is enabled.
- Per-inference terminal performance logs are also emitted only when diagnostic
  logging is enabled.
- Dashboard diagnostics polling and expensive `/api/metrics` resource
  collection/diagnosis are disabled when diagnostic logging is disabled.

Validation:
- `.venv/bin/python -m unittest tests.test_server_config tests.test_inference_worker`
  from `CoreSTT/`: passed, 43 tests.
- `.venv/bin/python -m unittest tests.test_server_config tests.test_inference_worker tests.test_monitoring`
  from `CoreSTT/`: passed, 47 tests.
- `.venv/bin/python -m unittest discover tests` from `CoreSTT/`: passed, 61
  tests.
- `git diff --check`: passed.

## 2026-08-14 - Fully Disable Realtime Resources in Final-Only Mode

Changed:
- Made `realtime_transcription_enabled` startup-only.
- Final-only mode no longer creates a realtime queue, inference worker, model
  load/warmup path, CUDA gate, recorder executor/callback, or recorder realtime
  thread.
- Added defensive rejection for realtime jobs and a `final-only` scheduler
  metrics mode while preserving final transcription.
- Added focused scheduler, configuration, and recorder regression coverage.

Validation:
- `.venv/bin/python -m unittest tests.test_inference_worker tests.test_server_config`
  from `CoreSTT/`: passed, 46 tests.
- `.venv/bin/python -m unittest discover tests` from `CoreSTT/`: passed, 64
  tests.
- `git diff --check`: passed.
