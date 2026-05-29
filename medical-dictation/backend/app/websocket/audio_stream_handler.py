"""Per-client audio buffering, VAD triggering, and transcription handling."""

import logging
import re
import time
from typing import Optional

from app.audio_config import AudioConfig
from app.domains.registry import get_domain_adapter
from app.services.transcription_engine import TranscriptionEngine

logger = logging.getLogger(__name__)


class AudioStreamHandler:
    """
    Handles real-time audio streaming with VAD-based dynamic buffering
    and optional wrapper command processing.
    """

    def __init__(
        self,
        transcription_engine: TranscriptionEngine,
        config: AudioConfig,
        domain: str | None = None,
    ):
        """
        Initialize stream handler for a client.

        Args:
            transcription_engine: Shared transcription engine with VAD.
            config: Audio configuration.
            domain: Optional domain adapter name.
        """
        self.engine = transcription_engine
        self.config = config
        self.domain_adapter = get_domain_adapter(
            domain or getattr(config, "DEFAULT_TRANSCRIPTION_DOMAIN", "general")
        )
        self.domain = self.domain_adapter.name
        self.command_processor = self.domain_adapter.command_processor

        self.audio_buffer = bytearray()
        self.overlap_buffer = bytearray()
        self.recent_emitted_words: list[str] = []

        self.consecutive_silence_chunks = 0
        self.last_speech_time = time.time()
        self.has_speech_in_buffer = False
        self.pending_flush_reason = "unknown"

        self.min_buffer_size = config.MIN_CHUNK_SIZE_BYTES
        self.max_buffer_size = config.MAX_CHUNK_SIZE_BYTES
        self.overlap_size = config.OVERLAP_SIZE_BYTES

        self.session_start_time = time.time()
        self.audio_received_bytes = 0
        self.chunks_received = 0
        self.transcriptions_count = 0
        self.total_words = 0
        self.silence_chunks_skipped = 0
        self.commands_executed = 0

    def add_audio_chunk(self, audio_bytes: bytes) -> Optional[dict]:
        """
        Add audio chunk with VAD-based processing.

        Args:
            audio_bytes: Audio data as int16 PCM, 16 kHz, mono.

        Returns:
            Dict with text and commands if transcription triggered, else None.
        """
        self.audio_received_bytes += len(audio_bytes)
        self.chunks_received += 1

        vad_result = self.engine.detect_speech(audio_bytes)

        if vad_result["has_speech"]:
            logger.debug("Speech detected (prob=%.2f)", vad_result["speech_prob"])

            self.audio_buffer.extend(audio_bytes)
            self.consecutive_silence_chunks = 0
            self.last_speech_time = time.time()
            self.has_speech_in_buffer = True

            if len(self.audio_buffer) >= self.max_buffer_size:
                logger.info(
                    "Max buffer size reached (%s bytes), forcing transcription",
                    len(self.audio_buffer),
                )
                self.pending_flush_reason = "max_buffer"
                return self._transcribe_buffer()

        else:
            self.consecutive_silence_chunks += 1

            if self.has_speech_in_buffer and self.consecutive_silence_chunks <= 2:
                self.audio_buffer.extend(audio_bytes)
            else:
                self.silence_chunks_skipped += 1
                logger.debug("Skipping silence chunk (saved CPU)")

            time_since_speech = time.time() - self.last_speech_time

            if (
                self.has_speech_in_buffer
                and len(self.audio_buffer) >= self.min_buffer_size
                and time_since_speech >= self.config.SILENCE_TIMEOUT_SECONDS
            ):
                logger.info(
                    "Natural pause detected (%.1fs silence), transcribing",
                    time_since_speech,
                )
                self.pending_flush_reason = "natural_pause"
                return self._transcribe_buffer()

        return None

    def _transcribe_buffer(self) -> Optional[dict]:
        """
        Transcribe the current audio buffer with overlap and command processing.

        Returns:
            Dict with text and commands keys, or None.
        """
        if len(self.audio_buffer) < self.config.MIN_AUDIO_SAMPLES * 2:
            logger.debug("Buffer too small to transcribe, clearing")
            self.audio_buffer.clear()
            self.has_speech_in_buffer = False
            return None

        try:
            buffered_audio_bytes = len(self.audio_buffer)
            audio_duration_seconds = buffered_audio_bytes / (
                self.config.SAMPLE_RATE * self.config.SAMPLE_WIDTH
            )
            flush_reason = self.pending_flush_reason

            if len(self.overlap_buffer) > 0:
                audio_with_overlap = bytes(self.overlap_buffer) + bytes(self.audio_buffer)
                logger.debug("Added %s bytes of overlap", len(self.overlap_buffer))
            else:
                audio_with_overlap = bytes(self.audio_buffer)

            result = self.engine.transcribe_audio_bytes(audio_with_overlap)
            processing_time_ms = float(result.get("processing_time_ms") or 0.0)

            if result.get("error"):
                logger.warning("Transcription error: %s", result["error"])
                self.audio_buffer.clear()
                self.overlap_buffer.clear()
                self.has_speech_in_buffer = False
                return None

            text = result.get("text", "").strip()
            if not text:
                self.audio_buffer.clear()
                self.overlap_buffer.clear()
                self.has_speech_in_buffer = False
                return None

            text = self._sanitize_stream_text(text)
            if not text:
                self.audio_buffer.clear()
                self.has_speech_in_buffer = False
                self.pending_flush_reason = "unknown"
                return None

            processed_text, commands = self.domain_adapter.process_transcript(text)
            self.commands_executed += len(commands)

            if len(self.audio_buffer) > self.overlap_size:
                self.overlap_buffer = self.audio_buffer[-self.overlap_size:]
            else:
                self.overlap_buffer = bytearray(self.audio_buffer)

            logger.debug("Saved %s bytes for overlap", len(self.overlap_buffer))
            logger.info(
                "Transcribed %.2fs audio in %.0fms (%s)",
                audio_duration_seconds,
                processing_time_ms,
                flush_reason,
            )

            self.transcriptions_count += 1
            if processed_text:
                self.total_words += len(processed_text.split())
                self._remember_emitted_text(processed_text)

            self.audio_buffer.clear()
            self.has_speech_in_buffer = False
            self.pending_flush_reason = "unknown"

            return {
                "text": processed_text,
                "domain": self.domain,
                "processing_time_ms": processing_time_ms,
                "audio_duration_seconds": audio_duration_seconds,
                "flush_reason": flush_reason,
                "commands": [
                    {
                        "type": (
                            cmd.command_type.value
                            if hasattr(cmd.command_type, "value")
                            else str(cmd.command_type)
                        ),
                        "action": cmd.action,
                        "original_text": cmd.original_text,
                        "replacement": cmd.replacement,
                    }
                    for cmd in commands
                ],
            }

        except Exception as e:
            logger.error("Error during transcription: %s", e, exc_info=True)
            self.audio_buffer.clear()
            self.overlap_buffer.clear()
            self.has_speech_in_buffer = False
            return None

    def _sanitize_stream_text(self, text: str) -> str:
        """Clean boundary artifacts caused by audio overlap in streaming mode."""
        text = text.strip()
        if not text:
            return ""

        text = re.sub(r"\s+\w+-$", "", text).strip()
        text = re.sub(r"\b(?:pause|paused)\b", "", text, flags=re.IGNORECASE)
        text = self._remove_adjacent_repeated_phrases(text)
        if not text:
            return ""

        words = text.split()
        normalized_words = self._boundary_tokens(text)
        recent = self.recent_emitted_words

        max_overlap = min(len(normalized_words), len(recent), 8)
        overlap_count = 0
        remove_word_count = 0
        for size in range(max_overlap, 0, -1):
            if self._token_sequences_match(recent[-size:], normalized_words[:size]):
                overlap_count = size
                remove_word_count = self._word_count_for_boundary_tokens(words, size)
                break

        if not overlap_count:
            max_repeated_prefix = min(len(normalized_words), len(recent))
            for size in range(max_repeated_prefix, 7, -1):
                if self._tokens_contain_sequence(recent, normalized_words[:size]):
                    overlap_count = size
                    remove_word_count = self._word_count_for_boundary_tokens(words, size)
                    break

        if overlap_count:
            text = " ".join(words[remove_word_count:]).strip()

        return self._cleanup_stream_text(text) if text else ""

    def _remove_adjacent_repeated_phrases(self, text: str) -> str:
        """Remove repeated 1-3 word phrases created around pauses."""
        words = text.split()
        output: list[str] = []
        for word in words:
            output.append(word)
            for size in range(3, 0, -1):
                if len(output) < size * 2:
                    continue
                first = [self._normalize_boundary_word(w) for w in output[-size * 2 : -size]]
                second = [self._normalize_boundary_word(w) for w in output[-size:]]
                if first == second and all(first):
                    del output[-size:]
                    break

        return " ".join(output)

    @staticmethod
    def _cleanup_stream_text(text: str) -> str:
        text = re.sub(r"\s{2,}", " ", text)
        text = re.sub(r"\s+([.,;:])", r"\1", text)
        return text.strip()

    def _remember_emitted_text(self, text: str):
        """Keep a short normalized tail to remove duplicate overlap text later."""
        words = self._boundary_tokens(text)
        self.recent_emitted_words = (self.recent_emitted_words + words)[-240:]

    @staticmethod
    def _normalize_boundary_word(word: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", word.lower())

    def _boundary_tokens(self, text: str) -> list[str]:
        tokens: list[str] = []
        for word in text.split():
            for part in re.split(r"[-/]+", word):
                normalized = self._normalize_boundary_word(part)
                if normalized:
                    tokens.append(normalized)
        return tokens

    def _word_count_for_boundary_tokens(self, words: list[str], token_count: int) -> int:
        consumed_tokens = 0
        for index, word in enumerate(words, start=1):
            consumed_tokens += len(self._boundary_tokens(word))
            if consumed_tokens >= token_count:
                return index
        return min(token_count, len(words))

    @staticmethod
    def _tokens_contain_sequence(tokens: list[str], sequence: list[str]) -> bool:
        if not sequence or len(sequence) > len(tokens):
            return False
        for start in range(0, len(tokens) - len(sequence) + 1):
            if AudioStreamHandler._token_sequences_match(
                tokens[start : start + len(sequence)],
                sequence,
            ):
                return True
        return False

    @staticmethod
    def _token_sequences_match(left: list[str], right: list[str]) -> bool:
        if len(left) != len(right):
            return False
        return all(AudioStreamHandler._tokens_match(a, b) for a, b in zip(left, right))

    @staticmethod
    def _tokens_match(left: str, right: str) -> bool:
        if left == right:
            return True
        if min(len(left), len(right)) < 4:
            return False
        if abs(len(left) - len(right)) > 1:
            return False

        previous = list(range(len(right) + 1))
        for i, left_char in enumerate(left, start=1):
            current = [i]
            for j, right_char in enumerate(right, start=1):
                cost = 0 if left_char == right_char else 1
                current.append(
                    min(
                        current[j - 1] + 1,
                        previous[j] + 1,
                        previous[j - 1] + cost,
                    )
                )
            previous = current

        return previous[-1] <= 1

    def flush(self) -> Optional[dict]:
        """
        Force transcribe any remaining audio in buffer.

        Returns:
            Dict with text and commands, or None.
        """
        if len(self.audio_buffer) == 0:
            return None

        logger.debug("Flushing buffer with %s bytes", len(self.audio_buffer))
        self.pending_flush_reason = "manual_flush"
        return self._transcribe_buffer()

    def get_stats(self) -> dict:
        """Get session statistics with efficiency metrics."""
        elapsed = time.time() - self.session_start_time
        audio_duration = self.audio_received_bytes / (
            self.config.SAMPLE_RATE * self.config.SAMPLE_WIDTH
        )

        return {
            "session_duration_seconds": elapsed,
            "audio_duration_seconds": audio_duration,
            "audio_received_bytes": self.audio_received_bytes,
            "chunks_received": self.chunks_received,
            "transcriptions_count": self.transcriptions_count,
            "total_words": self.total_words,
            "buffer_size_bytes": len(self.audio_buffer),
            "silence_chunks_skipped": self.silence_chunks_skipped,
            "efficiency_percent": (
                self.silence_chunks_skipped / max(self.chunks_received, 1)
            )
            * 100,
            "commands_executed": self.commands_executed,
        }
