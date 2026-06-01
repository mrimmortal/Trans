"""Faster-Whisper STT provider with audio processing and validation."""

from app.infrastructure.cuda_bootstrap import configure_windows_cuda_paths

configure_windows_cuda_paths()

import os
import logging
import time
import numpy as np
from typing import Optional
from faster_whisper import WhisperModel

# Silero VAD
try:
    import torch
    torch.set_num_threads(1)  # Reduce CPU usage
    TORCH_AVAILABLE = True
    CUDA_AVAILABLE = torch.cuda.is_available()
    if CUDA_AVAILABLE:
        print(f"✓ PyTorch CUDA available: {torch.cuda.get_device_name(0)}")
    else:
        print("ℹ PyTorch CUDA not available (CTranslate2 CUDA still works)")
except ImportError:
    TORCH_AVAILABLE = False
    CUDA_AVAILABLE = False
    logging.warning("torch not installed - Silero VAD disabled")

from app.audio_config import AudioConfig, config
from app.services.audio_processing import (
    bytes_to_float32,
    preprocess_audio,
    validate_audio,
)
from app.services.stt.config import get_faster_whisper_settings
from app.services.transcription_text import clean_text, filter_hallucinations

logger = logging.getLogger(__name__)


class FasterWhisperSTTProvider:
    """
    Production-grade STT provider using Faster-Whisper with Silero VAD.
    Handles audio validation, preprocessing, VAD, Whisper inference, and post-processing.
    All errors are caught and returned as dict with error key (never raises).
    """

    def __init__(self, config_instance: AudioConfig = None):
        """
        Initialize the transcription engine.

        Args:
            config_instance: AudioConfig instance (defaults to global config).
        """
        self.config = config_instance or config
        self.settings = get_faster_whisper_settings(self.config)
        self.model: Optional[WhisperModel] = None
        
        # Silero VAD components
        self.vad_model = None
        self.get_speech_timestamps = None
        
        # Load models
        self._load_silero_vad()
        self._load_model()

    def _load_silero_vad(self):
        """Load Silero VAD model for real-time speech detection."""
        if not TORCH_AVAILABLE:
            logger.warning("Torch not available - Silero VAD disabled")
            return
        
        try:
            logger.info("Loading Silero VAD model...")
            
            # Load Silero VAD from torch hub
            model, utils = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=False,
                onnx=False
            )
            
            self.vad_model = model
            self.get_speech_timestamps = utils[0]
            
            logger.info("✓ Silero VAD loaded successfully")
            
        except Exception as e:
            logger.warning(f"Failed to load Silero VAD (continuing without it): {e}")
            self.vad_model = None
            self.get_speech_timestamps = None

    def _load_model(self):
        """
        Load the Whisper model from configuration.
        Times the loading process and performs warmup.
        """
        start_time = time.time()
        try:
            logger.info(f"Loading Whisper model: {self.config.MODEL_SIZE}")
            logger.info(f"  Device: {self.config.DEVICE}")
            logger.info(f"  Compute Type: {self.config.COMPUTE_TYPE}")

            self.model = WhisperModel(
                self.config.MODEL_SIZE,
                device=self.config.DEVICE,
                compute_type=self.config.COMPUTE_TYPE,
                cpu_threads=4 if self.config.DEVICE == "cpu" else 1,
                num_workers=1,
            )

            elapsed = time.time() - start_time
            logger.info(f"✓ Model loaded successfully in {elapsed:.2f}s on {self.config.DEVICE.upper()}")

            # Warm up the model to avoid slow first transcription
            self._warmup()

        except RuntimeError as e:
            error_msg = str(e)
            
            # Check for CUDA-specific errors and fallback to CPU
            if "cublas" in error_msg.lower() or "cuda" in error_msg.lower():
                logger.warning(f"CUDA error: {e}")
                logger.warning("Attempting fallback to CPU...")
                
                try:
                    self.config.DEVICE = "cpu"
                    self.config.COMPUTE_TYPE = "int8"
                    
                    self.model = WhisperModel(
                        self.config.MODEL_SIZE,
                        device="cpu",
                        compute_type="int8",
                        cpu_threads=4,
                        num_workers=1,
                    )
                    
                    elapsed = time.time() - start_time
                    logger.info(f"✓ Model loaded on CPU (fallback) in {elapsed:.2f}s")
                    self._warmup()
                    return
                    
                except Exception as cpu_error:
                    logger.error(f"CPU fallback also failed: {cpu_error}")
                    raise
            
            error_msg = (
                f"Failed to load Whisper model '{self.config.MODEL_SIZE}' "
                f"on device '{self.config.DEVICE}': {e}. "
                "Ensure sufficient RAM (base.en needs ~1GB, medium.en needs ~5GB). "
                "Try switching to cpu device or a smaller model."
            )
            logger.error(error_msg)
            raise RuntimeError(error_msg)
            
        except Exception as e:
            logger.error(f"Unexpected error loading model: {e}")
            raise

    def _warmup(self):
        """
        Warmup the model with 1 second of silence to avoid slow first transcription.
        """
        try:
            # Create 1 second of silence (float32)
            silence = np.zeros(self.config.SAMPLE_RATE, dtype=np.float32)

            # Run transcription with minimal beam size
            segments, info = self.model.transcribe(
                silence,
                beam_size=1,
                vad_filter=True,
            )
            
            # Consume the generator
            _ = list(segments)

            logger.info("✓ Model warm-up complete")

        except Exception as e:
            # Non-critical, just log warning
            logger.warning(f"Model warmup encountered issue (non-critical): {e}")

    def detect_speech(self, audio_bytes: bytes) -> dict:
        """
        Detect speech in audio chunk using Silero VAD.
        
        Args:
            audio_bytes: Raw audio data (int16 PCM, 16kHz, mono)
        
        Returns:
            {
                'has_speech': bool,
                'speech_prob': float,  # 0.0 - 1.0
                'speech_segments': list  # [{start, end}]
            }
        """
        if self.vad_model is None:
            # Fallback to RMS-based detection if Silero not available
            return self._detect_speech_rms(audio_bytes)
        
        try:
            # Convert bytes to float32
            audio = self._bytes_to_float32(audio_bytes)
            if audio is None:
                return {'has_speech': False, 'speech_prob': 0.0, 'speech_segments': []}
            
            # Convert to torch tensor
            audio_tensor = torch.from_numpy(audio)
            
            # Silero's low-level model only accepts fixed-size windows:
            # 512 samples at 16 kHz, or 256 samples at 8 kHz.
            speech_prob = self._score_silero_frames(audio_tensor)
            
            # Get detailed speech segments
            speech_timestamps = self.get_speech_timestamps(
                audio_tensor,
                self.vad_model,
                sampling_rate=self.config.SAMPLE_RATE,
                threshold=self.config.SILERO_VAD_THRESHOLD,
                min_speech_duration_ms=self.config.SILERO_MIN_SPEECH_MS,
                min_silence_duration_ms=self.config.SILERO_MIN_SILENCE_MS,
                speech_pad_ms=self.config.SILERO_SPEECH_PAD_MS,
            )
            
            # Convert timestamps to dict format
            segments = []
            for seg in speech_timestamps:
                segments.append({
                    'start': seg['start'],
                    'end': seg['end']
                })
            
            return {
                'has_speech': (
                    speech_prob > self.config.SILERO_VAD_THRESHOLD
                    and (
                        not getattr(self.config, "SILERO_REQUIRE_SEGMENT", False)
                        or len(segments) > 0
                    )
                ),
                'speech_prob': speech_prob,
                'speech_segments': segments
            }
            
        except Exception as e:
            logger.warning(f"Silero VAD error (falling back to RMS): {e}")
            return self._detect_speech_rms(audio_bytes)

    def _score_silero_frames(self, audio_tensor) -> float:
        """Return max Silero speech probability across valid model frames."""
        frame_size = 512 if self.config.SAMPLE_RATE == 16000 else 256
        sample_count = audio_tensor.shape[-1]
        if sample_count == 0:
            return 0.0

        frame_scores = []
        for start in range(0, sample_count, frame_size):
            frame = audio_tensor[start:start + frame_size]
            if frame.shape[-1] < frame_size:
                frame = torch.nn.functional.pad(frame, (0, frame_size - frame.shape[-1]))
            frame_scores.append(self.vad_model(frame, self.config.SAMPLE_RATE).item())

        return max(frame_scores) if frame_scores else 0.0
    
    def _detect_speech_rms(self, audio_bytes: bytes) -> dict:
        """
        Fallback speech detection using RMS energy.
        
        Args:
            audio_bytes: Raw audio data
            
        Returns:
            Simple speech detection result
        """
        audio = self._bytes_to_float32(audio_bytes)
        if audio is None:
            return {'has_speech': False, 'speech_prob': 0.0, 'speech_segments': []}
        
        rms = np.sqrt(np.mean(audio**2))
        has_speech = rms >= self.config.SILENCE_RMS_THRESHOLD
        
        return {
            'has_speech': has_speech,
            'speech_prob': min(rms / 0.1, 1.0),  # Normalize to 0-1
            'speech_segments': []  # RMS doesn't provide segments
        }

    def transcribe_audio_bytes(self, audio_bytes: bytes) -> dict:
        """
        Transcribe audio bytes to text with full processing pipeline.

        PIPELINE (in order):
        1. Validate input (not empty)
        2. Convert bytes to float32 numpy array
        3. Validate audio quality (length, energy, clipping)
        4. Preprocess (DC offset removal, noise reduction, normalization)
        5. Run Whisper inference
        6. Filter hallucinations
        7. Clean text
        8. Return result

        Args:
            audio_bytes: Raw audio data (int16 PCM, 16kHz, mono)

        Returns:
            Dictionary with keys:
            - text: Transcribed text
            - is_final: Whether transcription is complete
            - confidence: 0.0-1.0 confidence score
            - processing_time_ms: Time taken
            - error: Error message if failed (None if success)
        """
        start_time = time.time()

        # ── 1. VALIDATE INPUT ──
        if not audio_bytes or len(audio_bytes) < 100:
            return {
                "text": "",
                "is_final": False,
                "confidence": 0.0,
                "processing_time_ms": 0.0,
                "error": "Audio too short (< 100 bytes)",
            }

        try:
            # ── 2. CONVERT BYTES TO FLOAT32 ──
            audio = self._bytes_to_float32(audio_bytes)
            if audio is None:
                return {
                    "text": "",
                    "is_final": False,
                    "confidence": 0.0,
                    "processing_time_ms": (time.time() - start_time) * 1000,
                    "error": "Failed to decode audio bytes",
                }

            # ── 3. VALIDATE AUDIO QUALITY ──
            validation = self._validate_audio(audio)
            if not validation["is_valid"]:
                return {
                    "text": "",
                    "is_final": False,
                    "confidence": 0.0,
                    "processing_time_ms": (time.time() - start_time) * 1000,
                    "error": validation["reason"],
                }

            # ── 4. PREPROCESS AUDIO ──
            audio = self._preprocess_audio(audio)

            # ── 5. RUN WHISPER ──
            whisper_result = self._run_whisper(audio)
            if whisper_result.get("error"):
                return {
                    "text": "",
                    "is_final": False,
                    "confidence": 0.0,
                    "processing_time_ms": (time.time() - start_time) * 1000,
                    "error": whisper_result["error"],
                }

            # ── 6. FILTER HALLUCINATIONS ──
            text = whisper_result.get("text", "")
            text = self._filter_hallucinations(text)

            # ── 7. CLEAN TEXT ──
            text = self._clean_text(text)

            # ── RETURN RESULT ──
            return {
                "text": text,
                "is_final": whisper_result.get("is_final", True),
                "confidence": whisper_result.get("confidence", 0.0),
                "processing_time_ms": (time.time() - start_time) * 1000,
                "language": whisper_result.get("language", "en"),
                "language_probability": whisper_result.get("language_probability", 0.0),
                "error": None,
            }

        except Exception as e:
            logger.error(f"Unexpected error in transcribe_audio_bytes: {e}", exc_info=True)
            return {
                "text": "",
                "is_final": False,
                "confidence": 0.0,
                "processing_time_ms": (time.time() - start_time) * 1000,
                "error": f"Transcription failed: {str(e)}",
            }

    def _bytes_to_float32(self, audio_bytes: bytes) -> Optional[np.ndarray]:
        """Convert raw int16 PCM bytes to float32 numpy array."""
        return bytes_to_float32(audio_bytes)

    def _validate_audio(self, audio: np.ndarray) -> dict:
        """Validate audio quality for transcription."""
        return validate_audio(audio, self.config)

    def _preprocess_audio(self, audio: np.ndarray) -> np.ndarray:
        """Preprocess float32 audio for Whisper."""
        return preprocess_audio(audio, self.config.SAMPLE_RATE)

    def _run_whisper(self, audio: np.ndarray) -> dict:
        """
        Run Whisper transcription with all production parameters.

        Args:
            audio: Float32 numpy array

        Returns:
            Dict with text, is_final, confidence, language, language_probability, error
        """
        try:
            if self.model is None:
                return {
                    "text": "",
                    "is_final": False,
                    "confidence": 0.0,
                    "error": "Model not loaded",
                }

            # Call Whisper with all parameters
            try:
                segments, info = self.model.transcribe(
                    audio,
                    language=self._get_transcription_language(),
                    beam_size=self.config.BEAM_SIZE,
                    patience=self.config.PATIENCE,
                    best_of=self.config.BEST_OF,
                    temperature=self.config.TEMPERATURE,
                    initial_prompt=self._get_initial_prompt(),
                    compression_ratio_threshold=self.config.COMPRESSION_RATIO_THRESHOLD,
                    log_prob_threshold=self.config.LOG_PROB_THRESHOLD,
                    no_speech_threshold=self.config.NO_SPEECH_THRESHOLD,
                    vad_filter=self.config.VAD_FILTER,
                    vad_parameters=self.config.VAD_PARAMETERS,
                    condition_on_previous_text=False,  # Each chunk is independent in streaming
                    word_timestamps=False,
                )
            except Exception as e:
                logger.error(f"Whisper transcribe call failed: {e}", exc_info=True)
                return {
                    "text": "",
                    "is_final": False,
                    "confidence": 0.0,
                    "error": f"Whisper transcribe call failed: {str(e)}",
                }

            # Iterate segments and collect results
            text_parts = []
            log_probs = []
            no_speech_probs = []
            
            # Get language info from info object
            language = "en"
            language_probability = 0.0
            
            if hasattr(info, 'language'):
                language = info.language
            elif isinstance(info, dict) and 'language' in info:
                language = info['language']
                
            if hasattr(info, 'language_probability'):
                language_probability = info.language_probability
            elif isinstance(info, dict) and 'language_probability' in info:
                language_probability = info['language_probability']

            for segment in segments:
                # Handle both dict and object segment formats
                if hasattr(segment, "text"):
                    text_parts.append(segment.text)
                    if hasattr(segment, "avg_logprob"):
                        log_probs.append(segment.avg_logprob)
                    if hasattr(segment, "no_speech_prob"):
                        no_speech_probs.append(segment.no_speech_prob)
                elif isinstance(segment, dict) and "text" in segment:
                    text_parts.append(segment["text"])
                    if "avg_logprob" in segment:
                        log_probs.append(segment["avg_logprob"])
                    if "no_speech_prob" in segment:
                        no_speech_probs.append(segment["no_speech_prob"])
                else:
                    logger.warning(f"Unexpected segment format: {segment}")

            # Combine text
            text = " ".join(text_parts).strip()

            # Calculate confidence from average log probability
            if log_probs:
                avg_log_prob = np.mean(log_probs)
                confidence = float(np.clip(np.exp(avg_log_prob), 0.0, 1.0))
            else:
                confidence = 1.0 if text else 0.0

            max_no_speech_prob = max(no_speech_probs) if no_speech_probs else 0.0
            if text and max_no_speech_prob >= self.config.HALLUCINATION_MAX_NO_SPEECH_PROB:
                logger.debug(
                    "Filtered hallucination from high no-speech probability: %.2f '%s'",
                    max_no_speech_prob,
                    text,
                )
                text = ""
                confidence = 0.0

            if (
                text
                and confidence < self.config.MIN_TRANSCRIPTION_CONFIDENCE
                and max_no_speech_prob >= (self.config.HALLUCINATION_MAX_NO_SPEECH_PROB * 0.5)
            ):
                logger.debug(
                    "Filtered hallucination from low confidence: %.2f '%s'",
                    confidence,
                    text,
                )
                text = ""

            return {
                "text": text,
                "is_final": True,
                "confidence": confidence,
                "language": language,
                "language_probability": language_probability,
                "error": None,
            }

        except Exception as e:
            logger.error(f"Whisper transcription error: {e}", exc_info=True)
            return {
                "text": "",
                "is_final": False,
                "confidence": 0.0,
                "error": f"Whisper error: {str(e)}",
            }

    def _filter_hallucinations(self, text: str) -> str:
        """Filter common Whisper hallucinations."""
        return filter_hallucinations(text, self.config)

    def _clean_text(self, text: str) -> str:
        """Clean transcribed text."""
        return clean_text(text)

    def transcribe_file(self, file_path: str) -> dict:
        """
        Transcribe an audio file with full context.

        Uses condition_on_previous_text=True (file has full context).
        Same processing pipeline as transcribe_audio_bytes.

        Args:
            file_path: Path to audio file (wav, mp3, flac, etc.)

        Returns:
            Dict with transcription result and error (if any)
        """
        start_time = time.time()

        try:
            if not self.model:
                return {
                    "text": "",
                    "is_final": False,
                    "confidence": 0.0,
                    "processing_time_ms": 0.0,
                    "error": "Model not loaded",
                }

            if not os.path.exists(file_path):
                return {
                    "text": "",
                    "is_final": False,
                    "confidence": 0.0,
                    "processing_time_ms": 0.0,
                    "error": f"File not found: {file_path}",
                }

            logger.info(f"Transcribing file: {file_path}")

            # Run transcription with full context
            segments, info = self.model.transcribe(
                file_path,
                language=self._get_transcription_language(),
                beam_size=self.config.BEAM_SIZE,
                patience=self.config.PATIENCE,
                best_of=self.config.BEST_OF,
                temperature=self.config.TEMPERATURE,
                initial_prompt=self._get_initial_prompt(),
                compression_ratio_threshold=self.config.COMPRESSION_RATIO_THRESHOLD,
                log_prob_threshold=self.config.LOG_PROB_THRESHOLD,
                no_speech_threshold=self.config.NO_SPEECH_THRESHOLD,
                vad_filter=self.config.VAD_FILTER,
                vad_parameters=self.config.VAD_PARAMETERS,
                condition_on_previous_text=True,  # Full context for file transcription
                word_timestamps=False,
            )

            # Iterate segments
            text_parts = []
            log_probs = []

            for segment in segments:
                # Handle both dict and object segment formats
                if hasattr(segment, "text"):
                    text_parts.append(segment.text)
                    if hasattr(segment, "avg_logprob"):
                        log_probs.append(segment.avg_logprob)
                elif isinstance(segment, dict):
                    if "text" in segment:
                        text_parts.append(segment["text"])
                    if "avg_logprob" in segment:
                        log_probs.append(segment["avg_logprob"])

            # Combine text
            text = " ".join(text_parts).strip()

            # Calculate confidence
            if log_probs:
                avg_log_prob = np.mean(log_probs)
                confidence = float(np.clip(np.exp(avg_log_prob), 0.0, 1.0))
            else:
                confidence = 1.0 if text else 0.0

            # Filter hallucinations and clean
            text = self._filter_hallucinations(text)
            text = self._clean_text(text)

            logger.info(f"Transcribed {len(text)} characters from {os.path.basename(file_path)}")

            return {
                "text": text,
                "is_final": True,
                "confidence": confidence,
                "processing_time_ms": (time.time() - start_time) * 1000,
                "language": "en",
                "error": None,
            }

        except Exception as e:
            logger.error(f"File transcription failed: {e}", exc_info=True)
            return {
                "text": "",
                "is_final": False,
                "confidence": 0.0,
                "processing_time_ms": (time.time() - start_time) * 1000,
                "error": f"File transcription failed: {str(e)}",
            }

    def _get_transcription_language(self) -> str:
        """Return configured transcription language with backward-compatible default."""
        return getattr(self.config, "TRANSCRIPTION_LANGUAGE", "en")

    def _get_initial_prompt(self) -> str:
        """Return configured initial prompt with backward-compatible fallback."""
        if hasattr(self.config, "get_initial_prompt"):
            return self.config.get_initial_prompt()
        return getattr(self.config, "TRANSCRIPTION_CONTEXT_PROMPT", "")
    
    def get_device_info(self) -> dict:
        """
        Get information about the current device configuration.
        
        Returns:
            Dict with device info
        """
        info = {
            "device": self.config.DEVICE,
            "compute_type": self.config.COMPUTE_TYPE,
            "model_size": self.config.MODEL_SIZE,
            "cuda_available": CUDA_AVAILABLE,
            "torch_available": TORCH_AVAILABLE,
        }
        
        if CUDA_AVAILABLE and TORCH_AVAILABLE:
            try:
                info["gpu_name"] = torch.cuda.get_device_name(0)
                info["gpu_memory_total"] = f"{torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB"
            except:
                pass
        
        return info
