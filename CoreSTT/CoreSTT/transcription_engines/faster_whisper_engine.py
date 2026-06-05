"""
Adapts faster-whisper models to the transcription engine interface.
"""

from importlib import import_module
import logging
import os
from pathlib import Path

from .base import (
    BaseTranscriptionEngine,
    TranscriptionEngineError,
    TranscriptionInfo,
    TranscriptionResult,
)

logger = logging.getLogger("corestt")


def _prepare_windows_cuda_dlls(config):
    """
    Makes PyTorch's bundled CUDA 12 DLLs visible to CTranslate2 on Windows.
    """
    if os.name != "nt" or not str(config.device).startswith("cuda"):
        return

    try:
        torch = import_module("torch")
    except ModuleNotFoundError:
        return

    torch_lib = Path(torch.__file__).resolve().parent / "lib"
    cublas = torch_lib / "cublas64_12.dll"
    if not cublas.exists():
        raise TranscriptionEngineError(
            "faster-whisper requires CUDA 12 cuBLAS (cublas64_12.dll), but "
            "the installed PyTorch build does not provide it. Install "
            "'requirements-cuda.txt' to use the supported CUDA 12.8 runtime, "
            "or set STT_DEVICE=cpu."
        )

    add_dll_directory = getattr(os, "add_dll_directory", None)
    if add_dll_directory is not None:
        # Keep the handle alive for the process lifetime.
        if not hasattr(_prepare_windows_cuda_dlls, "_dll_handles"):
            _prepare_windows_cuda_dlls._dll_handles = []
        _prepare_windows_cuda_dlls._dll_handles.append(
            add_dll_directory(str(torch_lib))
        )
    logger.info("faster-whisper CUDA DLL directory: %s", torch_lib)


def _load_faster_whisper():
    """
    Loads faster-whisper and its optional batched inference pipeline.
    """
    try:
        faster_whisper = import_module("faster_whisper")
    except ModuleNotFoundError as exc:
        raise TranscriptionEngineError(
            "The 'faster_whisper' transcription engine requires the optional "
            "'faster-whisper' package. Install it with "
            "'pip install \"CoreSTT[faster-whisper]\"' or select a "
            "different transcription engine."
        ) from exc

    return faster_whisper, faster_whisper.BatchedInferencePipeline


class FasterWhisperEngine(BaseTranscriptionEngine):
    """
    Transcribes audio with faster-whisper.
    """

    engine_name = "faster_whisper"

    def __init__(self, config):
        """
        Initializes the faster-whisper model.
        """
        super().__init__(config)
        _prepare_windows_cuda_dlls(config)
        faster_whisper, batched_inference_pipeline = _load_faster_whisper()
        model = faster_whisper.WhisperModel(
            model_size_or_path=self.config.model,
            device=self.config.device,
            compute_type=self.config.compute_type,
            device_index=self.config.gpu_device_index,
            download_root=self.config.download_root,
        )
        if self.config.batch_size > 0:
            model = batched_inference_pipeline(model=model)
        self.model = model

    def transcribe(self, audio, language=None, use_prompt=True):
        """
        Transcribes audio and returns normalized faster-whisper output.
        """
        audio = self._normalize_audio(audio)
        kwargs = {
            "language": language if language else None,
            "beam_size": self.config.beam_size,
            "initial_prompt": self._get_prompt(use_prompt),
            "suppress_tokens": self.config.suppress_tokens,
            "vad_filter": self.config.vad_filter,
        }
        if self.config.batch_size > 0:
            kwargs["batch_size"] = self.config.batch_size

        segments, info = self.model.transcribe(audio, **kwargs)
        text = " ".join(segment.text for segment in segments).strip()
        return TranscriptionResult(
            text=text,
            info=TranscriptionInfo(
                language=getattr(info, "language", None),
                language_probability=getattr(info, "language_probability", 0.0),
            ),
        )
