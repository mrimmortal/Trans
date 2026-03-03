"""Script to run the FastAPI development server with WebSocket support"""

import os
import sys
import logging
from dotenv import load_dotenv
import uvicorn

from app.audio_config import AudioConfig

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)


def main():
    """Run the FastAPI development server"""
    try:
        # Load configuration
        config = AudioConfig()

        host = config.HOST
        port = config.PORT

        logger.info("=" * 80)
        logger.info("MEDICAL DICTATION API - DEVELOPMENT SERVER")
        logger.info("=" * 80)
        logger.info(f"Host:        {host}")
        logger.info(f"Port:        {port}")
        logger.info(f"Model:       {config.MODEL_SIZE}")
        logger.info(f"Device:      {config.DEVICE}")
        logger.info(f"Compute:     {config.COMPUTE_TYPE}")
        logger.info("=" * 80)
        logger.info("")
        logger.info("🚀 Starting server...")
        logger.info(f"📍 API:      http://{host}:{port}")
        logger.info(f"📚 Docs:     http://{host}:{port}/docs")
        logger.info(f"🔌 WebSocket: ws://{host}:{port}/ws/dictate")
        logger.info("")
        logger.info("Press Ctrl+C to stop the server")
        logger.info("=" * 80)

        # Run Uvicorn
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            reload=True,
            log_level="info",
            # WebSocket configuration
            ws_max_size=16 * 1024 * 1024,  # 16MB max message size
            ws_ping_interval=30,  # Send ping every 30 seconds
            ws_ping_timeout=10,  # Wait 10 seconds for pong
            # Additional settings
            access_log=True,
        )

    except KeyboardInterrupt:
        logger.info("\n" + "=" * 80)
        logger.info("Server stopped by user")
        logger.info("=" * 80)
        sys.exit(0)

    except Exception as e:
        logger.critical(f"Failed to start server: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

