# CoreSTT Agent Notes

## Scope

The active project is in `CoreSTT/`. Keep changes narrowly focused and do not
edit the local `.venv/` or generated `__pycache__/` files.

## Project Commands

Run commands from `CoreSTT/`:

```powershell
python -m unittest discover -s tests -v
python -m compileall -q CoreSTT server.py
python server.py --host 127.0.0.1 --port 8020 --ws-port 8021
```

Model-backed smoke tests may download large files. Prefer unit tests with fake
backends unless a real-model test is explicitly required.

## CUDA Contract

- `STT_DEVICE=auto|cuda|cpu` overrides the constructor `device` argument.
- `auto` selects CUDA only when `torch.cuda.is_available()` is true.
- A requested but unavailable CUDA device must warn and fall back to CPU.
- CPU PyTorch inference stays in fp32.
- PyTorch inference must use `torch.inference_mode()` or `torch.no_grad()`.
- Keep the normal dependency list compatible with CPU-only installations.
- Keep shared packages in `CoreSTT/requirements.txt`.
- Use `CoreSTT/requirements-cpu.txt` and
  `CoreSTT/requirements-cuda.txt` to select the PyTorch runtime.
- Keep the CUDA runtime on CUDA 12.x while faster-whisper/CTranslate2 requires
  `cublas64_12.dll`; CUDA 13 PyTorch wheels are not runtime-compatible.

## Main Paths

- Public recorder: `CoreSTT/audio_recorder.py`
- Device selection: `CoreSTT/core/device.py`
- Main worker: `CoreSTT/core/transcription.py`
- Realtime model setup: `CoreSTT/core/initialization.py`
- Engine adapters: `CoreSTT/transcription_engines/`
- Demo server: `server.py`
- User documentation: `README.md`
