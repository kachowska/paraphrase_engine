"""
Block 1: Telegram Bot Interface
The only point of entry for the end user
"""

import os
import asyncio
from pathlib import Path
from typing import Dict, List
from telegram import Update, Document, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler
)
import logging
from datetime import datetime

from ..config import settings
from ..block2_orchestrator.task_manager import TaskManager
from ..block5_logging.logger import SystemLogger

# Configure logging
logger = logging.getLogger(__name__)

# Conversation states
WAITING_FOR_FILE, WAITING_FOR_FRAGMENTS = range(2)


class TelegramBotInterface:
    """Main Telegram bot interface for user interaction"""
    
    def __init__(self):
        self.application = None
        self.task_manager = TaskManager()
        self.system_logger = SystemLogger()
        self.user_sessions: Dict[int, dict] = {}
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup bot handlers - can be called before or after application creation"""
        # Create application if not exists
        if self.application is None:
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
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle /start command"""
        chat_id = update.effective_chat.id
        user_name = update.effective_user.username or "User"
        
        # Initialize session
        self.user_sessions[chat_id] = {
            "chat_id": chat_id,
            "user_name": user_name,
            "start_time": datetime.now(),
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
        
        return WAITING_FOR_FILE
    
    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle document upload"""
        chat_id = update.effective_chat.id
        
        if chat_id not in self.user_sessions:
            await update.message.reply_text(
                "❌ Session expired. Please start again with /start"
            )
            return ConversationHandler.END
        
        document: Document = update.message.document
        
        # Validate file format
        if not document.file_name.endswith('.docx'):
            await update.message.reply_text(
                "❌ Error: Please upload a .docx file only."
            )
            return WAITING_FOR_FILE
        
        # Check file size
        file_size_mb = document.file_size / (1024 * 1024)
        if file_size_mb > settings.max_file_size_mb:
            await update.message.reply_text(
                f"❌ Error: File size exceeds {settings.max_file_size_mb}MB limit."
            )
            return WAITING_FOR_FILE
        
        try:
            # Download and save file
            await update.message.reply_text("📥 Downloading file...")
            
            file = await context.bot.get_file(document.file_id)
            
            # Create unique file path
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"{chat_id}_{timestamp}_{document.file_name}"
            file_path = Path(settings.temp_files_dir) / file_name
            
            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Download file
            await file.download_to_drive(str(file_path))
            
            # Store in session
            self.user_sessions[chat_id]["file_path"] = str(file_path)
            self.user_sessions[chat_id]["file_name"] = document.file_name
            
            # Log file reception
            await self.system_logger.log_file_received(
                chat_id, 
                document.file_name, 
                file_size_mb
            )
            
            await update.message.reply_text(
                f"✅ File `{document.file_name}` accepted.\n\n"
                "📋 *Step 2:* Now enter the text fragments to be rephrased.\n"
                "⚠️ *Important:* Each fragment must be on a new line.",
                parse_mode='Markdown'
            )
            
            return WAITING_FOR_FRAGMENTS
            
        except Exception as e:
            logger.error(f"Error handling document: {e}")
            await self.system_logger.log_error(chat_id, "document_upload", str(e))
            
            await update.message.reply_text(
                "❌ Error: Unable to process the document. Please try again."
            )
            return WAITING_FOR_FILE
    
    async def handle_fragments(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle text fragments input"""
        chat_id = update.effective_chat.id
        
        if chat_id not in self.user_sessions:
            await update.message.reply_text(
                "❌ Session expired. Please start again with /start"
            )
            return ConversationHandler.END
        
        text = update.message.text
        
        # Parse fragments intelligently:
        # 1. If there are double newlines (empty lines), split by them (each paragraph = one fragment)
        #    - Each paragraph's internal line breaks are joined with spaces
        # 2. If no double newlines, treat each non-empty line as a separate fragment
        #    - This respects the user's explicit line breaks as fragment boundaries
        
        if '\n\n' in text:
            # Split by double newlines (paragraph separator)
            raw_fragments = text.split('\n\n')
            fragments = []
            for frag in raw_fragments:
                frag = frag.strip()
                if frag:
                    # Join lines within paragraph with spaces (remove line breaks)
                    lines = [line.strip() for line in frag.split('\n') if line.strip()]
                    if lines:
                        # Join all lines of the paragraph into one fragment
                        fragments.append(' '.join(lines))
        else:
            # No double newlines - treat each non-empty line as a separate fragment
            # This respects user intent: if they put text on separate lines, they likely want separate fragments
            fragments = [line.strip() for line in text.split('\n') if line.strip()]
        
        if not fragments:
            await update.message.reply_text(
                "❌ Не найдено фрагментов. Пожалуйста, введите текст.\n\n"
                "💡 *Совет:* Разделяйте абзацы пустой строкой для лучшей обработки.",
                parse_mode='Markdown'
            )
            return WAITING_FOR_FRAGMENTS
        
        # Store fragments
        self.user_sessions[chat_id]["fragments"] = fragments
        
        # Log fragments received
        await self.system_logger.log_fragments_received(chat_id, len(fragments))
        
        # Send confirmation
        estimated_time = max(5, len(fragments) * 2)  # Rough estimate
        await update.message.reply_text(
            f"✅ {len(fragments)} fragment(s) received.\n"
            f"⏳ Starting work. Estimated time: ~{estimated_time} minutes.\n"
            f"Please wait..."
        )
        
        # Start processing
        await self.process_task(update, context, chat_id)
        
        return ConversationHandler.END
    
    async def process_task(self, update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
        """Process the paraphrasing task"""
        session = self.user_sessions.get(chat_id)
        if not session:
            return
        
        try:
            # Create task in task manager (without fragments - they are added iteratively)
            task_id = await self.task_manager.create_task(
                chat_id=chat_id,
                file_path=session["file_path"]
            )
            
            # Add fragments to the task before processing
            # Get the task and add fragments from session
            task = self.task_manager.tasks.get(task_id)
            if task and session.get("fragments"):
                task.fragments = session["fragments"]
                # Save updated task to disk
                await self.task_manager._save_task_to_disk(task)
            
            # Process task (this will orchestrate blocks 3 and 4)
            result_file_path = await self.task_manager.process_task(task_id)
            
            # Send result to user
            if result_file_path and os.path.exists(result_file_path):
                with open(result_file_path, 'rb') as f:
                    await context.bot.send_document(
                        chat_id=chat_id,
                        document=f,
                        caption="✅ Done. Your document has been processed.",
                        filename=f"processed_{session.get('file_name', 'document.docx')}"
                    )
                
                # Log success
                await self.system_logger.log_task_completed(
                    chat_id, 
                    task_id,
                    len(session["fragments"])
                )
                
                # Cleanup session
                await self.cleanup_session(chat_id)
            else:
                raise Exception("Result file not found")
                
        except Exception as e:
            logger.error(f"Error processing task for chat {chat_id}: {e}")
            await self.system_logger.log_error(chat_id, "task_processing", str(e))
            
            await update.message.reply_text(
                "❌ An internal error has occurred. Please try again later.\n"
                f"Error: {str(e)[:100]}"
            )
            
            # Cleanup session on error
            await self.cleanup_session(chat_id)
    
    async def cleanup_session(self, chat_id: int):
        """Clean up user session and temporary files"""
        if chat_id in self.user_sessions:
            session = self.user_sessions[chat_id]
            
            # Schedule file deletion (after retention period)
            # In production, this would be handled by a background task
            if session.get("file_path"):
                # For now, just log that cleanup is needed
                logger.info(f"Scheduled cleanup for {session['file_path']}")
            
            # Remove session
            del self.user_sessions[chat_id]
    
    async def cancel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle /cancel command"""
        chat_id = update.effective_chat.id
        
        await self.cleanup_session(chat_id)
        
        await update.message.reply_text(
            "❌ Operation cancelled. Use /start to begin again."
        )
        
        return ConversationHandler.END
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Update {update} caused error {context.error}")
        
        if update and update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ An unexpected error occurred. Please try again with /start"
            )
    
    def run(self):
        """Run the bot in polling mode"""
        # Handlers are already set up in __init__
        # Run bot
        logger.info("Starting Telegram bot in polling mode...")
        # run_polling will automatically delete webhook if exists
        # drop_pending_updates=True ensures clean start
        self.application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )


def main():
    """Main entry point for the bot"""
    bot = TelegramBotInterface()
    bot.run()


if __name__ == "__main__":
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=getattr(logging, settings.log_level)
    )
    main()
