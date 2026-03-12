"""Production-grade Whisper transcription engine with audio processing and validation"""

import logging
import time
import numpy as np
import re
from typing import Optional, List, Dict, Tuple
from collections import Counter
from faster_whisper import WhisperModel

# Audio preprocessing
try:
    import noisereduce as nr
    NOISEREDUCE_AVAILABLE = True
except ImportError:
    NOISEREDUCE_AVAILABLE = False
    logging.warning("noisereduce not installed - noise reduction disabled")

try:
    from scipy import signal
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    logging.warning("scipy not installed - high-pass filtering disabled")

# Silero VAD
try:
    import torch
    torch.set_num_threads(1)  # Reduce CPU usage
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logging.warning("torch not installed - Silero VAD disabled")

from app.audio_config import AudioConfig, config

logger = logging.getLogger(__name__)


class TranscriptionEngine:
    """
    Production-grade transcription engine using Faster-Whisper with Silero VAD.
    Handles audio validation, preprocessing, VAD, Whisper inference, and post-processing.
    All errors are caught and returned as dict with error key (never raises).
    """

    def __init__(self, config_instance: AudioConfig = None):
        """
        Initialize the transcription engine.

        Args:
            config_instance: AudioConfig instance (defaults to global config)
        """
        self.config = config_instance or config
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

            self.model = WhisperModel(
                self.config.MODEL_SIZE,
                device=self.config.DEVICE,
                compute_type=self.config.COMPUTE_TYPE,
                cpu_threads=4,
                num_workers=1,
            )

            elapsed = time.time() - start_time
            logger.info(f"Model loaded successfully in {elapsed:.2f}s")

            # Warm up the model to avoid slow first transcription
            self._warmup()

        except RuntimeError as e:
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

            logger.info("Model warm-up complete")

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
            
            # Get speech probability for the whole chunk
            speech_prob = self.vad_model(audio_tensor, self.config.SAMPLE_RATE).item()
            
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
                'has_speech': speech_prob > self.config.SILERO_VAD_THRESHOLD,
                'speech_prob': speech_prob,
                'speech_segments': segments
            }
            
        except Exception as e:
            logger.warning(f"Silero VAD error (falling back to RMS): {e}")
            return self._detect_speech_rms(audio_bytes)
    
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
        """
        Convert raw int16 PCM bytes to float32 numpy array.

        Args:
            audio_bytes: Raw audio data as bytes

        Returns:
            Float32 numpy array normalized to [-1.0, 1.0], or None on error
        """
        try:
            # Convert int16 bytes to int16 array
            audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)

            # Normalize to float32 in range [-1.0, 1.0]
            audio_float32 = audio_int16.astype(np.float32) / 32768.0

            return audio_float32

        except ValueError:
            # Bytes length not divisible by 2 (not valid int16)
            # Truncate to nearest even length
            try:
                truncated_bytes = audio_bytes[: (len(audio_bytes) // 2) * 2]
                audio_int16 = np.frombuffer(truncated_bytes, dtype=np.int16)
                audio_float32 = audio_int16.astype(np.float32) / 32768.0
                logger.warning(f"Truncated audio from {len(audio_bytes)} to {len(truncated_bytes)} bytes")
                return audio_float32
            except Exception as e:
                logger.error(f"Failed to convert bytes to float32: {e}")
                return None

    def _validate_audio(self, audio: np.ndarray) -> dict:
        """
        Validate audio quality with three checks:
        1. Length: must be >= MIN_AUDIO_SAMPLES
        2. Energy: RMS must be >= SILENCE_RMS_THRESHOLD
        3. Clipping: warn if >5% of samples exceed 0.95 amplitude

        Args:
            audio: Float32 numpy array [-1.0, 1.0]

        Returns:
            Dict with is_valid (bool), reason (str), rms (float)
        """
        # ── CHECK 1: LENGTH ──
        if len(audio) < self.config.MIN_AUDIO_SAMPLES:
            return {
                "is_valid": False,
                "reason": f"Audio too short: {len(audio)} < {self.config.MIN_AUDIO_SAMPLES} samples",
                "rms": 0.0,
            }

        # ── CHECK 2: ENERGY (RMS) ──
        rms = np.sqrt(np.mean(audio**2))
        if rms < self.config.SILENCE_RMS_THRESHOLD:
            return {
                "is_valid": False,
                "reason": f"Audio is silence (RMS {rms:.6f} < {self.config.SILENCE_RMS_THRESHOLD})",
                "rms": rms,
            }

        # ── CHECK 3: CLIPPING ──
        clipping_ratio = np.sum(np.abs(audio) > 0.95) / len(audio)
        if clipping_ratio > 0.05:
            logger.warning(
                f"Audio clipping detected: {clipping_ratio*100:.1f}% of samples exceed 0.95. "
                "Microphone may be distorting."
            )

        return {
            "is_valid": True,
            "reason": "OK",
            "rms": float(rms),
        }

    def _preprocess_audio(self, audio: np.ndarray) -> np.ndarray:
        """
        Enhanced preprocessing pipeline:
        1. DC offset removal
        2. High-pass filter (remove low-frequency noise)
        3. Noise reduction (if available)
        4. Dynamic range compression
        5. Peak normalization

        Args:
            audio: Float32 numpy array

        Returns:
            Preprocessed float32 numpy array
        """
        # ── 1. DC OFFSET REMOVAL ──
        audio = audio - np.mean(audio)

        # ── 2. HIGH-PASS FILTER (remove rumble < 80 Hz) ──
        if SCIPY_AVAILABLE:
            try:
                sos = signal.butter(4, 80, 'hp', fs=self.config.SAMPLE_RATE, output='sos')
                audio = signal.sosfilt(sos, audio)
            except Exception as e:
                logger.warning(f"High-pass filter failed: {e}")

        # ── 3. NOISE REDUCTION ──
        if NOISEREDUCE_AVAILABLE:
            try:
                audio = nr.reduce_noise(
                    y=audio,
                    sr=self.config.SAMPLE_RATE,
                    stationary=True,
                    prop_decrease=0.8  # Reduce noise by 80%
                )
            except Exception as e:
                logger.warning(f"Noise reduction failed: {e}")

        # ── 4. DYNAMIC RANGE COMPRESSION ──
        # Boost quiet parts, compress loud parts
        try:
            threshold = 0.3
            ratio = 2.0
            audio_abs = np.abs(audio)
            compressed = np.where(
                audio_abs > threshold,
                np.sign(audio) * (threshold + (audio_abs - threshold) / ratio),
                audio
            )
            audio = compressed
        except Exception as e:
            logger.warning(f"Compression failed: {e}")

        # ── 5. PEAK NORMALIZATION ──
        peak = np.max(np.abs(audio))
        if peak > 0.1:
            audio = audio * (0.8 / peak)  # Target 0.8, leave headroom

        return audio.astype(np.float32)

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
                    language="en",
                    beam_size=self.config.BEAM_SIZE,
                    patience=self.config.PATIENCE,
                    best_of=self.config.BEST_OF,
                    temperature=self.config.TEMPERATURE,
                    initial_prompt=self.config.MEDICAL_CONTEXT_PROMPT,
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
                elif isinstance(segment, dict) and "text" in segment:
                    text_parts.append(segment["text"])
                    if "avg_logprob" in segment:
                        log_probs.append(segment["avg_logprob"])
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
        """
        IMPROVED: Filter common Whisper hallucinations.
        
        Checks:
        1. Exact match with known hallucination phrases
        2. Short text (< 15 chars) containing specific hallucination phrases
        3. Single word repeated >50% of all words
        4. Only punctuation or very short text
        5. Single character repetition pattern (a a a)

        Args:
            text: Transcribed text

        Returns:
            Filtered text (empty string if hallucination detected)
        """
        if not text or len(text.strip()) == 0:
            return ""

        text_lower = text.lower().strip()

        # ── CHECK 1: EXACT MATCH WITH HALLUCINATION PHRASES ──
        if text_lower in [p.lower() for p in self.config.HALLUCINATION_PHRASES]:
            logger.debug(f"Filtered hallucination (exact match): '{text}'")
            return ""

        # ── CHECK 2: SHORT TEXT + SPECIFIC PHRASES ──
        # Only filter very short text with clear hallucinations
        if len(text) < 15:
            for phrase in ["thank you", "subscribe", "www.", ".com", "copyright"]:
                if phrase in text_lower:
                    logger.debug(f"Filtered hallucination (short + phrase): '{text}'")
                    return ""

        # ── CHECK 3: SINGLE WORD REPETITION ──
        words = text.split()
        if len(words) >= 3:
            word_counts = Counter(w.lower() for w in words if len(w) > 2)
            if word_counts:
                most_common_word, count = word_counts.most_common(1)[0]
                if count / len(words) > 0.5:
                    logger.debug(f"Filtered hallucination (repetition): '{text}'")
                    return ""

        # ── CHECK 4: ONLY PUNCTUATION OR TOO SHORT ──
        text_stripped = text.strip().rstrip(".,;:!?")
        if len(text_stripped) < 2:
            logger.debug(f"Filtered hallucination (too short): '{text}'")
            return ""
        
        if all(not c.isalnum() for c in text_stripped):
            logger.debug(f"Filtered hallucination (punctuation only): '{text}'")
            return ""

        # ── CHECK 5: SINGLE CHARACTER REPETITION PATTERN ──
        if re.search(r'\b(\w)\s+\1\s+\1\b', text_lower):
            logger.debug(f"Filtered hallucination (single char repetition): '{text}'")
            return ""

        return text

    def _clean_text(self, text: str) -> str:
        """
        Clean transcribed text:
        1. Collapse multiple spaces
        2. Remove leading punctuation
        3. Strip whitespace

        Args:
            text: Raw transcribed text

        Returns:
            Cleaned text
        """
        # Collapse multiple spaces
        text = re.sub(r"\s+", " ", text)

        # Remove leading punctuation
        text = re.sub(r"^[,;:]+\s*", "", text)

        # Strip whitespace
        text = text.strip()

        return text

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

            import os
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
                language="en",
                beam_size=self.config.BEAM_SIZE,
                patience=self.config.PATIENCE,
                best_of=self.config.BEST_OF,
                temperature=self.config.TEMPERATURE,
                initial_prompt=self.config.MEDICAL_CONTEXT_PROMPT,
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

            import os
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


# ─────────────────────────────────────────────────────────────────
# TESTING
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import os

    # Setup logging for tests
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger.info("=== Transcription Engine Tests ===\n")

    # Initialize engine
    engine = TranscriptionEngine()

    # ── TEST 1: SILENCE ──
    logger.info("Test 1: Silence (should return empty)")
    silence_audio = np.zeros(16000, dtype=np.int16)  # 1 second of silence
    silence_bytes = silence_audio.tobytes()
    result = engine.transcribe_audio_bytes(silence_bytes)
    logger.info(f"Result: text='{result['text']}', error={result['error']}\n")

    # ── TEST 2: VAD ──
    logger.info("Test 2: VAD detection on silence")
    vad_result = engine.detect_speech(silence_bytes)
    logger.info(f"VAD: has_speech={vad_result['has_speech']}, prob={vad_result['speech_prob']:.3f}\n")

    # ── TEST 3: TOO SHORT ──
    logger.info("Test 3: Too short audio (should return empty)")
    short_audio = np.zeros(100, dtype=np.int16)
    short_bytes = short_audio.tobytes()
    result = engine.transcribe_audio_bytes(short_bytes)
    logger.info(f"Result: text='{result['text']}', error={result['error']}\n")

    logger.info("=== Tests Complete ===")
    