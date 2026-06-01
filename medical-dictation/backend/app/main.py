"""FastAPI application with WebSocket audio streaming."""

from dotenv import load_dotenv
load_dotenv()

import logging
import json
import time
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.api.llm_routes import router as llm_router
from app.api.system_routes import router as system_router
from app.api.tts_routes import router as tts_router
from app.audio_config import AudioConfig
from app.dependencies import create_stt_service
from app.models.schemas import (
    ConnectionResponse,
    ErrorResponse,
)
from app.websocket.audio_stream_handler import AudioStreamHandler
from app.websocket.control_messages import handle_control_message
from app.websocket.responses import build_transcription_message, build_welcome_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────
# FASTAPI LIFESPAN
# ─────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle with async context manager.
    Initializes audio configuration and transcription models on startup.
    """
    # ══════════════════════════════════════════════════════════════
    # STARTUP
    # ══════════════════════════════════════════════════════════════
    logger.info("=" * 80)
    logger.info("TRANSCRIPTION TEMPLATE API - STARTING UP")
    logger.info("=" * 80)

    try:
        # ── Step 1: Load Audio Config ──
        config = AudioConfig()
        logger.info(f"✓ Audio Config: {config.MODEL_SIZE} on {config.DEVICE}")

        # ── Step 2: Load Whisper Model ──
        logger.info("Loading Whisper model and VAD (this may take 30-60 seconds)...")
        stt_service = create_stt_service(config)
        logger.info("✓ Whisper model loaded successfully")

        # ── Store in app state ──
        app.state.config = config
        app.state.stt_service = stt_service
        app.state.active_connections = 0

        logger.info("=" * 80)
        logger.info("✓ APPLICATION READY FOR REQUESTS")
        logger.info("=" * 80)
        logger.info("")
        logger.info(f"  📍 API:         http://0.0.0.0:8000")
        logger.info(f"  📚 Docs:        http://0.0.0.0:8000/docs")
        logger.info(f"  🔌 WebSocket:   ws://0.0.0.0:8000/ws/audio")
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
    title="Transcription Template API",
    description="""
    Real-time voice transcription with WebSocket audio streaming.
    
    ## Features
    - 🎤 Real-time audio transcription via WebSocket
    - 🗣️ Voice Activity Detection (VAD) for efficient processing
    - 🧩 Wrapper-ready domain adapter layer
    
    ## WebSocket Endpoint
    Connect to `/ws/audio` for real-time audio streaming.
    """,
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=AudioConfig().CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system_router)
app.include_router(llm_router)
app.include_router(tts_router)


# ─────────────────────────────────────────────────────────────────
# WEBSOCKET ENDPOINT
# ─────────────────────────────────────────────────────────────────


@app.websocket("/ws/audio")
async def websocket_audio_stream(websocket: WebSocket, domain: Optional[str] = None):
    """
    WebSocket endpoint for real-time audio streaming with VAD and commands.

    PROTOCOL:
    - Client → Server: Binary audio data (16-bit PCM, 16kHz, mono)
    - Client → Server: JSON control messages
    - Server → Client: JSON transcription/error/command messages
    """
    session_id = f"session_{int(time.time() * 1000)}"
    handler = None
    client_disconnected = False

    try:
        # ── STEP 1: Accept connection ──
        await websocket.accept()
        app.state.active_connections += 1

        logger.info(f"[{session_id}] Client connected (total: {app.state.active_connections})")

        # ── STEP 2: Create handler ──
        handler = AudioStreamHandler(app.state.stt_service, app.state.config, domain=domain)

        # ── STEP 3: Send welcome message ──
        welcome_config = build_welcome_config(
            app.state.config,
            app.state.stt_service,
            handler,
        )
        
        welcome = ConnectionResponse(
            type="connected",
            message="Connected to Transcription Template API",
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
                        response = build_transcription_message(
                            result,
                            fallback_domain=handler.domain,
                        )
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
                        await handle_control_message(websocket, handler, control_msg, session_id)
                    except json.JSONDecodeError:
                        logger.warning(f"[{session_id}] Invalid JSON control message")
                        error = ErrorResponse(
                            type="error",
                            message="Invalid JSON control message",
                            code="INVALID_JSON",
                        )
                        await websocket.send_json(error.model_dump())

            except WebSocketDisconnect:
                client_disconnected = True
                logger.info(f"[{session_id}] Client disconnected")
                break

            except RuntimeError as e:
                if "disconnect" in str(e).lower():
                    client_disconnected = True
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
                    if not client_disconnected:
                        try:
                            response = build_transcription_message(
                                remaining,
                                fallback_domain=handler.domain,
                                timestamp_format="iso",
                            )
                            await websocket.send_json(response)
                        except Exception as e:
                            logger.debug(f"[{session_id}] Final transcription not sent after disconnect: {e}")

                # Send final stats
                final_stats = handler.get_stats()
                if not client_disconnected:
                    try:
                        await websocket.send_json({"type": "stats", "data": final_stats})
                    except Exception as e:
                        logger.debug(f"[{session_id}] Final stats not sent after disconnect: {e}")

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
    logger.info("")
    logger.info("Press Ctrl+C to stop the server")
    logger.info("=" * 80)

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
