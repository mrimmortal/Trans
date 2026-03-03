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
# AUDIO STREAM HANDLER
# ─────────────────────────────────────────────────────────────────


class AudioStreamHandler:
    """
    Handles real-time audio streaming for a single WebSocket client.
    Accumulates audio chunks and periodically transcribes them.
    """

    def __init__(self, transcription_engine: TranscriptionEngine, config: AudioConfig):
        """
        Initialize stream handler for a client.

        Args:
            transcription_engine: Shared transcription engine
            config: Audio configuration
        """
        self.engine = transcription_engine
        self.config = config
        self.formatter = MedicalFormatter()

        # Audio buffer
        self.audio_buffer = bytearray()
        self.buffer_threshold = config.CHUNK_SIZE_BYTES

        # Session stats
        self.session_start_time = time.time()
        self.audio_received_bytes = 0
        self.chunks_received = 0
        self.transcriptions_count = 0
        self.total_words = 0

    def add_audio_chunk(self, audio_bytes: bytes) -> Optional[str]:
        """
        Add audio chunk to buffer and transcribe if threshold is reached.

        Args:
            audio_bytes: Audio data (int16 PCM, 16kHz, mono)

        Returns:
            Transcribed text if buffer threshold reached, None otherwise
        """
        self.audio_buffer.extend(audio_bytes)
        self.audio_received_bytes += len(audio_bytes)
        self.chunks_received += 1

        # Check if buffer is full
        if len(self.audio_buffer) >= self.buffer_threshold:
            # Force transcription
            result = self._transcribe_buffer()
            return result

        return None

    def _transcribe_buffer(self) -> Optional[str]:
        """
        Transcribe the current audio buffer and clear it.

        Returns:
            Transcribed and formatted text, None if no text
        """
        if len(self.audio_buffer) < self.config.MIN_AUDIO_SAMPLES * 2:
            return None

        try:
            # Transcribe
            result = self.engine.transcribe_audio_bytes(bytes(self.audio_buffer))

            if result.get("error"):
                logger.warning(f"Transcription error: {result['error']}")
                return None

            text = result.get("text", "").strip()
            if not text:
                return None

            # Format text
            text = self.formatter.format(text)

            # Update stats
            self.transcriptions_count += 1
            self.total_words += len(text.split())

            # Clear buffer
            self.audio_buffer.clear()

            return text

        except Exception as e:
            logger.error(f"Error during transcription: {e}", exc_info=True)
            self.audio_buffer.clear()
            return None

    def flush(self) -> Optional[str]:
        """
        Force transcribe any remaining audio in buffer.

        Returns:
            Transcribed text
        """
        if len(self.audio_buffer) == 0:
            return None

        logger.debug(f"Flushing buffer with {len(self.audio_buffer)} bytes")
        return self._transcribe_buffer()

    def get_stats(self) -> dict:
        """Get session statistics"""
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

        # Load transcription engine (loads Whisper model)
        logger.info("Loading Whisper model (this may take 30-60 seconds)...")
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


@app.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns:
        status: "healthy" or "degraded"
        model_loaded: Whether Whisper model is loaded
        active_connections: Number of active WebSocket connections
        timestamp: ISO 8601 timestamp
    """
    try:
        config = app.state.config
        engine = app.state.transcription_engine
        active = app.state.active_connections

        model_loaded = engine.model is not None

        return JSONResponse(
            status_code=200,
            content={
                "status": "healthy" if model_loaded else "degraded",
                "model_loaded": model_loaded,
                "active_connections": active,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )


@app.get("/config")
async def get_config():
    """
    Get server audio configuration.

    Returns:
        Audio format, Whisper model, and processing parameters
    """
    try:
        config = app.state.config

        return JSONResponse(
            status_code=200,
            content={
                "sample_rate": config.SAMPLE_RATE,
                "channels": config.CHANNELS,
                "sample_width": config.SAMPLE_WIDTH,
                "dtype": config.DTYPE,
                "chunk_duration_seconds": config.CHUNK_DURATION_SECONDS,
                "chunk_size_bytes": config.CHUNK_SIZE_BYTES,
                "overlap_duration_seconds": config.OVERLAP_DURATION_SECONDS,
                "model_size": config.MODEL_SIZE,
                "device": config.DEVICE,
                "compute_type": config.COMPUTE_TYPE,
                "vad_filter": config.VAD_FILTER,
            },
        )
    except Exception as e:
        logger.error(f"Config endpoint error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
        )


# ─────────────────────────────────────────────────────────────────
# WEBSOCKET ENDPOINT
# ─────────────────────────────────────────────────────────────────


@app.websocket("/ws/dictate")
async def websocket_dictate(websocket: WebSocket):
    """
    WebSocket endpoint for real-time audio streaming and transcription.

    PROTOCOL:
    - Client → Server: Binary audio data (16-bit PCM, 16kHz, mono)
    - Server → Client: JSON transcription/error messages

    LIFECYCLE:
    1. Accept connection
    2. Send welcome message with audio config
    3. Process audio chunks and control messages
    4. On disconnect: flush buffer, send final stats, cleanup
    """
    try:
        # ── STEP 1: Accept connection ──
        await websocket.accept()
        app.state.active_connections += 1
        session_id = f"session_{int(time.time() * 1000)}"

        logger.info(f"[{session_id}] Client connected (total: {app.state.active_connections})")

        # ── STEP 2: Create handler ──
        handler = AudioStreamHandler(app.state.transcription_engine, app.state.config)

        # ── STEP 3: Send welcome message ──
        welcome = ConnectionResponse(
            type="connected",
            message="Connected to Medical Dictation API",
            config={
                "sample_rate": app.state.config.SAMPLE_RATE,
                "channels": app.state.config.CHANNELS,
                "sample_width": app.state.config.SAMPLE_WIDTH,
                "chunk_duration_seconds": app.state.config.CHUNK_DURATION_SECONDS,
                "chunk_size_bytes": app.state.config.CHUNK_SIZE_BYTES,
                "model": app.state.config.MODEL_SIZE,
                "device": app.state.config.DEVICE,
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
                    logger.info(f"[{session_id}] Received {len(audio_bytes)} bytes of audio")

                    # Add to handler buffer and transcribe if ready
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
                        logger.debug(f"[{session_id}] Sent transcription: {text[:50]}...")

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

            # Send final stats
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
                f"{final_stats['total_words']} words"
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

