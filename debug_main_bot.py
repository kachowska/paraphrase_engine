#!/usr/bin/env python3
"""
Debug version of the main bot to identify initialization issues
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

class DebugBot:
    """Debug version of TelegramBotInterface"""
    
    def __init__(self):
        logger.info("Initializing DebugBot...")
        
        try:
            logger.info("Step 1: Initializing basic attributes...")
            self.application = None
            self.user_sessions = {}
            logger.info("✅ Basic attributes initialized")
            
            logger.info("Step 2: Testing SystemLogger import...")
            from paraphrase_engine.block5_logging.logger import SystemLogger
            logger.info("✅ SystemLogger imported")
            
            logger.info("Step 3: Initializing SystemLogger...")
            self.system_logger = SystemLogger()
            logger.info("✅ SystemLogger initialized")
            
            logger.info("Step 4: Testing TaskManager import...")
            from paraphrase_engine.block2_orchestrator.task_manager import TaskManager
            logger.info("✅ TaskManager imported")
            
            logger.info("Step 5: Initializing TaskManager...")
            self.task_manager = TaskManager()
            logger.info("✅ TaskManager initialized")
            
            logger.info("🎉 DebugBot initialization completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ DebugBot initialization failed: {e}", exc_info=True)
            raise
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle /start command"""
        try:
            chat_id = update.effective_chat.id
            user_name = update.effective_user.username or "User"
            
            logger.info(f"Start command from user {user_name} (ID: {chat_id})")
            
            # Initialize session
            self.user_sessions[chat_id] = {
                "chat_id": chat_id,
                "user_name": user_name,
                "file_path": None,
                "fragments": []
            }
            
            # Log new session
            await self.system_logger.log_task_start(chat_id, user_name)
            
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
            
            logger.info(f"Start command completed for user {chat_id}")
            return WAITING_FOR_FILE
            
        except Exception as e:
            logger.error(f"Error in start command: {e}", exc_info=True)
            await update.message.reply_text(
                f"❌ Error: {str(e)}\n\nPlease try again with /start"
            )
            return ConversationHandler.END
    
    async def cancel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle /cancel command"""
        chat_id = update.effective_chat.id
        
        if chat_id in self.user_sessions:
            del self.user_sessions[chat_id]
        
        await update.message.reply_text(
            "❌ Operation cancelled. Use /start to begin again."
        )
        
        return ConversationHandler.END
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Update {update} caused error {context.error}", exc_info=True)
        
        if update and update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ An unexpected error occurred. Please try again with /start"
            )
    
    def run(self):
        """Run the bot"""
        logger.info("Creating Telegram application...")
        
        # Create application
        self.application = Application.builder().token(settings.telegram_bot_token).build()
        
        # Create conversation handler
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self.start_command)],
            states={
                WAITING_FOR_FILE: [
                    MessageHandler(filters.Document.ALL, lambda u, c: ConversationHandler.END),
                ],
                WAITING_FOR_FRAGMENTS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u, c: ConversationHandler.END)
                ],
            },
            fallbacks=[CommandHandler('cancel', self.cancel_command)],
        )
        
        # Add handlers
        self.application.add_handler(conv_handler)
        self.application.add_error_handler(self.error_handler)
        
        # Run bot
        logger.info("Starting Telegram bot polling...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

def main():
    """Main entry point for the debug bot"""
    logger.info("Starting Debug Paraphrase Engine Bot...")
    
    try:
        bot = DebugBot()
        bot.run()
    except Exception as e:
        logger.error(f"Failed to start debug bot: {e}", exc_info=True)

if __name__ == "__main__":
    main()
