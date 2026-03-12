"""FastAPI application with WebSocket audio streaming endpoint"""

import logging
import json
import time
from contextlib import asynccontextmanager
from typing import Optional
from datetime import datetime, timezone

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, WebSocketException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.audio_config import AudioConfig
from app.services.transcription_engine import TranscriptionEngine
from app.services.medical_formatter import MedicalFormatter
from app.models.schemas import (
    TranscriptionResponse,
    ConnectionResponse,
    ErrorResponse,
    StatsResponse,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────
# AUDIO STREAM HANDLER (IMPROVED WITH VAD)
# ─────────────────────────────────────────────────────────────────


class AudioStreamHandler:
    """
    IMPROVED: Handles real-time audio streaming with VAD-based dynamic buffering.
    
    Key improvements:
    - Uses Silero VAD for real-time speech detection
    - Dynamic chunk sizes based on speech pauses (not fixed 2 seconds)
    - Implements overlap buffer to prevent word cutoffs
    - Tracks silence to trigger transcription at natural pauses
    """

    def __init__(self, transcription_engine: TranscriptionEngine, config: AudioConfig):
        """
        Initialize stream handler for a client.

        Args:
            transcription_engine: Shared transcription engine (with VAD)
            config: Audio configuration
        """
        self.engine = transcription_engine
        self.config = config
        self.formatter = MedicalFormatter()

        # Dynamic audio buffers
        self.audio_buffer = bytearray()
        self.overlap_buffer = bytearray()  # NEW: Overlap implementation
        
        # VAD state tracking
        self.consecutive_silence_chunks = 0
        self.last_speech_time = time.time()
        self.has_speech_in_buffer = False
        
        # Buffer size limits (dynamic, not fixed)
        self.min_buffer_size = config.MIN_CHUNK_SIZE_BYTES
        self.max_buffer_size = config.MAX_CHUNK_SIZE_BYTES
        self.overlap_size = config.OVERLAP_SIZE_BYTES

        # Session stats
        self.session_start_time = time.time()
        self.audio_received_bytes = 0
        self.chunks_received = 0
        self.transcriptions_count = 0
        self.total_words = 0
        self.silence_chunks_skipped = 0  # NEW: Track efficiency

    def add_audio_chunk(self, audio_bytes: bytes) -> Optional[str]:
        """
        IMPROVED: Add audio chunk with VAD-based processing.
        
        Uses Silero VAD to:
        - Skip pure silence chunks (reduce CPU)
        - Detect natural pauses to trigger transcription
        - Accumulate speech dynamically (not fixed 2 seconds)

        Args:
            audio_bytes: Audio data (int16 PCM, 16kHz, mono)

        Returns:
            Transcribed text if natural pause detected, None otherwise
        """
        self.audio_received_bytes += len(audio_bytes)
        self.chunks_received += 1
        
        # ── STEP 1: DETECT SPEECH IN THIS CHUNK ──
        vad_result = self.engine.detect_speech(audio_bytes)
        
        if vad_result['has_speech']:
            # ── SPEECH DETECTED ──
            logger.debug(f"Speech detected (prob={vad_result['speech_prob']:.2f})")
            
            # Add to buffer and reset silence counter
            self.audio_buffer.extend(audio_bytes)
            self.consecutive_silence_chunks = 0
            self.last_speech_time = time.time()
            self.has_speech_in_buffer = True
            
            # Check if buffer is too large (safety: force transcription)
            if len(self.audio_buffer) >= self.max_buffer_size:
                logger.info(f"Max buffer size reached ({len(self.audio_buffer)} bytes), forcing transcription")
                return self._transcribe_buffer()
        
        else:
            # ── SILENCE DETECTED ──
            self.consecutive_silence_chunks += 1
            
            # If we have speech in buffer, add a bit of silence for context
            if self.has_speech_in_buffer and self.consecutive_silence_chunks <= 2:
                self.audio_buffer.extend(audio_bytes)
            else:
                self.silence_chunks_skipped += 1
                logger.debug(f"Skipping silence chunk (saved CPU)")
            
            # Check if we should transcribe (natural pause detected)
            time_since_speech = time.time() - self.last_speech_time
            
            if (self.has_speech_in_buffer and 
                len(self.audio_buffer) >= self.min_buffer_size and
                time_since_speech >= self.config.SILENCE_TIMEOUT_SECONDS):
                
                logger.info(f"Natural pause detected ({time_since_speech:.1f}s silence), transcribing")
                return self._transcribe_buffer()
        
        return None

    def _transcribe_buffer(self) -> Optional[str]:
        """
        IMPROVED: Transcribe the current audio buffer with overlap.
        
        Overlap implementation:
        - Prepends last 0.5s from previous chunk
        - Prevents word cutoffs at boundaries
        - Stores last 0.5s for next transcription

        Returns:
            Transcribed and formatted text, None if no text
        """
        if len(self.audio_buffer) < self.config.MIN_AUDIO_SAMPLES * 2:
            logger.debug("Buffer too small to transcribe, clearing")
            self.audio_buffer.clear()
            self.has_speech_in_buffer = False
            return None

        try:
            # ── PREPEND OVERLAP FROM PREVIOUS CHUNK ──
            if len(self.overlap_buffer) > 0:
                audio_with_overlap = bytes(self.overlap_buffer) + bytes(self.audio_buffer)
                logger.debug(f"Added {len(self.overlap_buffer)} bytes of overlap")
            else:
                audio_with_overlap = bytes(self.audio_buffer)
            
            # ── TRANSCRIBE ──
            result = self.engine.transcribe_audio_bytes(audio_with_overlap)

            if result.get("error"):
                logger.warning(f"Transcription error: {result['error']}")
                # Clear buffers and reset
                self.audio_buffer.clear()
                self.overlap_buffer.clear()
                self.has_speech_in_buffer = False
                return None

            text = result.get("text", "").strip()
            if not text:
                # No text, but clear buffers
                self.audio_buffer.clear()
                self.overlap_buffer.clear()
                self.has_speech_in_buffer = False
                return None

            # ── FORMAT TEXT ──
            text = self.formatter.format(text)

            # ── SAVE OVERLAP FOR NEXT CHUNK ──
            # Store last 0.5 seconds of current buffer
            if len(self.audio_buffer) > self.overlap_size:
                self.overlap_buffer = self.audio_buffer[-self.overlap_size:]
            else:
                # Buffer is small, use all of it as overlap
                self.overlap_buffer = bytearray(self.audio_buffer)
            
            logger.debug(f"Saved {len(self.overlap_buffer)} bytes for overlap")

            # ── UPDATE STATS ──
            self.transcriptions_count += 1
            self.total_words += len(text.split())

            # ── CLEAR BUFFER ──
            self.audio_buffer.clear()
            self.has_speech_in_buffer = False

            return text

        except Exception as e:
            logger.error(f"Error during transcription: {e}", exc_info=True)
            self.audio_buffer.clear()
            self.overlap_buffer.clear()
            self.has_speech_in_buffer = False
            return None

    def flush(self) -> Optional[str]:
        """
        Force transcribe any remaining audio in buffer.
        Called when connection closes or user manually flushes.

        Returns:
            Transcribed text
        """
        if len(self.audio_buffer) == 0:
            return None

        logger.debug(f"Flushing buffer with {len(self.audio_buffer)} bytes")
        return self._transcribe_buffer()

    def get_stats(self) -> dict:
        """Get session statistics with efficiency metrics."""
        elapsed = time.time() - self.session_start_time
        audio_duration = (self.audio_received_bytes / (self.config.SAMPLE_RATE * self.config.SAMPLE_WIDTH))

        return {
            "session_duration_seconds": elapsed,
            "audio_duration_seconds": audio_duration,
            "audio_received_bytes": self.audio_received_bytes,
            "chunks_received": self.chunks_received,
            "transcriptions_count": self.transcriptions_count,
            "total_words": self.total_words,
            "buffer_size_bytes": len(self.audio_buffer),
            "silence_chunks_skipped": self.silence_chunks_skipped,  # NEW
            "efficiency_percent": (self.silence_chunks_skipped / max(self.chunks_received, 1)) * 100,  # NEW
        }


# ─────────────────────────────────────────────────────────────────
# FASTAPI LIFESPAN
# ─────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle with async context manager.
    Loads Whisper model on startup, cleanup on shutdown.
    """
    # ── STARTUP ──
    logger.info("=" * 80)
    logger.info("MEDICAL DICTATION API - STARTING UP")
    logger.info("=" * 80)

    try:
        # Load audio config
        config = AudioConfig()
        logger.info(f"Audio Config: {config.MODEL_SIZE} on {config.DEVICE}")

        # Load transcription engine (loads Whisper model + Silero VAD)
        logger.info("Loading Whisper model and VAD (this may take 30-60 seconds)...")
        engine = TranscriptionEngine(config)
        logger.info("✓ Whisper model loaded successfully")

        # Store in app state
        app.state.config = config
        app.state.transcription_engine = engine
        app.state.active_connections = 0

        logger.info("=" * 80)
        logger.info("✓ APPLICATION READY FOR REQUESTS")
        logger.info("=" * 80)

    except Exception as e:
        logger.critical(f"Failed to start application: {e}", exc_info=True)
        raise

    yield

    # ── SHUTDOWN ──
    logger.info("=" * 80)
    logger.info("SHUTTING DOWN")
    logger.info("=" * 80)

    try:
        active = getattr(app.state, "active_connections", 0)
        if active > 0:
            logger.warning(f"Shutdown with {active} active connections")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# ─────────────────────────────────────────────────────────────────
# FASTAPI APP
# ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Medical Dictation API",
    description="Real-time medical voice dictation with WebSocket audio streaming",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────
# REST ENDPOINTS
# ─────────────────────────────────────────────────────────────────


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "Medical Dictation API",
        "version": "1.0.0",
        "active_connections": app.state.active_connections,
    }


@app.get("/health")
async def health():
    """Detailed health check with model status"""
    try:
        engine = app.state.transcription_engine
        config = app.state.config
        
        # Check if VAD is available
        vad_status = "enabled" if engine.vad_model is not None else "disabled (fallback to RMS)"

        return JSONResponse(
            content={
                "status": "healthy",
                "model_loaded": engine.model is not None,
                "model_size": config.MODEL_SIZE,
                "device": config.DEVICE,
                "vad_status": vad_status,
                "active_connections": app.state.active_connections,
            },
            status_code=200,
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            content={"status": "unhealthy", "error": str(e)},
            status_code=503,
        )


@app.get("/config")
async def get_config():
    """Get current audio configuration"""
    try:
        config = app.state.config
        return {
            "sample_rate": config.SAMPLE_RATE,
            "channels": config.CHANNELS,
            "sample_width": config.SAMPLE_WIDTH,
            "min_chunk_bytes": config.MIN_CHUNK_SIZE_BYTES,
            "max_chunk_bytes": config.MAX_CHUNK_SIZE_BYTES,
            "overlap_bytes": config.OVERLAP_SIZE_BYTES,
            "model": config.MODEL_SIZE,
            "device": config.DEVICE,
            "vad_enabled": app.state.transcription_engine.vad_model is not None,
        }
    except Exception as e:
        logger.error(f"Get config failed: {e}")
        return JSONResponse(
            content={"error": str(e)},
            status_code=500,
        )


# ─────────────────────────────────────────────────────────────────
# WEBSOCKET ENDPOINT
# ─────────────────────────────────────────────────────────────────


@app.websocket("/ws/audio")
async def websocket_audio_stream(websocket: WebSocket):
    """
    WebSocket endpoint for real-time audio streaming with VAD.

    PROTOCOL:
    - Client → Server: Binary audio data (16-bit PCM, 16kHz, mono)
    - Server → Client: JSON transcription/error messages

    LIFECYCLE:
    1. Accept connection
    2. Send welcome message with audio config
    3. Process audio chunks with VAD-based dynamic buffering
    4. On disconnect: flush buffer, send final stats, cleanup
    """
    try:
        # ── STEP 1: Accept connection ──
        await websocket.accept()
        app.state.active_connections += 1
        session_id = f"session_{int(time.time() * 1000)}"

        logger.info(f"[{session_id}] Client connected (total: {app.state.active_connections})")

        # ── STEP 2: Create handler with VAD ──
        handler = AudioStreamHandler(app.state.transcription_engine, app.state.config)

        # ── STEP 3: Send welcome message ──
        welcome = ConnectionResponse(
            type="connected",
            message="Connected to Medical Dictation API with VAD",
            config={
                "sample_rate": app.state.config.SAMPLE_RATE,
                "channels": app.state.config.CHANNELS,
                "sample_width": app.state.config.SAMPLE_WIDTH,
                "min_chunk_bytes": app.state.config.MIN_CHUNK_SIZE_BYTES,
                "max_chunk_bytes": app.state.config.MAX_CHUNK_SIZE_BYTES,
                "overlap_bytes": app.state.config.OVERLAP_SIZE_BYTES,
                "model": app.state.config.MODEL_SIZE,
                "device": app.state.config.DEVICE,
                "vad_enabled": app.state.transcription_engine.vad_model is not None,
            },
        )
        await websocket.send_json(welcome.model_dump())
        logger.debug(f"[{session_id}] Sent welcome message")

        # ── STEP 4: Message receive loop ──
        while True:
            try:
                # Receive message (binary or text)
                data = await websocket.receive()

                # Binary audio data
                if "bytes" in data:
                    audio_bytes = data["bytes"]
                    logger.debug(f"[{session_id}] Received {len(audio_bytes)} bytes of audio")

                    # Add to handler buffer (VAD-based processing)
                    text = handler.add_audio_chunk(audio_bytes)

                    if text:
                        # Send transcription result
                        response = TranscriptionResponse(
                            type="transcription",
                            text=text,
                            is_final=True,
                            confidence=0.95,
                            processing_time_ms=50,
                            timestamp=datetime.now(timezone.utc).timestamp(),
                        )
                        await websocket.send_json(response.model_dump())
                        logger.info(f"[{session_id}] Sent transcription: {text[:50]}...")

                # Text control message
                elif "text" in data:
                    message_text = data["text"]
                    try:
                        control_msg = json.loads(message_text)
                        await _handle_control_message(websocket, handler, control_msg, session_id)
                    except json.JSONDecodeError:
                        logger.warning(f"[{session_id}] Invalid JSON control message")
                        error = ErrorResponse(
                            type="error",
                            message="Invalid JSON control message",
                            code="INVALID_JSON",
                        )
                        await websocket.send_json(error.model_dump())

            except WebSocketDisconnect:
                logger.info(f"[{session_id}] Client disconnected")
                break

            except RuntimeError as e:
                if "Cannot call \"receive\" once a disconnect message has been received." in str(e):
                    logger.info(f"[{session_id}] WebSocket already disconnected: {e}")
                    break
                else:
                    logger.error(f"[{session_id}] Message processing error: {e}", exc_info=True)
                    break

            except Exception as e:
                logger.error(f"[{session_id}] Message processing error: {e}", exc_info=True)
                break

    except Exception as e:
        logger.error(f"[{session_id}] WebSocket connection error: {e}", exc_info=True)
        try:
            await websocket.close(code=1011, reason=str(e))
        except Exception as close_error:
            logger.error(f"Failed to close websocket: {close_error}")

    finally:
        # ── STEP 5: Cleanup on disconnect ──
        try:
            # Flush remaining audio
            remaining_text = handler.flush()
            if remaining_text:
                try:
                    response = TranscriptionResponse(
                        type="transcription",
                        text=remaining_text,
                        is_final=True,
                        confidence=0.95,
                        processing_time_ms=100,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    )
                    await websocket.send_json(response.model_dump())
                except Exception as e:
                    logger.warning(f"[{session_id}] Could not send final transcription: {e}")

            # Send final stats (with efficiency metrics)
            final_stats = handler.get_stats()
            stats_response = StatsResponse(
                type="stats",
                data=final_stats,
            )
            try:
                await websocket.send_json(stats_response.model_dump())
            except Exception as e:
                logger.warning(f"[{session_id}] Could not send final stats: {e}")

            logger.info(
                f"[{session_id}] Session ended: {final_stats['transcriptions_count']} transcriptions, "
                f"{final_stats['total_words']} words, "
                f"{final_stats['efficiency_percent']:.1f}% silence skipped"
            )

        except Exception as e:
            logger.error(f"[{session_id}] Error during cleanup: {e}", exc_info=True)

        finally:
            app.state.active_connections -= 1
            logger.info(f"[{session_id}] Connection closed (total: {app.state.active_connections})")


async def _handle_control_message(websocket: WebSocket, handler: AudioStreamHandler, message: dict, session_id: str):
    """
    Handle control messages from client.

    Args:
        websocket: WebSocket connection
        handler: Audio stream handler
        message: Control message dict with 'type' key
        session_id: Session ID for logging
    """
    msg_type = message.get("type")
    timestamp = datetime.now(timezone.utc).isoformat()

    try:
        if msg_type == "reset":
            # Reset handler
            handler.audio_buffer.clear()
            handler.overlap_buffer.clear()
            handler.has_speech_in_buffer = False
            logger.info(f"[{session_id}] Handler reset")
            await websocket.send_json(
                {
                    "type": "control_ack",
                    "action": "reset",
                    "timestamp": timestamp,
                }
            )

        elif msg_type == "flush":
            # Force transcribe buffer
            text = handler.flush()
            response_data = {
                "type": "control_ack",
                "action": "flush",
                "text": text or "",
                "timestamp": timestamp,
            }
            await websocket.send_json(response_data)
            logger.debug(f"[{session_id}] Buffer flushed")

        elif msg_type == "stats":
            # Return session stats
            stats = handler.get_stats()
            stats_response = StatsResponse(
                type="stats",
                data=stats,
            )
            await websocket.send_json(stats_response.model_dump())
            logger.debug(f"[{session_id}] Stats requested")

        elif msg_type == "ping":
            # Echo with timestamp
            await websocket.send_json(
                {
                    "type": "pong",
                    "timestamp": timestamp,
                }
            )
            logger.debug(f"[{session_id}] Ping/pong")

        else:
            logger.warning(f"[{session_id}] Unknown control message type: {msg_type}")
            error = ErrorResponse(
                type="error",
                message=f"Unknown message type: {msg_type}",
                code="UNKNOWN_MESSAGE_TYPE",
            )
            await websocket.send_json(error.model_dump())

    except Exception as e:
        logger.error(f"[{session_id}] Error handling control message: {e}", exc_info=True)
        error = ErrorResponse(
            type="error",
            message=f"Control message error: {str(e)}",
            code="CONTROL_ERROR",
        )
        try:
            await websocket.send_json(error.model_dump())
        except Exception:
            logger.error(f"[{session_id}] Could not send error response")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )