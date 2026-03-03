"""WebSocket audio streaming support for a single client

Architecture:
    Frontend sends audio bytes -> add_audio_chunk() -> buffer accumulates ->
    when buffer >= CHUNK_SIZE_BYTES -> prepend overlap from previous chunk ->
    run through TranscriptionEngine -> deduplicate overlapping words ->
    apply MedicalFormatter -> return result to WebSocket
"""

import logging
import asyncio
from collections import deque
from typing import Optional

from app.audio_config import AudioConfig
from app.services.transcription_engine import TranscriptionEngine
from app.services.medical_formatter import MedicalFormatter

logger = logging.getLogger(__name__)


class AudioStreamHandler:
    """Handles buffering, overlap, deduplication, and transcription for one client."""

    def __init__(
        self,
        engine: TranscriptionEngine,
        formatter: MedicalFormatter,
        config: AudioConfig,
    ):
        # external dependencies
        self.engine = engine
        self.formatter = formatter
        self.config = config

        # buffers
        self.audio_buffer = bytearray()
        self._overlap_buffer = bytearray()

        # state
        self.is_processing: bool = False
        self.total_audio_received: int = 0
        self.total_transcriptions: int = 0
        self.consecutive_silence_count: int = 0
        self.session_start_time = asyncio.get_event_loop().time()

        # deduplication
        self._previous_text: str = ""
        self._text_history: deque = deque(maxlen=10)

    async def add_audio_chunk(self, chunk: bytes) -> Optional[dict]:
        """
        Add incoming audio to the buffer and process if threshold met.

        Returns transcription result dict or None if nothing produced.
        """
        self.audio_buffer.extend(chunk)
        self.total_audio_received += len(chunk)
        logger.info(f"Chunk: {len(chunk)} bytes = {len(chunk)//2} samples = {len(chunk)//2/16000:.3f}s at 16kHz")

        if len(self.audio_buffer) < self.config.CHUNK_SIZE_BYTES:
            return None

        if self.is_processing:
            # avoid reentrancy; drop chunk until processing finishes
            return None

        return await self._process_buffer()

    async def _process_buffer(self) -> Optional[dict]:
        """Process the buffered audio and return transcription info."""
        self.is_processing = True
        try:
            # prepend overlap from previous cycle
            if self._overlap_buffer:
                logger.debug("Prepending overlap to current buffer")
                self.audio_buffer = self._overlap_buffer + self.audio_buffer

            # save new overlap for next cycle
            if len(self.audio_buffer) > self.config.OVERLAP_SIZE_BYTES:
                self._overlap_buffer = self.audio_buffer[-self.config.OVERLAP_SIZE_BYTES :]
            else:
                self._overlap_buffer = self.audio_buffer[:]  # whatever we have

            # grab copy to send for transcription and clear
            audio_to_transcribe = bytes(self.audio_buffer)
            self.audio_buffer.clear()

            # run transcription in executor
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self.engine.transcribe_audio_bytes, audio_to_transcribe)

            text = result.get("text", "")
            if not text:
                self.consecutive_silence_count += 1
                return None

            self.consecutive_silence_count = 0

            # deduplicate
            deduped = self._deduplicate_text(text)
            formatted = self.formatter.format(deduped)

            # update history
            self._previous_text = deduped
            self._text_history.append(deduped)
            self.total_transcriptions += 1

            return {
                "text": formatted,
                "raw_text": deduped,
                "confidence": result.get("confidence", 0.0),
                "processing_time_ms": result.get("processing_time_ms", 0.0),
                "timestamp": result.get("timestamp"),
            }

        except Exception as e:
            logger.error(f"Error processing buffer: {e}", exc_info=True)
            return {"error": str(e)}

        finally:
            self.is_processing = False

    def _deduplicate_text(self, new_text: str) -> str:
        """Remove overlapping words with previous result."""
        if not self._previous_text or not new_text:
            return new_text

        prev_words = self._previous_text.lower().split()
        new_words = new_text.lower().split()

        max_overlap = min(5, len(prev_words), len(new_words))
        overlap_count = 0

        for n in range(max_overlap, 0, -1):
            if prev_words[-n:] == new_words[:n]:
                overlap_count = n
                break

        if overlap_count > 0:
            deduped = " ".join(new_text.split()[overlap_count:])
            return deduped
        return new_text

    async def flush(self) -> Optional[dict]:
        """Force transcription of any remaining audio."""
        if len(self.audio_buffer) <= 100:
            return None
        return await self._process_buffer()

    def reset(self):
        """Clear buffers and reset state counters."""
        self.audio_buffer.clear()
        self._overlap_buffer.clear()
        self.is_processing = False
        self.total_audio_received = 0
        self.total_transcriptions = 0
        self.consecutive_silence_count = 0
        self.session_start_time = asyncio.get_event_loop().time()
        self._previous_text = ""
        self._text_history.clear()

    def get_stats(self) -> dict:
        """Return session statistics."""
        elapsed = asyncio.get_event_loop().time() - self.session_start_time
        total_seconds = self.total_audio_received / (self.config.SAMPLE_RATE * self.config.SAMPLE_WIDTH)
        return {
            "session_duration_seconds": elapsed,
            "total_audio_bytes": self.total_audio_received,
            "total_audio_seconds": total_seconds,
            "total_transcriptions": self.total_transcriptions,
            "buffer_size_bytes": len(self.audio_buffer),
        }
