# CoreSTT

Standalone speech-to-text core for reuse in another application. The package,
demo server, browser UI, and dependency list are contained inside this folder.

## What Is Included

- `CoreSTT/`: isolated Python package.
- `CoreSTT/audio_recorder.py`: main `AudioToTextRecorder` entry point.
- `CoreSTT/core/`: recorder lifecycle, VAD, buffering, realtime processing, and transcription flow.
- `CoreSTT/transcription_engines/`: ASR engine adapters and factory.
- `static/index.html`: minimal browser microphone UI.
- `server.py`: standalone HTTP and websocket demo server.

## Choose CPU Or CUDA

Install the shared requirements and then exactly one runtime requirements
file:

- `requirements-cpu.txt`: CPU-only PyTorch, works without an NVIDIA GPU.
- `requirements-cuda.txt`: NVIDIA CUDA 12.8 PyTorch for supported Windows and
  Linux systems.
- `requirements.txt`: shared dependencies only; it intentionally does not
  choose a PyTorch runtime.

## CPU Setup

From this folder:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -r requirements-cpu.txt
```

On Windows:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -r requirements-cpu.txt
```

PyAudio may need PortAudio installed first. On macOS:

```bash
brew install portaudio
```

## CUDA Setup

For an NVIDIA GPU with a compatible current driver:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -r requirements-cuda.txt
```

On Windows:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -r requirements-cuda.txt
```

Verify PyTorch can see CUDA:

```bash
python -c "import torch; print('CUDA:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'none')"
```

CoreSTT accepts `STT_DEVICE=auto|cuda|cpu` and defaults to `auto`.

Linux/macOS:

```bash
STT_DEVICE=auto python server.py
```

Windows PowerShell:

```powershell
$env:STT_DEVICE = "auto"
python server.py
```

The CUDA requirements use PyTorch's official CUDA 12.8 wheel index. This
matches the CUDA 12 cuBLAS runtime required by CTranslate2/faster-whisper. A newer
NVIDIA driver can run this CUDA runtime; a separate system CUDA Toolkit is not
required for the wheel. For other CUDA wheel versions, use the command from
the [PyTorch installation selector](https://pytorch.org/get-started/locally/).

`cuda` requests GPU execution but safely logs a warning and falls back to CPU
when CUDA is unavailable. `cpu` always disables GPU model execution.

## Run Demo

```bash
python server.py --host 127.0.0.1 --port 8020 --ws-port 8021
```

Open:

```text
http://127.0.0.1:8020
```

Click `Start` and allow microphone access.

## Use In Your Project

Copy this whole `CoreSTT` folder into another project, install
`requirements.txt`, then install either `requirements-cpu.txt` or
`requirements-cuda.txt` before importing:

```python
from CoreSTT import AudioToTextRecorder

with AudioToTextRecorder(
    model="small.en",
    device="auto",
    language="en",
) as recorder:
    print(recorder.text())
```

For browser or external audio:

```python
from CoreSTT import AudioToTextRecorder

recorder = AudioToTextRecorder(
    model="small.en",
    device="auto",
    language="en",
    use_microphone=False,
    enable_realtime_transcription=True,
    realtime_model_type="tiny.en",
)

recorder.feed_audio(audio_bytes, original_sample_rate=48000)
text = recorder.text()
```

## Startup Logs

With `level=logging.INFO`, startup includes messages like:

```text
STT device request: auto (source: AudioToTextRecorder device setting)
PyTorch CUDA available: True
STT processing will run on: CUDA (GPU 0: NVIDIA GeForce RTX 3060)
```

CPU fallback:

```text
CUDA was requested but is unavailable; falling back to CPU.
PyTorch CUDA available: False
STT processing will run on: CPU
```

## Default Model Path

The demo uses:

- final model: `small.en`
- realtime model: `tiny.en`
- backend: `faster_whisper`
- device: `auto`

PyTorch-backed engines use inference mode and keep CPU inference in fp32.
CUDA engines may use a supported reduced precision through `compute_type`.

If faster-whisper reports that `cublas64_12.dll` is missing, reinstall the
CUDA runtime file. Do not use the CUDA 13.0 PyTorch wheel with the current
CTranslate2 build:

```powershell
python -m pip install --force-reinstall -r requirements-cuda.txt
```

## Checks

Fast checks that do not download a model:

```bash
python -m unittest discover -s tests -v
python -m compileall -q CoreSTT server.py
```

There is currently no Dockerfile in this standalone project. If container
support is added later, keep a normal CPU image/run path and document GPU runs
with NVIDIA Container Toolkit and Docker's `--gpus all` option.

See `AI_AGENT_GUIDE.md` and the repository-level `AGENTS.md` for maintenance
notes.
