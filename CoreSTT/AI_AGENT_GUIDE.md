# AI Agent Guide

## Runtime Flow

`AudioToTextRecorder` collects constructor arguments, then
`core.initialization.initialize_recorder()` resolves the execution device.
The selected `cpu` or `cuda` value is passed to both:

- the final transcription worker in `core/transcription.py`
- the optional realtime engine created in `core/initialization.py`

Engine construction is routed through
`transcription_engines/factory.py`. The default backend is
`faster_whisper`, which uses CTranslate2. Other adapters may use PyTorch,
ONNX Runtime, native libraries, or remote APIs.

## Device Rules

`core/device.py` is the source of truth for automatic selection. Do not add
backend-specific CUDA detection unless a backend has a separate runtime that
cannot use the resolved recorder device.

PyTorch adapters share dtype and inference helpers in
`transcription_engines/_model_utils.py`. CPU tensors must remain fp32.
Reduced precision is allowed only for CUDA models that support it.

Silero VAD has separate backend selection. Its `auto` mode intentionally
prefers CPU ONNX for short VAD chunks and should not be coupled to the STT
model device.

Dependency runtime files:

- `requirements.txt` contains shared dependencies and no Torch runtime.
- `requirements-cpu.txt` selects official CPU Torch wheels after the shared
  requirements are installed.
- `requirements-cuda.txt` selects official CUDA 12.8 Torch wheels after the
  shared requirements are installed.

Install only one runtime file in an environment. Do not add CUDA-only Torch
packages to the shared requirements or include shared packages under the
PyTorch-only package index.

## Testing

Fast checks:

```powershell
python -m unittest discover -s tests -v
python -m compileall -q CoreSTT server.py
```

Before real CUDA testing, verify:

```powershell
python -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
```

Then run the demo with `STT_DEVICE=auto`, `STT_DEVICE=cuda`, and
`STT_DEVICE=cpu` to exercise selection and fallback behavior.
