# Commands

Only commands verified from `CoreSTT/README.md`, `CoreSTT/requirements.txt`,
tests, or `.github/workflows/medical-dictation-pipeline.yml`.

## Setup

From `CoreSTT/`:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

After the virtualenv exists, prefer explicit `.venv` commands from `CoreSTT/`:

```bash
.venv/bin/python -m pip install -r requirements.txt
```

On Windows, from `CoreSTT/`:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

macOS PyAudio prerequisite:

```bash
brew install portaudio
```

## Run

From `CoreSTT/`:

```bash
python server.py --host 127.0.0.1 --port 8020 --device cpu
```

Open:

```text
http://127.0.0.1:8020
```

## Test

Focused tests from `CoreSTT/`:

```bash
.venv/bin/python -m unittest tests/test_server_protocol.py
.venv/bin/python -m unittest tests/test_server_config.py
```

Discover all current `unittest` tests from `CoreSTT/`:

```bash
.venv/bin/python -m unittest discover tests
```

Stress harness tests from `CoreSTT/`:

```bash
.venv/bin/python -m unittest tests/test_stress_harness.py
```

Create `CoreSTT/.venv` and install `requirements.txt` before running tests.
Server tests import runtime dependencies such as `numpy`.

## Lint / Typecheck / Build

No local lint, typecheck, or build command was found for the current `CoreSTT`
tree.

The current GitHub Actions workflow validates a missing `medical-dictation/`
tree with backend `unittest`/`compileall` and frontend `pnpm` commands. Treat
that workflow as `To verify` for this checkout.

## Smoke Checks

After starting the server:

```text
GET http://127.0.0.1:8020/health
GET http://127.0.0.1:8020/api/config
GET http://127.0.0.1:8020/api/metrics
```

Stress-test harness from `CoreSTT/`:

```bash
.venv/bin/python -m tools.stress.harness --url ws://127.0.0.1:8020/ws/transcribe --clients 25 --duration 30 --mode handshake --ping-interval 2 --metrics
.venv/bin/python -m tools.stress.harness --url ws://127.0.0.1:8020/ws/transcribe --clients 10 --duration 20 --mode stream --chunk-ms 100 --ping-interval 2
```

## Notes

- Installing requirements can download large ML/audio dependencies.
- Server/model smoke checks may download or load ASR models depending on
  selected engine and model settings.
- In the current shell, `python` was not found; `python3` exists but test
  discovery failed before server tests because `numpy` is not installed.
- Future validation should use `CoreSTT/.venv/bin/python` once the virtualenv is
  created.
