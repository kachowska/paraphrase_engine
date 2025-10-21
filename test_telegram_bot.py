#!/usr/bin/env python3
"""
Test Telegram bot initialization
"""

import sys
from pathlib import Path
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from paraphrase_engine.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
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
    """Test Telegram bot initialization"""
    logger.info("Testing Telegram bot initialization...")
    
    try:
        # Test creating application
        logger.info("Creating Telegram application...")
        application = Application.builder().token(settings.telegram_bot_token).build()
        logger.info("✅ Application created successfully")
        
        # Test adding handlers
        logger.info("Adding handlers...")
        application.add_handler(CommandHandler('start', start_command))
        application.add_error_handler(error_handler)
        logger.info("✅ Handlers added successfully")
        
        # Test starting polling (but don't actually start)
        logger.info("✅ All Telegram bot components initialized successfully!")
        logger.info("Bot is ready to start polling")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize Telegram bot: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 Telegram bot initialization test PASSED!")
        print("The bot should work correctly.")
    else:
        print("\n❌ Telegram bot initialization test FAILED!")
        print("There's an issue with the bot setup.")
