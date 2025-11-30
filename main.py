"""
Main entry point for Paraphrase Engine v1.0
Supports both polling and webhook modes
"""

import logging
import sys
import os
import uvicorn
from dotenv import load_dotenv
from pathlib import Path

# Load .env file explicitly before importing settings
project_root = Path(__file__).resolve().parent
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file)
else:
    load_dotenv()

from paraphrase_engine.config import settings
from webhook_server import app

logger = logging.getLogger(__name__)

def main():
    """Main entry point - uses webhook mode for production"""
    logger.info("=" * 60)
    logger.info("Starting Paraphrase Engine v1.0 (Webhook Mode)")
    logger.info("=" * 60)
    logger.info(f"Environment: {settings.app_env}")
    logger.info(f"Log level: {settings.log_level}")

    if not settings.telegram_bot_token:
        logger.error("TELEGRAM_BOT_TOKEN not configured!")
        sys.exit(1)

    port = int(os.getenv('PORT', '10000'))
    logger.info(f"Starting Uvicorn server on host 0.0.0.0:{port}")
    try:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=port
        )
    except Exception as e:
        logger.error(f"Fatal error during Uvicorn startup: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
