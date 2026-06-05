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

## Default Model Path

The demo uses:

- final model: `small.en`
- realtime model: `tiny.en`
- backend: `faster_whisper`
- device: `cpu`

For better accuracy, use a larger model and GPU when available.
