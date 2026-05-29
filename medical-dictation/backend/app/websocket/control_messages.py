"""Control message handling for the audio WebSocket endpoint."""

import logging
import re
from datetime import datetime, timezone

from fastapi import WebSocket

from app.models.schemas import ErrorResponse
from app.services.command_processor import CommandType, VoiceCommand
from app.websocket.audio_stream_handler import AudioStreamHandler

logger = logging.getLogger(__name__)


async def handle_control_message(
    websocket: WebSocket,
    handler: AudioStreamHandler,
    message: dict,
    session_id: str,
):
    """Handle control messages from the WebSocket client."""
    msg_type = message.get("type")
    timestamp = datetime.now(timezone.utc).isoformat()

    try:
        if msg_type == "reset":
            handler.audio_buffer.clear()
            handler.overlap_buffer.clear()
            handler.has_speech_in_buffer = False
            handler.consecutive_silence_chunks = 0
            logger.info("[%s] Handler reset", session_id)
            await websocket.send_json(
                {
                    "type": "control_ack",
                    "action": "reset",
                    "timestamp": timestamp,
                }
            )

        elif msg_type == "flush":
            result = handler.flush()
            await websocket.send_json(
                {
                    "type": "control_ack",
                    "action": "flush",
                    "text": result["text"] if result else "",
                    "commands": result.get("commands", []) if result else [],
                    "timestamp": timestamp,
                }
            )
            logger.debug("[%s] Buffer flushed", session_id)

        elif msg_type == "stats":
            stats = handler.get_stats()
            await websocket.send_json({"type": "stats", "data": stats})
            logger.debug("[%s] Stats requested", session_id)

        elif msg_type == "ping":
            await websocket.send_json(
                {
                    "type": "pong",
                    "timestamp": timestamp,
                }
            )

        elif msg_type == "enable_commands":
            handler.command_processor.enable()
            await websocket.send_json(
                {
                    "type": "control_ack",
                    "action": "enable_commands",
                    "timestamp": timestamp,
                }
            )
            logger.info("[%s] Commands enabled", session_id)

        elif msg_type == "disable_commands":
            handler.command_processor.disable()
            await websocket.send_json(
                {
                    "type": "control_ack",
                    "action": "disable_commands",
                    "timestamp": timestamp,
                }
            )
            logger.info("[%s] Commands disabled", session_id)

        elif msg_type == "get_commands":
            commands = handler.command_processor.get_available_commands()
            await websocket.send_json(
                {
                    "type": "available_commands",
                    "commands_list": commands,
                    "timestamp": timestamp,
                }
            )
            logger.debug("[%s] Commands list sent", session_id)

        elif msg_type == "register_command":
            pattern = message.get("pattern")
            replacement = message.get("replacement", "")
            action = message.get("action", "custom")

            if pattern:
                handler.command_processor.register_custom_command(
                    rf"\b{pattern}\b",
                    VoiceCommand(
                        command_type=CommandType.CUSTOM,
                        action=action,
                        replacement=replacement,
                    ),
                )
                await websocket.send_json(
                    {
                        "type": "control_ack",
                        "action": "register_command",
                        "pattern": pattern,
                        "timestamp": timestamp,
                    }
                )
                logger.info(
                    "[%s] Custom command registered: '%s' -> '%s...'",
                    session_id,
                    pattern,
                    replacement[:30],
                )
            else:
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": "Pattern required for register_command",
                        "code": "MISSING_PATTERN",
                    }
                )

        elif msg_type == "unregister_command":
            pattern = message.get("pattern")
            if pattern:
                handler.command_processor.unregister_custom_command(rf"\b{pattern}\b")
                await websocket.send_json(
                    {
                        "type": "control_ack",
                        "action": "unregister_command",
                        "pattern": pattern,
                        "timestamp": timestamp,
                    }
                )
                logger.info("[%s] Custom command unregistered: '%s'", session_id, pattern)

        elif msg_type == "command_history":
            limit = message.get("limit", 50)
            history = handler.command_processor.get_command_history(limit)
            await websocket.send_json(
                {
                    "type": "command_history",
                    "history": history,
                    "timestamp": timestamp,
                }
            )
            logger.debug("[%s] Command history sent", session_id)

        elif msg_type == "clear_command_history":
            handler.command_processor.clear_history()
            await websocket.send_json(
                {
                    "type": "control_ack",
                    "action": "clear_command_history",
                    "timestamp": timestamp,
                }
            )

        else:
            logger.warning("[%s] Unknown control message type: %s", session_id, msg_type)
            error = ErrorResponse(
                type="error",
                message=f"Unknown message type: {msg_type}",
                code="UNKNOWN_MESSAGE_TYPE",
            )
            await websocket.send_json(error.model_dump())

    except Exception as e:
        logger.error("[%s] Error handling control message: %s", session_id, e, exc_info=True)
        error = ErrorResponse(
            type="error",
            message=f"Control message error: {str(e)}",
            code="CONTROL_ERROR",
        )
        try:
            await websocket.send_json(error.model_dump())
        except Exception:
            logger.error("[%s] Could not send error response", session_id)
