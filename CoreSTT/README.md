# CoreSTT

Standalone speech-to-text core for reuse in another application. The package,
demo server, browser UI, and dependency list are contained inside this folder.

## What Is Included

- `CoreSTT/`: isolated Python package.
- `CoreSTT/audio_recorder.py`: main `AudioToTextRecorder` entry point.
- `CoreSTT/core/`: recorder lifecycle, VAD, buffering, realtime processing, and transcription flow.
- `CoreSTT/transcription_engines/`: ASR engine adapters and factory.
- `static/index.html`: full browser microphone console with live transcript,
  signal history, session state, timeline events, metrics, and config display.
- `protocol.py`: binary browser audio packet helpers used by the server.
- `server.py`: standalone FastAPI/uvicorn browser streaming server.

## Install

From this folder:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On Windows:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

PyAudio may need PortAudio installed first. On macOS:

```bash
brew install portaudio
```

## Run Server

```bash
python server.py --host 127.0.0.1 --port 8020 --device cpu
```

Open:

```text
http://127.0.0.1:8020
```

Click `Start` and allow microphone access.

Useful endpoints:

- `GET /`: browser console.
- `GET /health`: readiness, active sessions, scheduler health, and startup errors.
- `GET /api/config`: public settings, limits, supported engines, and runtime setting contract.
- `PATCH /api/config`: update supported runtime settings.
- `GET /api/metrics`: session, scheduler, queue, latency, resource,
  diagnostic, and limit metrics.
- `WS /ws/transcribe`: browser audio streaming websocket.

## Use In Your Project

Copy this whole `CoreSTT` folder into another project, install
`requirements.txt`, then import:

```python
from CoreSTT import AudioToTextRecorder

with AudioToTextRecorder(
    model="small.en",
    device="cpu",
    language="en",
) as recorder:
    print(recorder.text())
```

For browser or external audio:

```python
from CoreSTT import AudioToTextRecorder

recorder = AudioToTextRecorder(
    model="small.en",
    device="cpu",
    language="en",
    use_microphone=False,
    enable_realtime_transcription=True,
    realtime_model_type="tiny.en",
)

recorder.feed_audio(audio_bytes, original_sample_rate=48000)
text = recorder.text()
```

## Domain Profiles

The browser/WebSocket server can bias transcription for named domains using
`domain_profiles.json`. Profiles provide final/realtime prompts and
`faster_whisper` hotwords without changing model weights.

Example client start command:

```json
{ "type": "start", "domain": "medical" }
```

The bundled `medical` profile includes clinical prompt text and example
hotwords such as `hypertension`, `metformin`, `dyspnea`, `myocardial
infarction`, and `hemoglobin A1c`. Unknown domains are rejected before
streaming starts.

## Default Model Path

The server uses:

- final model: `small.en` (fixed for final jobs)
- realtime model: `tiny.en` (fixed for realtime jobs)
- backend: `faster_whisper`
- device: `cuda` by default, with server-side fallback to CPU when CUDA is not available
- Faster-Whisper VAD: enabled for final jobs and disabled for realtime jobs

`device` and `compute_type` remain configurable. Server CLI defaults are read
from `ServerSettings`, so changing the defaults in `settings.py` affects
startup unless a CLI flag overrides them. The production WebSocket pipeline
loads both models once at startup and reuses them across sessions.
Faster-Whisper startup controls include `--cpu-threads`, `--num-workers`, and
`--single-gpu-inference-gate`/`--no-single-gpu-inference-gate` for tuning CPU
threading and same-GPU final/realtime contention.
Use `--no-realtime-transcription` for final-only mode. This disables the
interim realtime transcription pipeline while keeping speech detection,
final-utterance buffering, and final transcription active.

## Server Features

- FastAPI app served on one port.
- Multi-session websocket admission with `--max-sessions`.
- Active speaker throttling with `--max-active-speakers`.
- Dedicated final/realtime inference workers with final-priority scheduling.
- Optional same-GPU inference gating so queued final jobs block new realtime
  inference until final work drains.
- Realtime job coalescing, segment-aware cancellation, and stale interim update dropping.
- Optional realtime transcription disable flag for final-only operation.
- `RealtimeSession` production pipeline with a bounded five-second realtime
  ring buffer and a separate complete final-utterance buffer.
- Configurable final/realtime engines, prompts, beam sizes, batch sizes, VAD
  timing, wake-word settings, device/compute settings, and queue limits.
- Server-owned domain profiles for per-session prompts and faster-whisper
  hotwords.
- Named tuning profiles for Parakeet latency/quality tradeoffs.
- Wake-word states and timeline events when wake words are enabled.
- Runtime config update endpoint for active-session-safe and new-session-only settings.
- Metrics for sessions, queues, inference latency, resource pressure,
  scheduler health, and dropped work.
- Browser diagnostics dashboard with threshold coloring, bottleneck hints, and
  local JSON/JSONL/CSV export.
