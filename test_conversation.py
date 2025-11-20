#!/usr/bin/env python3
"""
Test conversation handler initialization
"""

import sys
from pathlib import Path
import logging

# Ensure project root is on sys.path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from paraphrase_engine.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Conversation states
WAITING_FOR_FILE, WAITING_FOR_FRAGMENTS = range(2)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
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
        return WAITING_FOR_FILE
        
    except Exception as e:
        logger.error(f"Error in start command: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ Error: {str(e)}\n\nPlease try again with /start"
        )
        return ConversationHandler.END

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /cancel command"""
    await update.message.reply_text(
        "❌ Operation cancelled. Use /start to begin again."
    )
    return ConversationHandler.END

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
    """Test conversation handler initialization"""
    logger.info("Testing conversation handler initialization...")
    
    try:
        # Test creating application
        logger.info("Creating Telegram application...")
        application = Application.builder().token(settings.telegram_bot_token).build()
        logger.info("✅ Application created successfully")
        
        # Test creating conversation handler
        logger.info("Creating conversation handler...")
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', start_command)],
            states={
                WAITING_FOR_FILE: [
                    MessageHandler(filters.Document.ALL, lambda u, c: ConversationHandler.END),
                ],
                WAITING_FOR_FRAGMENTS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u, c: ConversationHandler.END)
                ],
            },
            fallbacks=[CommandHandler('cancel', cancel_command)],
        )
        logger.info("✅ Conversation handler created successfully")
        
        # Test adding handlers
        logger.info("Adding handlers...")
        application.add_handler(conv_handler)
        application.add_error_handler(error_handler)
        logger.info("✅ Handlers added successfully")
        
        logger.info("✅ All conversation handler components initialized successfully!")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize conversation handler: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 Conversation handler initialization test PASSED!")
        print("The conversation handler should work correctly.")
    else:
        print("\n❌ Conversation handler initialization test FAILED!")
        print("There's an issue with the conversation handler setup.")
