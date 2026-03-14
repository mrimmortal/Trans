"""FastAPI application with WebSocket audio streaming and template management"""

# ============================================
# CUDA PATH FIX FOR VIRTUAL ENVIRONMENT
# MUST BE AT THE VERY TOP BEFORE ALL IMPORTS
# ============================================
import os
import sys
import glob

if sys.platform == "win32":
    try:
        site_packages_dirs = [p for p in sys.path if 'site-packages' in p.lower()]
        
        if not site_packages_dirs:
            raise ImportError("site-packages not found in sys.path")
        
        site_packages = site_packages_dirs[0]
        nvidia_base = os.path.join(site_packages, 'nvidia')
        
        if not os.path.exists(nvidia_base):
            raise ImportError(f"nvidia directory not found at {nvidia_base}")
        
        cuda_paths = []
        
        for subdir in ['cublas', 'cudnn']:
            base_dir = os.path.join(nvidia_base, subdir)
            if os.path.exists(base_dir):
                for root, dirs, files in os.walk(base_dir):
                    dll_files = [f for f in files if f.endswith('.dll')]
                    if dll_files and root not in cuda_paths:
                        cuda_paths.append(root)
        
        if not cuda_paths:
            raise ImportError("No CUDA DLL directories found")
        
        path_addition = os.pathsep.join(cuda_paths)
        os.environ['PATH'] = path_addition + os.pathsep + os.environ.get('PATH', '')
        
        print(f"✓ Added {len(cuda_paths)} CUDA path(s) to system PATH")
        for p in cuda_paths:
            dll_count = len(glob.glob(os.path.join(p, '*.dll')))
            print(f"  - {os.path.basename(os.path.dirname(p))}/bin ({dll_count} DLLs)")
            
    except Exception as e:
        print(f"⚠ CUDA setup failed: {e}")
        print("  Falling back to CPU mode...")
        os.environ['DEVICE'] = 'cpu'
        os.environ['COMPUTE_TYPE'] = 'int8'

# ============================================
# NOW import everything else
# ============================================
from dotenv import load_dotenv
load_dotenv()

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
from app.services.command_processor import CommandProcessor, VoiceCommand, CommandType
from app.models.schemas import (
    TranscriptionResponse,
    ConnectionResponse,
    ErrorResponse,
    StatsResponse,
)

# Import database and template modules
from app.database.init_db import init_database, get_database_info
from app.api.template_routes import router as template_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────
# AUDIO STREAM HANDLER (WITH VAD + COMMANDS)
# ─────────────────────────────────────────────────────────────────


class AudioStreamHandler:
    """
    Handles real-time audio streaming with VAD-based dynamic buffering
    and voice command processing.
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
        self.command_processor = CommandProcessor()

        # Dynamic audio buffers
        self.audio_buffer = bytearray()
        self.overlap_buffer = bytearray()
        
        # VAD state tracking
        self.consecutive_silence_chunks = 0
        self.last_speech_time = time.time()
        self.has_speech_in_buffer = False
        
        # Buffer size limits
        self.min_buffer_size = config.MIN_CHUNK_SIZE_BYTES
        self.max_buffer_size = config.MAX_CHUNK_SIZE_BYTES
        self.overlap_size = config.OVERLAP_SIZE_BYTES

        # Session stats
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
            audio_bytes: Audio data (int16 PCM, 16kHz, mono)

        Returns:
            Dict with 'text' and 'commands' if transcription triggered, None otherwise
        """
        self.audio_received_bytes += len(audio_bytes)
        self.chunks_received += 1
        
        # ── STEP 1: DETECT SPEECH IN THIS CHUNK ──
        vad_result = self.engine.detect_speech(audio_bytes)
        
        if vad_result['has_speech']:
            # ── SPEECH DETECTED ──
            logger.debug(f"Speech detected (prob={vad_result['speech_prob']:.2f})")
            
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

    def _transcribe_buffer(self) -> Optional[dict]:
        """
        Transcribe the current audio buffer with overlap and command processing.

        Returns:
            Dict with 'text' and 'commands' keys, or None
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

            # ── FORMAT TEXT ──
            text = self.formatter.format(text)

            # ── PROCESS VOICE COMMANDS ──
            processed_text, commands = self.command_processor.process(text)
            self.commands_executed += len(commands)

            # ── SAVE OVERLAP FOR NEXT CHUNK ──
            if len(self.audio_buffer) > self.overlap_size:
                self.overlap_buffer = self.audio_buffer[-self.overlap_size:]
            else:
                self.overlap_buffer = bytearray(self.audio_buffer)
            
            logger.debug(f"Saved {len(self.overlap_buffer)} bytes for overlap")

            # ── UPDATE STATS ──
            self.transcriptions_count += 1
            if processed_text:
                self.total_words += len(processed_text.split())

            # ── CLEAR BUFFER ──
            self.audio_buffer.clear()
            self.has_speech_in_buffer = False

            # ── RETURN RESULT WITH COMMANDS ──
            return {
                "text": processed_text,
                "commands": [
                    {
                        "type": cmd.command_type.value if hasattr(cmd.command_type, 'value') else str(cmd.command_type),
                        "action": cmd.action,
                        "original_text": cmd.original_text,
                        "replacement": cmd.replacement,
                    }
                    for cmd in commands
                ]
            }

        except Exception as e:
            logger.error(f"Error during transcription: {e}", exc_info=True)
            self.audio_buffer.clear()
            self.overlap_buffer.clear()
            self.has_speech_in_buffer = False
            return None

    def flush(self) -> Optional[dict]:
        """
        Force transcribe any remaining audio in buffer.

        Returns:
            Dict with 'text' and 'commands', or None
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
            "silence_chunks_skipped": self.silence_chunks_skipped,
            "efficiency_percent": (self.silence_chunks_skipped / max(self.chunks_received, 1)) * 100,
            "commands_executed": self.commands_executed,
        }


# ─────────────────────────────────────────────────────────────────
# FASTAPI LIFESPAN
# ─────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle with async context manager.
    Initializes database, models, and template manager on startup.
    """
    # ══════════════════════════════════════════════════════════════
    # STARTUP
    # ══════════════════════════════════════════════════════════════
    logger.info("=" * 80)
    logger.info("MEDICAL DICTATION API - STARTING UP")
    logger.info("=" * 80)

    try:
        # ── Step 1: Initialize Database ──
        logger.info("Initializing SQLite database...")
        seed_defaults = os.getenv("SEED_DEFAULT_TEMPLATES", "true").lower() == "true"
        db_result = init_database(seed_defaults=seed_defaults)
        db_info = get_database_info()
        logger.info(f"✓ Database ready: {db_info['active_templates']} templates")
        
        # ── Step 2: Load Audio Config ──
        config = AudioConfig()
        logger.info(f"✓ Audio Config: {config.MODEL_SIZE} on {config.DEVICE}")

        # ── Step 3: Load Whisper Model ──
        logger.info("Loading Whisper model and VAD (this may take 30-60 seconds)...")
        engine = TranscriptionEngine(config)
        logger.info("✓ Whisper model loaded successfully")

        # ── Step 4: Initialize Template Manager ──
        logger.info("Initializing template manager...")
        from app.services.template_manager import get_template_manager
        template_manager = get_template_manager()
        template_stats = template_manager.get_stats()
        logger.info(f"✓ Template manager ready: {template_stats['registered_patterns']} patterns registered")

        # ── Store in app state ──
        app.state.config = config
        app.state.transcription_engine = engine
        app.state.active_connections = 0
        app.state.template_manager = template_manager

        logger.info("=" * 80)
        logger.info("✓ APPLICATION READY FOR REQUESTS")
        logger.info("=" * 80)
        logger.info("")
        logger.info(f"  📍 API:         http://0.0.0.0:8000")
        logger.info(f"  📚 Docs:        http://0.0.0.0:8000/docs")
        logger.info(f"  🔌 WebSocket:   ws://0.0.0.0:8000/ws/audio")
        logger.info(f"  📝 Templates:   http://0.0.0.0:8000/api/templates")
        logger.info("")
        logger.info("=" * 80)

    except Exception as e:
        logger.critical(f"Failed to start application: {e}", exc_info=True)
        raise

    yield

    # ══════════════════════════════════════════════════════════════
    # SHUTDOWN
    # ══════════════════════════════════════════════════════════════
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
    description="""
    Real-time medical voice dictation with WebSocket audio streaming.
    
    ## Features
    - 🎤 Real-time audio transcription via WebSocket
    - 🗣️ Voice Activity Detection (VAD) for efficient processing
    - 📝 Custom template management with SQLite storage
    - ⚡ Voice commands for formatting and templates
    
    ## WebSocket Endpoint
    Connect to `/ws/audio` for real-time audio streaming.
    
    ## Template API
    Use `/api/templates` endpoints to manage custom voice-activated templates.
    """,
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────
# INCLUDE ROUTERS
# ─────────────────────────────────────────────────────────────────

# Template API routes
app.include_router(template_router, prefix="/api")


# ─────────────────────────────────────────────────────────────────
# REST ENDPOINTS
# ─────────────────────────────────────────────────────────────────


@app.get("/")
async def root():
    """Root endpoint with API overview"""
    return {
        "status": "online",
        "service": "Medical Dictation API",
        "version": "1.0.0",
        "active_connections": app.state.active_connections,
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "config": "/config",
            "websocket": "/ws/audio",
            "templates": "/api/templates"
        }
    }


@app.get("/health")
async def health():
    """Detailed health check with model and database status"""
    try:
        engine = app.state.transcription_engine
        config = app.state.config
        
        # Get database info
        db_info = get_database_info()
        
        # Get template stats
        from app.services.template_manager import get_template_manager
        template_stats = get_template_manager().get_stats()
        
        vad_status = "enabled" if engine.vad_model is not None else "disabled (fallback to RMS)"

        return JSONResponse(
            content={
                "status": "healthy",
                "model": {
                    "loaded": engine.model is not None,
                    "size": config.MODEL_SIZE,
                    "device": config.DEVICE,
                },
                "vad_status": vad_status,
                "database": {
                    "path": db_info["database_path"],
                    "templates": db_info["active_templates"],
                    "size_kb": db_info["file_size_kb"]
                },
                "templates": {
                    "total": template_stats["total_templates"],
                    "registered_patterns": template_stats["registered_patterns"],
                    "categories": template_stats["categories"]
                },
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
    """Get current audio and system configuration"""
    try:
        config = app.state.config
        
        # Get template manager stats
        from app.services.template_manager import get_template_manager
        template_stats = get_template_manager().get_stats()
        
        return {
            "audio": {
                "sample_rate": config.SAMPLE_RATE,
                "channels": config.CHANNELS,
                "sample_width": config.SAMPLE_WIDTH,
                "min_chunk_bytes": config.MIN_CHUNK_SIZE_BYTES,
                "max_chunk_bytes": config.MAX_CHUNK_SIZE_BYTES,
                "overlap_bytes": config.OVERLAP_SIZE_BYTES,
            },
            "model": {
                "size": config.MODEL_SIZE,
                "device": config.DEVICE,
            },
            "vad_enabled": app.state.transcription_engine.vad_model is not None,
            "templates": {
                "total": template_stats["total_templates"],
                "categories": template_stats["categories"]
            }
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
    WebSocket endpoint for real-time audio streaming with VAD and commands.

    PROTOCOL:
    - Client → Server: Binary audio data (16-bit PCM, 16kHz, mono)
    - Client → Server: JSON control messages
    - Server → Client: JSON transcription/error/command messages
    """
    session_id = f"session_{int(time.time() * 1000)}"
    handler = None

    try:
        # ── STEP 1: Accept connection ──
        await websocket.accept()
        app.state.active_connections += 1

        logger.info(f"[{session_id}] Client connected (total: {app.state.active_connections})")

        # ── STEP 2: Create handler ──
        handler = AudioStreamHandler(app.state.transcription_engine, app.state.config)

        # ── STEP 3: Send welcome message ──
        welcome_config = {
            "sample_rate": app.state.config.SAMPLE_RATE,
            "channels": app.state.config.CHANNELS,
            "sample_width": app.state.config.SAMPLE_WIDTH,
            "min_chunk_bytes": app.state.config.MIN_CHUNK_SIZE_BYTES,
            "max_chunk_bytes": app.state.config.MAX_CHUNK_SIZE_BYTES,
            "overlap_bytes": app.state.config.OVERLAP_SIZE_BYTES,
            "model": app.state.config.MODEL_SIZE,
            "device": app.state.config.DEVICE,
            "vad_enabled": app.state.transcription_engine.vad_model is not None,
            "commands_enabled": True,
            "available_commands": handler.command_processor.get_available_commands(),
        }
        
        welcome = ConnectionResponse(
            type="connected",
            message="Connected to Medical Dictation API with VAD, Voice Commands, and Custom Templates",
            config=welcome_config,
        )
        await websocket.send_json(welcome.model_dump())
        logger.debug(f"[{session_id}] Sent welcome message")

        # ── STEP 4: Message receive loop ──
        while True:
            try:
                data = await websocket.receive()

                # Binary audio data
                if "bytes" in data:
                    audio_bytes = data["bytes"]
                    logger.debug(f"[{session_id}] Received {len(audio_bytes)} bytes of audio")

                    result = handler.add_audio_chunk(audio_bytes)

                    if result:
                        # Send transcription with commands
                        response = {
                            "type": "transcription",
                            "text": result["text"],
                            "commands": result.get("commands", []),
                            "is_final": True,
                            "confidence": 0.95,
                            "processing_time_ms": 50,
                            "timestamp": datetime.now(timezone.utc).timestamp(),
                        }
                        await websocket.send_json(response)
                        
                        cmd_count = len(result.get("commands", []))
                        if cmd_count > 0:
                            logger.info(f"[{session_id}] Transcription with {cmd_count} commands: {result['text'][:50]}...")
                        else:
                            logger.info(f"[{session_id}] Transcription: {result['text'][:50]}...")

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
                if "disconnect" in str(e).lower():
                    logger.info(f"[{session_id}] WebSocket already disconnected")
                    break
                else:
                    logger.error(f"[{session_id}] Error: {e}", exc_info=True)
                    break

            except Exception as e:
                logger.error(f"[{session_id}] Error: {e}", exc_info=True)
                break

    except Exception as e:
        logger.error(f"[{session_id}] WebSocket connection error: {e}", exc_info=True)
        try:
            await websocket.close(code=1011, reason=str(e))
        except Exception:
            pass

    finally:
        # ── STEP 5: Cleanup on disconnect ──
        try:
            if handler:
                # Flush remaining audio
                remaining = handler.flush()
                if remaining:
                    try:
                        response = {
                            "type": "transcription",
                            "text": remaining["text"],
                            "commands": remaining.get("commands", []),
                            "is_final": True,
                            "confidence": 0.95,
                            "processing_time_ms": 100,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                        await websocket.send_json(response)
                    except Exception as e:
                        logger.warning(f"[{session_id}] Could not send final transcription: {e}")

                # Send final stats
                final_stats = handler.get_stats()
                try:
                    await websocket.send_json({"type": "stats", "data": final_stats})
                except Exception as e:
                    logger.warning(f"[{session_id}] Could not send final stats: {e}")

                logger.info(
                    f"[{session_id}] Session ended: {final_stats['transcriptions_count']} transcriptions, "
                    f"{final_stats['total_words']} words, "
                    f"{final_stats['commands_executed']} commands, "
                    f"{final_stats['efficiency_percent']:.1f}% silence skipped"
                )

        except Exception as e:
            logger.error(f"[{session_id}] Cleanup error: {e}", exc_info=True)

        finally:
            app.state.active_connections -= 1
            logger.info(f"[{session_id}] Connection closed (total: {app.state.active_connections})")


# ─────────────────────────────────────────────────────────────────
# CONTROL MESSAGE HANDLER
# ─────────────────────────────────────────────────────────────────


async def _handle_control_message(
    websocket: WebSocket, 
    handler: AudioStreamHandler, 
    message: dict, 
    session_id: str
):
    """
    Handle ALL control messages from client including command-related ones.
    """
    msg_type = message.get("type")
    timestamp = datetime.now(timezone.utc).isoformat()

    try:
        # ══════════════════════════════════════════════════════════
        # BASIC CONTROL MESSAGES
        # ══════════════════════════════════════════════════════════
        
        if msg_type == "reset":
            handler.audio_buffer.clear()
            handler.overlap_buffer.clear()
            handler.has_speech_in_buffer = False
            handler.consecutive_silence_chunks = 0
            logger.info(f"[{session_id}] Handler reset")
            await websocket.send_json({
                "type": "control_ack",
                "action": "reset",
                "timestamp": timestamp,
            })

        elif msg_type == "flush":
            result = handler.flush()
            response_data = {
                "type": "control_ack",
                "action": "flush",
                "text": result["text"] if result else "",
                "commands": result.get("commands", []) if result else [],
                "timestamp": timestamp,
            }
            await websocket.send_json(response_data)
            logger.debug(f"[{session_id}] Buffer flushed")

        elif msg_type == "stats":
            stats = handler.get_stats()
            await websocket.send_json({"type": "stats", "data": stats})
            logger.debug(f"[{session_id}] Stats requested")

        elif msg_type == "ping":
            await websocket.send_json({
                "type": "pong",
                "timestamp": timestamp,
            })

        # ══════════════════════════════════════════════════════════
        # COMMAND-RELATED CONTROL MESSAGES
        # ══════════════════════════════════════════════════════════
        
        elif msg_type == "enable_commands":
            handler.command_processor.enable()
            await websocket.send_json({
                "type": "control_ack",
                "action": "enable_commands",
                "timestamp": timestamp,
            })
            logger.info(f"[{session_id}] Commands enabled")

        elif msg_type == "disable_commands":
            handler.command_processor.disable()
            await websocket.send_json({
                "type": "control_ack",
                "action": "disable_commands",
                "timestamp": timestamp,
            })
            logger.info(f"[{session_id}] Commands disabled")

        elif msg_type == "get_commands":
            commands = handler.command_processor.get_available_commands()
            await websocket.send_json({
                "type": "available_commands",
                "commands_list": commands,
                "timestamp": timestamp,
            })
            logger.debug(f"[{session_id}] Commands list sent")

        elif msg_type == "register_command":
            # Register a custom voice command
            pattern = message.get("pattern")
            replacement = message.get("replacement", "")
            action = message.get("action", "custom")
            
            if pattern:
                handler.command_processor.register_custom_command(
                    rf"\b{pattern}\b",
                    VoiceCommand(
                        command_type=CommandType.CUSTOM,
                        action=action,
                        replacement=replacement
                    )
                )
                await websocket.send_json({
                    "type": "control_ack",
                    "action": "register_command",
                    "pattern": pattern,
                    "timestamp": timestamp,
                })
                logger.info(f"[{session_id}] Custom command registered: '{pattern}' → '{replacement[:30]}...'")
            else:
                await websocket.send_json({
                    "type": "error",
                    "message": "Pattern required for register_command",
                    "code": "MISSING_PATTERN",
                })

        elif msg_type == "unregister_command":
            pattern = message.get("pattern")
            if pattern:
                handler.command_processor.unregister_custom_command(rf"\b{pattern}\b")
                await websocket.send_json({
                    "type": "control_ack",
                    "action": "unregister_command",
                    "pattern": pattern,
                    "timestamp": timestamp,
                })
                logger.info(f"[{session_id}] Custom command unregistered: '{pattern}'")

        elif msg_type == "command_history":
            limit = message.get("limit", 50)
            history = handler.command_processor.get_command_history(limit)
            await websocket.send_json({
                "type": "command_history",
                "history": history,
                "timestamp": timestamp,
            })
            logger.debug(f"[{session_id}] Command history sent")

        elif msg_type == "clear_command_history":
            handler.command_processor.clear_history()
            await websocket.send_json({
                "type": "control_ack",
                "action": "clear_command_history",
                "timestamp": timestamp,
            })

        # ══════════════════════════════════════════════════════════
        # TEMPLATE-RELATED CONTROL MESSAGES
        # ══════════════════════════════════════════════════════════
        
        elif msg_type == "get_templates":
            # Get available templates
            from app.services.template_manager import get_template_manager
            manager = get_template_manager()
            templates = manager.list_templates()
            
            await websocket.send_json({
                "type": "templates_list",
                "templates": [
                    {
                        "name": t["name"],
                        "trigger_phrases": t["trigger_phrases"],
                        "category": t["category"],
                        "description": t["description"]
                    }
                    for t in templates
                ],
                "timestamp": timestamp,
            })
            logger.debug(f"[{session_id}] Templates list sent")

        elif msg_type == "refresh_templates":
            # Refresh templates from database
            from app.services.template_manager import get_template_manager
            manager = get_template_manager()
            manager.refresh()
            stats = manager.get_stats()
            
            await websocket.send_json({
                "type": "control_ack",
                "action": "refresh_templates",
                "stats": stats,
                "timestamp": timestamp,
            })
            logger.info(f"[{session_id}] Templates refreshed")

        # ══════════════════════════════════════════════════════════
        # UNKNOWN MESSAGE TYPE
        # ══════════════════════════════════════════════════════════
        
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


# ─────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    logger.info("=" * 80)
    logger.info("")
    logger.info("🚀 Starting server...")
    logger.info(f"📍 API:        http://0.0.0.0:8000")
    logger.info(f"📚 Docs:       http://0.0.0.0:8000/docs")
    logger.info(f"🔌 WebSocket:  ws://0.0.0.0:8000/ws/audio")
    logger.info(f"📝 Templates:  http://0.0.0.0:8000/api/templates")
    logger.info("")
    logger.info("Press Ctrl+C to stop the server")
    logger.info("=" * 80)

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )