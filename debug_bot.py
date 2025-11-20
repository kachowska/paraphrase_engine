#!/usr/bin/env python3
"""
Debug version of the bot to identify the error
"""

import sys
from pathlib import Path
import logging

# Ensure project root is on sys.path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from paraphrase_engine.config import settings

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    try:
        logger.info(f"Start command received from user {update.effective_user.id}")
        
        welcome_message = (
            "🎯 Welcome to Paraphrase Engine v1.0!\n\n"
            "I will help you professionally rewrite text fragments while preserving "
            "their academic style and meaning.\n\n"
            "📋 *Step 1:* Please upload your document in .docx format."
        )
        
        await update.message.reply_text(
            welcome_message,
            parse_mode='Markdown'
        )
        
        logger.info("Start command completed successfully")
        
    except Exception as e:
        logger.error(f"Error in start command: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ Error: {str(e)}\n\nPlease try again with /start"
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}", exc_info=True)
    
    if update and update.effective_chat:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ An unexpected error occurred. Please try again with /start"
            )
        except Exception as e:
            logger.error(f"Failed to send error message: {e}")

def main():
    """Main entry point for the debug bot"""
    logger.info("Starting debug bot...")
    
    # Create application
    application = Application.builder().token(settings.telegram_bot_token).build()
    
    # Add handlers
    application.add_handler(CommandHandler('start', start_command))
    application.add_error_handler(error_handler)
    
    # Run bot
    logger.info("Starting Telegram bot polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
