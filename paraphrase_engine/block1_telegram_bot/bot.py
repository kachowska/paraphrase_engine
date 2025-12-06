"""
Block 1: Telegram Bot Interface
The only point of entry for the end user
"""

import os
import asyncio
from pathlib import Path
from typing import Dict, List, Optional
from telegram import Update, Document, Bot, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
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
from ..block4_document import PDFReportExtractor, PlagiarismFragment

# Configure logging
logger = logging.getLogger(__name__)

# Conversation states
WAITING_FOR_FILE, WAITING_FOR_FRAGMENT, ASKING_MORE, WAITING_FOR_REPORT_PDF, WAITING_FOR_SOURCE_DOCX = range(5)


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
        
        # Create report processing conversation handler
        report_conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler('process_report', self.process_report_command)
            ],
            states={
                WAITING_FOR_REPORT_PDF: [
                    MessageHandler(filters.Document.ALL, self.handle_report_pdf),
                ],
                WAITING_FOR_SOURCE_DOCX: [
                    MessageHandler(filters.Document.ALL, self.handle_source_docx),
                ],
            },
            fallbacks=[CommandHandler('cancel', self.cancel_command)],
        )
        
        # Add handlers (report handler first to catch /process_report)
        self.application.add_handler(report_conv_handler)
        self.application.add_handler(conv_handler)
        self.application.add_error_handler(self.error_handler)
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle /start command"""
        if not update.message or not update.effective_chat or not update.effective_user:
            return ConversationHandler.END
        
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
    
    async def continue_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle /continue command - continue working with existing document"""
        if not update.message or not update.effective_chat or not update.effective_user:
            return ConversationHandler.END
        
        chat_id = update.effective_chat.id
        user_name = update.effective_user.username or "User"
        
        # Check if there's an existing document
        existing_doc = await self.task_manager.load_existing_document(chat_id)
        
        if not existing_doc:
            await update.message.reply_text(
                "❌ Не найдено сохраненного документа для продолжения работы.\n\n"
                "💡 Используйте /start для начала новой работы с документом."
            )
            return ConversationHandler.END
        
        # Initialize session for continuing
        self.user_sessions[chat_id] = {
            "chat_id": chat_id,
            "user_name": user_name,
            "start_time": datetime.now(),
            "file_path": existing_doc.current_file_path,
            "fragments": [],
            "existing_document": existing_doc,
            "is_continuation": True
        }
        
        await update.message.reply_text(
            f"✅ Найден сохраненный документ (версия {existing_doc.version}).\n\n"
            f"📄 Оригинальный файл: {Path(existing_doc.original_file_path).name}\n"
            f"📝 Обработано фрагментов: {len(existing_doc.fragments)}\n"
            f"🕒 Обновлен: {existing_doc.updated_at.strftime('%Y-%m-%d %H:%M')}\n\n"
            "📋 Введите новые фрагменты текста для перефразирования:"
        )
        
        return WAITING_FOR_FRAGMENT
    
    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle document upload"""
        if not update.message or not update.effective_chat:
            return ConversationHandler.END
        
        chat_id = update.effective_chat.id
        
        if chat_id not in self.user_sessions:
            await update.message.reply_text(
                "❌ Session expired. Please start again with /start"
            )
            return ConversationHandler.END
        
        if not update.message.document:
            await update.message.reply_text(
                "❌ No document found in message"
            )
            return ConversationHandler.END
        
        document: Document = update.message.document
        
        # Validate file format
        if not document.file_name or not document.file_name.endswith('.docx'):
            await update.message.reply_text(
                "❌ Error: Please upload a .docx file only."
            )
            return WAITING_FOR_FILE
        
        # Check file size
        if document.file_size is None:
            await update.message.reply_text(
                "❌ Error: Could not determine file size."
            )
            return WAITING_FOR_FILE
        
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
        if not update.message or not update.effective_chat:
            return ConversationHandler.END
        
        chat_id = update.effective_chat.id
        
        if chat_id not in self.user_sessions:
            await update.message.reply_text(
                "❌ Сессия истекла. Пожалуйста, начните заново с /start"
            )
            return ConversationHandler.END
        
        if not update.message.text:
            await update.message.reply_text(
                "❌ Error: No text found in message."
            )
            return WAITING_FOR_FRAGMENT
        
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
        if not update.effective_chat:
            return ConversationHandler.END
        
        chat_id = update.effective_chat.id
        
        if chat_id not in self.user_sessions:
            if update.message:
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
            if not update.message or not update.message.text:
                return ASKING_MORE
            
            text = update.message.text.strip().lower()
            if text in ['да', 'yes', 'y', 'д', '+', '1']:
                choice = "more_yes"
            elif text in ['нет', 'no', 'n', 'н', '-', '0']:
                choice = "more_no"
            else:
                if update.message:
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
        
        if not message:
            return ConversationHandler.END
        
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
                if message:
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
                if message:
                    await message.reply_text("❌ Ошибка: Задача не найдена. Пожалуйста, попробуйте снова.")
                return
            
            # Create progress callback for sending updates to user
            progress_messages = []  # Store sent messages to edit them
            
            # Get bot instance for sending messages
            bot_instance = context.bot if context and context.bot else None
            if not bot_instance:
                logger.error(f"Bot instance not available for chat {chat_id}")
            
            async def progress_callback(text: str):
                """Send or update progress message"""
                if not bot_instance:
                    logger.warning(f"Cannot send progress update: bot instance not available")
                    return
                    
                try:
                    logger.info(f"📊 Sending progress update to chat {chat_id}: {text[:80]}...")
                    if progress_messages:
                        # Edit last message
                        try:
                            await progress_messages[-1].edit_text(text, parse_mode='Markdown')
                            logger.debug(f"✅ Updated progress message for chat {chat_id}")
                        except Exception as edit_error:
                            # If edit fails (e.g., message too old), send new message
                            logger.warning(f"⚠️ Failed to edit message, sending new: {edit_error}")
                            try:
                                msg = await bot_instance.send_message(
                                    chat_id=chat_id,
                                    text=text,
                                    parse_mode='Markdown'
                                )
                                progress_messages.append(msg)
                                logger.info(f"✅ Sent new progress message to chat {chat_id}")
                            except Exception as send_error:
                                logger.error(f"❌ Failed to send new progress message: {send_error}")
                    else:
                        # Send first message
                        try:
                            msg = await bot_instance.send_message(
                                chat_id=chat_id,
                                text=text,
                                parse_mode='Markdown'
                            )
                            progress_messages.append(msg)
                            logger.info(f"✅ Sent initial progress message to chat {chat_id}")
                        except Exception as send_error:
                            logger.error(f"❌ Failed to send initial progress message: {send_error}")
                except Exception as e:
                    logger.error(f"❌ Failed to send progress update to chat {chat_id}: {e}", exc_info=True)
            
            # Process task (this will orchestrate blocks 3 and 4)
            result_file_path = await self.task_manager.process_task(task_id, progress_callback=progress_callback)
            
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
            error_str = str(e)
            logger.error(f"Error processing task for chat {chat_id}: {e}", exc_info=True)
            await self.system_logger.log_error(chat_id, "task_processing", str(e))
            
            # Check if it's a quota error
            from ..block3_paraphrasing.ai_providers import QuotaExceededError
            
            if isinstance(e, QuotaExceededError) or "quota" in error_str.lower() or "429" in error_str or "превышен лимит" in error_str.lower():
                # Check if we have partial progress
                task = self.task_manager.tasks.get(task_id)
                if not task:
                    task = await self.task_manager._load_task_from_disk(task_id)
                
                processed_count = 0
                if task and task.paraphrased_fragments:
                    processed_count = sum(1 for f in task.paraphrased_fragments if f and f.strip() and f != task.fragments[task.paraphrased_fragments.index(f) if f in task.paraphrased_fragments else 0])
                
                # Count actually processed (not just original text)
                if task and task.paraphrased_fragments:
                    processed_count = len([f for i, f in enumerate(task.paraphrased_fragments) 
                                          if f and f.strip() and (i >= len(task.fragments) or f != task.fragments[i])])
                
                total_count = len(fragments) if fragments else (len(task.fragments) if task else 0)
                
                if processed_count > 0:
                    error_message = (
                        f"⚠️ *Превышен лимит запросов к Gemini API*\n\n"
                        f"Обработка остановлена из-за превышения дневной квоты.\n\n"
                        f"📊 *Прогресс:* {processed_count}/{total_count} фрагментов обработано\n"
                        f"💾 Прогресс сохранен. Вы можете продолжить обработку позже.\n\n"
                        f"📋 *Что делать:*\n"
                        f"1. Проверьте квоту: https://ai.dev/usage?tab=rate-limit\n"
                        f"2. Подождите до следующего дня (лимит обновляется ежедневно)\n"
                        f"3. Или увеличьте лимит в Google Cloud Console\n\n"
                        f"💡 *Совет:* Попробуйте обработать документ завтра или разбейте его на меньшие части.\n\n"
                        f"🔄 Чтобы продолжить обработку, просто загрузите документ снова после восстановления квоты."
                    )
                else:
                    error_message = (
                        "⚠️ *Превышен лимит запросов к Gemini API*\n\n"
                        "К сожалению, достигнут дневной лимит запросов к Google Gemini API.\n\n"
                        "📊 *Что делать:*\n"
                        "1. Проверьте вашу квоту: https://ai.dev/usage?tab=rate-limit\n"
                        "2. Подождите до следующего дня (лимит обновляется ежедневно)\n"
                        "3. Или увеличьте лимит в настройках Google Cloud Console\n\n"
                        "💡 *Совет:* Попробуйте обработать документ позже или разбейте его на меньшие части."
                    )
            else:
                error_message = "❌ Произошла ошибка при обработке задачи.\n\n"
            
            # Provide more specific error messages
            error_str = str(e).lower()
            if "not found" in error_str or "не найден" in error_str:
                error_message += "⚠️ Один или несколько фрагментов не были найдены в документе.\n"
                error_message += "Проверьте, что текст фрагментов точно соответствует тексту в документе.\n\n"
            
            error_message += f"Детали ошибки: {str(e)[:200]}"
            
            if message:
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
        if not update.message or not update.effective_chat:
            return ConversationHandler.END
        
        chat_id = update.effective_chat.id
        
        await self.cleanup_session(chat_id)
        
        await update.message.reply_text(
            "❌ Operation cancelled. Use /start to begin again."
        )
        
        return ConversationHandler.END
    
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Update {update} caused error {context.error}")
        
        # Type guard для update
        if isinstance(update, Update) and update.effective_chat and context.bot:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="❌ An unexpected error occurred. Please try again with /start"
                )
    
    async def process_report_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle /process_report command - обработка PDF-отчетов Антиплагиата"""
        if not update.message or not update.effective_chat:
            return ConversationHandler.END
        
        chat_id = update.effective_chat.id
        
        # Initialize session for report processing
        self.user_sessions[chat_id] = {
            "chat_id": chat_id,
            "user_name": update.effective_user.username or "User" if update.effective_user else "User",
            "start_time": datetime.now(),
            "file_path": None,
            "fragments": [],
            "report_mode": True,
            "pdf_path": None,
            "extracted_fragments": []
        }
        
        await update.message.reply_text(
            "📊 Обработка PDF-отчетов Антиплагиата\n\n"
            "📄 Шаг 1: Загрузите PDF-отчет Антиплагиата.\n"
            "Бот автоматически извлечет выделенные фрагменты плагиата."
        )
        
        logger.info(f"/process_report command received from {chat_id}")
        return WAITING_FOR_REPORT_PDF
    
    async def handle_report_pdf(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle PDF report file upload"""
        if not update.message or not update.effective_chat:
            return ConversationHandler.END
        
        chat_id = update.effective_chat.id
        
        if chat_id not in self.user_sessions:
            await update.message.reply_text(
                "❌ Сессия истекла. Пожалуйста, начните заново с /process_report"
            )
            return ConversationHandler.END
        
        if not update.message.document:
            await update.message.reply_text(
                "❌ Не найден файл в сообщении."
            )
            return WAITING_FOR_REPORT_PDF
        
        document: Document = update.message.document
        
        # Validate file format
        if not document.file_name or not document.file_name.lower().endswith('.pdf'):
            await update.message.reply_text(
                "❌ Пожалуйста, загрузите PDF-файл (.pdf)"
            )
            return WAITING_FOR_REPORT_PDF
        
        # Check file size
        if document.file_size is None:
            await update.message.reply_text(
                "❌ Не удалось определить размер файла."
            )
            return WAITING_FOR_REPORT_PDF
        
        file_size_mb = document.file_size / (1024 * 1024)
        if file_size_mb > settings.max_file_size_mb:
            await update.message.reply_text(
                f"❌ Размер файла превышает {settings.max_file_size_mb}MB."
            )
            return WAITING_FOR_REPORT_PDF
        
        try:
            # Download PDF file
            file = await context.bot.get_file(document.file_id)
            temp_dir = Path(settings.temp_files_dir)
            temp_dir.mkdir(parents=True, exist_ok=True)
            pdf_path = temp_dir / f"report_{chat_id}_{document.file_id}.pdf"
            
            await file.download_to_drive(pdf_path)
            
            # Extract plagiarism fragments
            await update.message.reply_text(
                "⏳ Анализирую PDF-отчет и извлекаю фрагменты плагиата..."
            )
            
            extractor = PDFReportExtractor()
            fragments = extractor.extract_plagiarism_fragments(str(pdf_path))
            
            if not fragments:
                await update.message.reply_text(
                    "⚠️ В отчете не найдено выделенных фрагментов плагиата.\n"
                    "Убедитесь, что отчет содержит выделенные оранжевым/красным цветом фрагменты."
                )
                # Cleanup
                if pdf_path.exists():
                    pdf_path.unlink()
                return ConversationHandler.END
            
            # Store extracted fragments
            self.user_sessions[chat_id]["pdf_path"] = str(pdf_path)
            self.user_sessions[chat_id]["extracted_fragments"] = [f.text for f in fragments]
            
            await update.message.reply_text(
                f"✅ Найдено {len(fragments)} фрагмент(ов) плагиата.\n\n"
                "📄 Шаг 2: Загрузите исходный DOCX документ для замены фрагментов."
            )
            
            return WAITING_FOR_SOURCE_DOCX
            
        except Exception as e:
            logger.error(f"Error handling PDF report: {e}", exc_info=True)
            await self.system_logger.log_error(chat_id, "pdf_report_processing", str(e))
            await update.message.reply_text(
                "❌ Ошибка при обработке PDF-отчета. Пожалуйста, попробуйте снова."
            )
            return ConversationHandler.END
    
    async def handle_source_docx(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle source DOCX file for report processing"""
        if not update.message or not update.effective_chat:
            return ConversationHandler.END
        
        chat_id = update.effective_chat.id
        
        if chat_id not in self.user_sessions:
            await update.message.reply_text(
                "❌ Сессия истекла. Пожалуйста, начните заново с /process_report"
            )
            return ConversationHandler.END
        
        if not update.message.document:
            await update.message.reply_text(
                "❌ Не найден файл в сообщении."
            )
            return WAITING_FOR_SOURCE_DOCX
        
        document: Document = update.message.document
        
        # Validate file format
        if not document.file_name or not document.file_name.lower().endswith('.docx'):
            await update.message.reply_text(
                "❌ Пожалуйста, загрузите DOCX-файл (.docx)"
            )
            return WAITING_FOR_SOURCE_DOCX
        
        # Check file size
        if document.file_size is None:
            await update.message.reply_text(
                "❌ Не удалось определить размер файла."
            )
            return WAITING_FOR_SOURCE_DOCX
        
        file_size_mb = document.file_size / (1024 * 1024)
        if file_size_mb > settings.max_file_size_mb:
            await update.message.reply_text(
                f"❌ Размер файла превышает {settings.max_file_size_mb}MB."
            )
            return WAITING_FOR_SOURCE_DOCX
        
        try:
            # Download DOCX file
            file = await context.bot.get_file(document.file_id)
            temp_dir = Path(settings.temp_files_dir)
            temp_dir.mkdir(parents=True, exist_ok=True)
            docx_path = temp_dir / f"source_{chat_id}_{document.file_id}.docx"
            
            await file.download_to_drive(docx_path)
            
            # Store file path and extracted fragments
            self.user_sessions[chat_id]["file_path"] = str(docx_path)
            self.user_sessions[chat_id]["fragments"] = self.user_sessions[chat_id]["extracted_fragments"]
            
            await update.message.reply_text(
                f"✅ Документ принят. Найдено {len(self.user_sessions[chat_id]['fragments'])} фрагмент(ов) для обработки.\n"
                "⏳ Начинаю перефразирование и замену фрагментов...\n"
                "Это может занять некоторое время. Пожалуйста, подождите."
            )
            
            # Create task and process
            task_id = await self.task_manager.create_task(
                chat_id=chat_id,
                file_path=str(docx_path)
            )
            
            task = self.task_manager.tasks.get(task_id)
            if task:
                task.fragments = self.user_sessions[chat_id]["fragments"]
                task.metadata = {"report_mode": True, "pdf_path": self.user_sessions[chat_id].get("pdf_path")}
                await self.task_manager._save_task_to_disk(task)
            
            # Process task
            result_file_path = await self.task_manager.process_task(task_id)
            
            if result_file_path and os.path.exists(result_file_path):
                with open(result_file_path, 'rb') as f:
                    await context.bot.send_document(
                        chat_id=chat_id,
                        document=f,
                        caption=f"✅ Документ обработан!\n\n"
                               f"📊 Обработано фрагментов: {len(self.user_sessions[chat_id]['fragments'])}",
                        filename=f"paraphrased_{Path(result_file_path).name}"
                    )
                
                await self.cleanup_session(chat_id)
            else:
                await update.message.reply_text(
                    "❌ Ошибка при обработке документа. Пожалуйста, попробуйте снова."
                )
            
            return ConversationHandler.END
            
        except Exception as e:
            logger.error(f"Error handling source DOCX: {e}", exc_info=True)
            await self.system_logger.log_error(chat_id, "source_docx_processing", str(e))
            await update.message.reply_text(
                "❌ Ошибка при обработке документа. Пожалуйста, попробуйте снова."
            )
            return ConversationHandler.END
    
    async def _set_bot_commands(self):
        """Устанавливает команды бота для отображения в меню"""
        commands = [
            BotCommand("start", "Начать работу с ботом"),
            BotCommand("process_report", "Обработать PDF-отчет Антиплагиата"),
            BotCommand("cancel", "Отменить текущую операцию"),
        ]
        try:
            if self.application and self.application.bot:
                await self.application.bot.set_my_commands(commands)
            logger.info("✅ Команды бота установлены: /start, /process_report, /cancel")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось установить команды бота: {e}")
    
    def run(self):
        """Run the bot in polling mode"""
        # Handlers are already set up in __init__
        # Set bot commands using post_init callback
        async def post_init(app: Application) -> None:
            await self._set_bot_commands()
        
        # Run bot
        logger.info("Starting Telegram bot in polling mode...")
        # run_polling will automatically delete webhook if exists
        # drop_pending_updates=True ensures clean start
        if self.application:
            self.application.post_init = post_init
            self.application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )
        else:
            logger.error("Application is None, cannot start bot")
            raise RuntimeError("Application is not initialized")


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
