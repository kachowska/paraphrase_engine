#!/usr/bin/env python3
"""
Simple working version of the bot without complex dependencies
"""

import sys
from pathlib import Path
import logging
import asyncio

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

class SimpleBot:
    """Simple bot without complex dependencies"""
    
    def __init__(self):
        self.user_sessions = {}
        logger.info("Simple bot initialized")
    
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
    
    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle document upload"""
        try:
            chat_id = update.effective_chat.id
            
            if chat_id not in self.user_sessions:
                await update.message.reply_text(
                    "❌ Session expired. Please start again with /start"
                )
                return ConversationHandler.END
            
            document = update.message.document
            
            # Validate file format
            if not document.file_name.endswith('.docx'):
                await update.message.reply_text(
                    "❌ Error: Please upload a .docx file only."
                )
                return WAITING_FOR_FILE
            
            # Check file size
            file_size_mb = document.file_size / (1024 * 1024)
            if file_size_mb > 10:  # 10MB limit
                await update.message.reply_text(
                    "❌ Error: File size exceeds 10MB limit."
                )
                return WAITING_FOR_FILE
            
            # Download and save file
            await update.message.reply_text("📥 Downloading file...")
            
            file = await context.bot.get_file(document.file_id)
            
            # Create unique file path
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"{chat_id}_{timestamp}_{document.file_name}"
            file_path = Path("temp_files") / file_name
            
            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Download file
            await file.download_to_drive(str(file_path))
            
            # Store in session
            self.user_sessions[chat_id]["file_path"] = str(file_path)
            self.user_sessions[chat_id]["file_name"] = document.file_name
            
            await update.message.reply_text(
                f"✅ File `{document.file_name}` accepted.\n\n"
                "📋 *Step 2:* Now enter the text fragments to be rephrased.\n"
                "⚠️ *Important:* Each fragment must be on a new line.",
                parse_mode='Markdown'
            )
            
            return WAITING_FOR_FRAGMENTS
            
        except Exception as e:
            logger.error(f"Error handling document: {e}", exc_info=True)
            await update.message.reply_text(
                "❌ Error: Unable to process the document. Please try again."
            )
            return WAITING_FOR_FILE
    
    async def handle_fragments(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle text fragments input"""
        try:
            chat_id = update.effective_chat.id
            
            if chat_id not in self.user_sessions:
                await update.message.reply_text(
                    "❌ Session expired. Please start again with /start"
                )
                return ConversationHandler.END
            
            text = update.message.text
            
            # Parse fragments (split by newline)
            fragments = [f.strip() for f in text.split('\n') if f.strip()]
            
            if not fragments:
                await update.message.reply_text(
                    "❌ No fragments detected. Please enter text with each fragment on a new line."
                )
                return WAITING_FOR_FRAGMENTS
            
            # Store fragments
            self.user_sessions[chat_id]["fragments"] = fragments
            
            # Send confirmation
            estimated_time = max(5, len(fragments) * 2)  # Rough estimate
            await update.message.reply_text(
                f"✅ {len(fragments)} fragment(s) received.\n"
                f"⏳ Starting work. Estimated time: ~{estimated_time} minutes.\n"
                f"Please wait..."
            )
            
            # For now, just simulate processing
            await asyncio.sleep(2)  # Simulate processing time
            
            await update.message.reply_text(
                "✅ Processing complete!\n\n"
                "Note: This is a simplified version. The full paraphrasing functionality "
                "is available in the complete bot.\n\n"
                "To use the full version, please check the logs for any initialization errors."
            )
            
            return ConversationHandler.END
            
        except Exception as e:
            logger.error(f"Error handling fragments: {e}", exc_info=True)
            await update.message.reply_text(
                "❌ Error: Unable to process fragments. Please try again."
            )
            return WAITING_FOR_FRAGMENTS
    
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
                    MessageHandler(filters.Document.ALL, self.handle_document),
                ],
                WAITING_FOR_FRAGMENTS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_fragments)
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
    """Main entry point for the simple bot"""
    logger.info("Starting Simple Paraphrase Engine Bot...")
    
    try:
        bot = SimpleBot()
        bot.run()
    except Exception as e:
        logger.error(f"Failed to start bot: {e}", exc_info=True)

if __name__ == "__main__":
    main()
