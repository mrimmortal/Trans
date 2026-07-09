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
- `GET /api/metrics`: session, scheduler, queue, latency, and limit metrics.
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

- final model: `small.en`
- realtime model: `tiny.en`
- backend: `faster_whisper`
- device: `cuda` by default, with server-side fallback to CPU when CUDA is not available

For better accuracy, use a larger model and GPU when available.

## Server Features

- FastAPI app served on one port.
- Multi-session websocket admission with `--max-sessions`.
- Active speaker throttling with `--max-active-speakers`.
- Shared main/realtime inference workers with fair per-session queueing.
- Realtime job coalescing and stale interim update dropping.
- Configurable final/realtime engines, models, prompts, beam sizes, batch sizes,
  VAD timing, wake-word settings, and queue limits.
- Server-owned domain profiles for per-session prompts and faster-whisper
  hotwords.
- Named tuning profiles for Parakeet latency/quality tradeoffs.
- Wake-word states and timeline events when wake words are enabled.
- Runtime config update endpoint for active-session-safe and new-session-only settings.
- Metrics for sessions, queues, inference latency, scheduler health, and dropped work.
