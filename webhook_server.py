"""
Webhook server for Paraphrase Engine v1.0
Compatible with Render deployment
"""

import asyncio
import logging
import os
from fastapi import FastAPI, Request, Response
from telegram import Update
from dotenv import load_dotenv
from pathlib import Path

# Load .env file explicitly
project_root = Path(__file__).resolve().parent
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file)
else:
    # Try loading from current directory
    load_dotenv()

from paraphrase_engine.config import settings
from paraphrase_engine.block1_telegram_bot.bot import TelegramBotInterface

# Basic logging setup
logging.basicConfig(
    level=getattr(logging, settings.log_level, "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI()

logger.info("Initializing Telegram bot interface...")
try:
    # Bot setup
    bot_interface = TelegramBotInterface()
    logger.info("Telegram bot interface initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Telegram bot interface: {e}", exc_info=True)
    raise

# Use the bot token as a secret path to avoid random requests
SECRET_PATH = settings.telegram_bot_token

# Validate that token is configured
if not SECRET_PATH:
    logger.error("TELEGRAM_BOT_TOKEN is not configured! Webhook endpoint will not work.")
else:
    logger.info(f"Bot token configured (length: {len(SECRET_PATH)})")

@app.on_event("startup")
async def startup_event():
    """On startup, set the webhook to point to this server."""
    logger.info("Starting up webhook server...")
    logger.info(f"APP_ENV: {settings.app_env}")
    
    try:
        await bot_interface.application.initialize()
        logger.info("Bot application initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize bot application: {e}", exc_info=True)
        raise
    
    if not SECRET_PATH:
        logger.error("TELEGRAM_BOT_TOKEN is empty! Cannot set webhook.")
        return
    
    # Determine webhook URL - try multiple sources
    webhook_base_url = (
        os.getenv("RENDER_EXTERNAL_URL") or  # Render hosting
        os.getenv("WEBHOOK_BASE_URL") or      # Custom environment variable
        os.getenv("WEBHOOK_URL") or           # Alternative env var
        "https://plagiatanet.by"              # Default domain
    )
    
    if settings.app_env == "production":
        webhook_url = f"{webhook_base_url}/{SECRET_PATH}"
        # Mask the token in logs for security (show only first 4 and last 4 chars)
        masked_path = f"{SECRET_PATH[:4]}...{SECRET_PATH[-4:]}" if len(SECRET_PATH) > 8 else "***"
        masked_url = f"{webhook_base_url}/{masked_path}"
        logger.info(f"Setting webhook to {masked_url}")
        
        try:
            result = await bot_interface.application.bot.set_webhook(
                url=webhook_url,
                allowed_updates=Update.ALL_TYPES
            )
            logger.info(f"Webhook set successfully: {result}")
            
            # Verify webhook info
            webhook_info = await bot_interface.application.bot.get_webhook_info()
            logger.info(f"Webhook info: URL={webhook_info.url}, pending_update_count={webhook_info.pending_update_count}")
        except Exception as e:
            logger.error(f"Failed to set webhook: {e}", exc_info=True)
    else:
        logger.warning("Not setting webhook in development mode. Set APP_ENV=production to enable.")

@app.on_event("shutdown")
async def shutdown_event():
    """On shutdown, remove the webhook."""
    if settings.app_env == "production":
        logger.info("Deleting webhook")
        try:
            await bot_interface.application.bot.delete_webhook()
        except Exception as e:
            logger.error(f"Error deleting webhook: {e}", exc_info=True)
    
    logger.info("Shutting down bot application")

# Webhook endpoint - only create if token is configured
if SECRET_PATH:
    @app.post(f"/{SECRET_PATH}")
    async def webhook(request: Request):
        """Handles incoming updates from Telegram by passing them to the bot."""
        try:
            data = await request.json()
            logger.debug(f"Received update: {data.get('update_id', 'unknown')}")
            update = Update.de_json(data=data, bot=bot_interface.application.bot)
            await bot_interface.application.process_update(update)
            logger.debug(f"Successfully processed update {update.update_id}")
        except Exception as e:
            logger.error(f"Error processing update: {e}", exc_info=True)
        return Response(status_code=200)
else:
    logger.warning("Webhook endpoint not created - TELEGRAM_BOT_TOKEN is not configured")

@app.get("/")
async def root():
    """Root endpoint to handle basic requests and reduce 404 noise in logs."""
    return {
        "service": "Paraphrase Engine",
        "status": "running",
        "version": "1.0"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for Render to ensure the service is live."""
    return {"status": "ok"}

