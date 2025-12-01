"""
Block 1: Telegram Bot Interface
The only point of entry for the end user
"""

import os
import asyncio
from pathlib import Path
from typing import Dict, List
from telegram import Update, Document, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
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
WAITING_FOR_FILE, WAITING_FOR_FRAGMENT, ASKING_MORE = range(3)


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
            entry_points=[
                CommandHandler('start', self.start_command),
                CommandHandler('continue', self.continue_command)
            ],
            states={
                WAITING_FOR_FILE: [
                    MessageHandler(filters.Document.ALL, self.handle_document),
                ],
                WAITING_FOR_FRAGMENT: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_fragment)
                ],
                ASKING_MORE: [
                    CallbackQueryHandler(self.handle_more_choice, pattern='^more_'),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_more_choice)
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
                f"✅ Файл `{document.file_name}` принят.\n\n"
                "📋 *Шаг 2:* Введите фрагмент текста для перефразирования.\n"
                "💡 Вы можете вводить фрагменты по одному, они могут быть из разных частей документа.",
                parse_mode='Markdown'
            )
            
            return WAITING_FOR_FRAGMENT
            
        except Exception as e:
            logger.error(f"Error handling document: {e}")
            await self.system_logger.log_error(chat_id, "document_upload", str(e))
            
            await update.message.reply_text(
                "❌ Error: Unable to process the document. Please try again."
            )
            return WAITING_FOR_FILE
    
    async def handle_fragment(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle single fragment input"""
        chat_id = update.effective_chat.id
        
        if chat_id not in self.user_sessions:
            await update.message.reply_text(
                "❌ Сессия истекла. Пожалуйста, начните заново с /start"
            )
            return ConversationHandler.END
        
        text = update.message.text.strip()
        
        if not text:
            await update.message.reply_text(
                "❌ Пустой фрагмент. Пожалуйста, введите текст для перефразирования."
            )
            return WAITING_FOR_FRAGMENT
        
        # Parse fragment: if there are double newlines, split into separate fragments
        # Otherwise, treat as one fragment (join lines with spaces)
        if '\n\n' in text:
            # Split by double newlines (paragraph separator)
            raw_fragments = text.split('\n\n')
            fragments = []
            for frag in raw_fragments:
                frag = frag.strip()
                if frag:
                    # Join lines within paragraph with spaces
                    lines = [line.strip() for line in frag.split('\n') if line.strip()]
                    if lines:
                        fragments.append(' '.join(lines))
            
            # If we got multiple fragments, add them all
            if len(fragments) > 1:
                if "fragments" not in self.user_sessions[chat_id]:
                    self.user_sessions[chat_id]["fragments"] = []
                
                for frag in fragments:
                    self.user_sessions[chat_id]["fragments"].append(frag)
                
                total_fragments = len(self.user_sessions[chat_id]["fragments"])
                await update.message.reply_text(
                    f"✅ Принято {len(fragments)} фрагмент(ов).\n"
                    f"📝 Всего фрагментов: {total_fragments}"
                )
                
                # Ask if user wants to add more
                keyboard = [
                    [
                        InlineKeyboardButton("✅ Да", callback_data="more_yes"),
                        InlineKeyboardButton("❌ Нет", callback_data="more_no")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    "❓ Хотите еще добавить текст для перефразирования?",
                    reply_markup=reply_markup
                )
                
                return ASKING_MORE
            
            # If only one fragment after splitting, continue with normal flow
            fragment = fragments[0] if fragments else None
        else:
            # No double newlines - treat as one fragment
            fragment = ' '.join([line.strip() for line in text.split('\n') if line.strip()])
        
        if not fragment:
            await update.message.reply_text(
                "❌ Не удалось извлечь текст. Пожалуйста, введите фрагмент еще раз."
            )
            return WAITING_FOR_FRAGMENT
        
        # Add fragment to session
        if "fragments" not in self.user_sessions[chat_id]:
            self.user_sessions[chat_id]["fragments"] = []
        
        self.user_sessions[chat_id]["fragments"].append(fragment)
        total_fragments = len(self.user_sessions[chat_id]["fragments"])
        
        # Confirm fragment received
        await update.message.reply_text(
            f"✅ Фрагмент {total_fragments} принят.\n"
            f"📝 Всего фрагментов: {total_fragments}"
        )
        
        # Ask if user wants to add more
        keyboard = [
            [
                InlineKeyboardButton("✅ Да", callback_data="more_yes"),
                InlineKeyboardButton("❌ Нет", callback_data="more_no")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "❓ Хотите еще добавить текст для перефразирования?",
            reply_markup=reply_markup
        )
        
        return ASKING_MORE
    
    async def handle_more_choice(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle user's choice to add more fragments or process"""
        chat_id = update.effective_chat.id
        
        if chat_id not in self.user_sessions:
            await update.message.reply_text(
                "❌ Сессия истекла. Пожалуйста, начните заново с /start"
            )
            return ConversationHandler.END
        
        # Handle both callback queries (buttons) and text messages
        if update.callback_query:
            query = update.callback_query
            try:
                await query.answer()
            except Exception as e:
                # Handle expired callback queries gracefully
                logger.warning(f"Callback query expired or invalid: {e}")
                # Continue processing anyway
            choice = query.data
            message = query.message
        else:
            # Handle text response
            text = update.message.text.strip().lower()
            if text in ['да', 'yes', 'y', 'д', '+', '1']:
                choice = "more_yes"
            elif text in ['нет', 'no', 'n', 'н', '-', '0']:
                choice = "more_no"
            else:
                await update.message.reply_text(
                    "❓ Пожалуйста, ответьте «да» или «нет».\n"
                    "Или используйте кнопки ниже.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("✅ Да", callback_data="more_yes"),
                        InlineKeyboardButton("❌ Нет", callback_data="more_no")
                    ]])
                )
                return ASKING_MORE
            message = update.message
        
        if choice == "more_yes":
            # User wants to add more fragments
            await message.reply_text(
                "📝 Введите следующий фрагмент текста для перефразирования:"
            )
            return WAITING_FOR_FRAGMENT
        
        elif choice == "more_no":
            # User is done, process all fragments
            fragments = self.user_sessions[chat_id].get("fragments", [])
            
            if not fragments:
                await message.reply_text(
                    "❌ Не найдено фрагментов для обработки. Пожалуйста, начните заново с /start"
                )
                return ConversationHandler.END
            
            # Check if this is a continuation of existing document
            session = self.user_sessions[chat_id]
            is_continuation = session.get("is_continuation", False)
            
            if is_continuation:
                # Continue with existing document
                await message.reply_text(
                    f"✅ Принято {len(fragments)} новый(ых) фрагмент(ов). Обновляю документ...\n"
                    f"⏳ Это может занять некоторое время. Пожалуйста, подождите."
                )
                
                result_file_path = await self.task_manager.continue_with_existing_document(
                    chat_id=chat_id,
                    new_fragments=fragments
                )
                
                if result_file_path and os.path.exists(result_file_path):
                    existing_doc = session.get("existing_document")
                    version = existing_doc.version + 1 if existing_doc else 1
                    
                    with open(result_file_path, 'rb') as f:
                        await context.bot.send_document(
                            chat_id=chat_id,
                            document=f,
                            caption=f"✅ Документ обновлен (версия {version})!\n\n"
                                   f"📊 Всего обработано фрагментов: {len(existing_doc.fragments) + len(fragments) if existing_doc else len(fragments)}",
                            filename=f"updated_{Path(result_file_path).name}"
                        )
                    
                    await self.cleanup_session(chat_id)
                else:
                    await message.reply_text(
                        "❌ Ошибка при обновлении документа. Пожалуйста, попробуйте снова."
                    )
            else:
                # New document processing
                await message.reply_text(
                    f"✅ Принято {len(fragments)} фрагмент(ов). Начинаю обработку...\n"
                    f"⏳ Это может занять некоторое время. Пожалуйста, подождите."
                )
                
                # Process all fragments
                await self.process_task(update, context, chat_id)
            
            return ConversationHandler.END
        
        return ASKING_MORE
    
    async def process_task(self, update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
        """Process the paraphrasing task"""
        session = self.user_sessions.get(chat_id)
        if not session:
            return
        
        # Get message object for sending replies
        if update.callback_query:
            message = update.callback_query.message
        elif update.message:
            message = update.message
        else:
            logger.error(f"No message object available for chat {chat_id}")
            return
        
        try:
            fragments = session.get("fragments", [])
            if not fragments:
                await message.reply_text(
                    "❌ Не найдено фрагментов для обработки."
                )
                return
            
            # Create task in task manager (without fragments - they are added iteratively)
            task_id = await self.task_manager.create_task(
                chat_id=chat_id,
                file_path=session["file_path"]
            )
            
            # Add fragments to the task before processing
            task = self.task_manager.tasks.get(task_id)
            if task:
                task.fragments = fragments
                # Save updated task to disk
                await self.task_manager._save_task_to_disk(task)
                logger.info(f"Added {len(fragments)} fragments to task {task_id}")
            else:
                logger.error(f"Task {task_id} not found after creation")
                await message.reply_text("❌ Ошибка: Задача не найдена. Пожалуйста, попробуйте снова.")
                return
            
            # Process task (this will orchestrate blocks 3 and 4)
            result_file_path = await self.task_manager.process_task(task_id)
            
            # Check if processing was successful
            if not result_file_path or not os.path.exists(result_file_path):
                raise Exception("Файл результата не найден")
            
            # Get task to check for any issues
            task = self.task_manager.tasks.get(task_id)
            if not task:
                # Try to load from disk
                task = await self.task_manager._load_task_from_disk(task_id)
            
            # Prepare result message
            result_message = "✅ Документ обработан успешно!\n\n"
            
            # Check if all fragments were processed
            if task and len(task.paraphrased_fragments) < len(fragments):
                missing_count = len(fragments) - len(task.paraphrased_fragments)
                result_message += f"⚠️ Внимание: {missing_count} фрагмент(ов) не было найдено в документе.\n\n"
            
            result_message += f"📊 Обработано фрагментов: {len(task.paraphrased_fragments) if task else len(fragments)}/{len(fragments)}\n\n"
            result_message += "📄 Перефразированные фрагменты:\n\n"
            
            # Add paraphrased fragments to message
            if task and task.paraphrased_fragments:
                for i, (original, paraphrased) in enumerate(zip(
                    task.fragments,
                    task.paraphrased_fragments
                ), 1):
                    result_message += f"*Фрагмент {i}:*\n"
                    result_message += f"📝 Оригинал: {original[:100]}{'...' if len(original) > 100 else ''}\n"
                    result_message += f"✨ Перефразировано: {paraphrased[:100]}{'...' if len(paraphrased) > 100 else ''}\n\n"
            
            # Send result document
            with open(result_file_path, 'rb') as f:
                await context.bot.send_document(
                    chat_id=chat_id,
                    document=f,
                    caption=result_message,
                    filename=f"processed_{session.get('file_name', 'document.docx')}",
                    parse_mode='Markdown'
                )
            
            # Log success
            await self.system_logger.log_task_completed(
                chat_id, 
                task_id,
                len(fragments)
            )
            
            # Cleanup session
            await self.cleanup_session(chat_id)
                
        except Exception as e:
            logger.error(f"Error processing task for chat {chat_id}: {e}", exc_info=True)
            await self.system_logger.log_error(chat_id, "task_processing", str(e))
            
            error_message = "❌ Произошла ошибка при обработке задачи.\n\n"
            
            # Provide more specific error messages
            error_str = str(e).lower()
            if "not found" in error_str or "не найден" in error_str:
                error_message += "⚠️ Один или несколько фрагментов не были найдены в документе.\n"
                error_message += "Проверьте, что текст фрагментов точно соответствует тексту в документе.\n\n"
            
            error_message += f"Детали ошибки: {str(e)[:200]}"
            
            await message.reply_text(error_message)
            
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
