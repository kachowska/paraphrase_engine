"""
Block 2: Task Management Core (Backend Orchestrator)
Manages the lifecycle of each task from the user
"""

import os
import json
import uuid
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any
from enum import Enum
import logging

from ..config import settings
from ..block3_paraphrasing.agent_core import ParaphrasingAgent
from ..block4_document.document_builder import DocumentBuilder
from ..block5_logging.logger import SystemLogger
from ..block6_database.database import DatabaseManager, ParaphrasedDocument

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task status enumeration"""
    CREATED = "created"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task:
    """Represents a paraphrasing task"""
    
    def __init__(self, task_id: str, chat_id: int, file_path: str, fragments: List[str] = None):
        self.task_id = task_id
        self.chat_id = chat_id
        self.file_path = file_path
        self.fragments = fragments if fragments is not None else []
        self.paraphrased_fragments: List[str] = []
        self.status = TaskStatus.CREATED
        self.created_at = datetime.now()
        self.completed_at: Optional[datetime] = None
        self.result_file_path: Optional[str] = None
        self.error_message: Optional[str] = None
        self.metadata: Dict[str, Any] = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary"""
        return {
            "task_id": self.task_id,
            "chat_id": self.chat_id,
            "file_path": self.file_path,
            "fragments": self.fragments,
            "paraphrased_fragments": self.paraphrased_fragments,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result_file_path": self.result_file_path,
            "error_message": self.error_message,
            "metadata": self.metadata
        }


class TaskManager:
    """Orchestrates the paraphrasing process"""
    
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.paraphrasing_agent = ParaphrasingAgent()
        self.document_builder = DocumentBuilder()
        self.system_logger = SystemLogger()
        self.database_manager = DatabaseManager()
        self.task_semaphore = asyncio.Semaphore(settings.max_parallel_tasks)
        self.fragment_semaphore = asyncio.Semaphore(settings.max_parallel_fragments)
        
        # Ensure tasks directory exists
        self.tasks_dir = Path(settings.temp_files_dir) / "tasks"
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
    
    async def create_task(self, chat_id: int, file_path: str) -> str:
        """Create a new task without fragments (fragments are added iteratively)"""
        task_id = str(uuid.uuid4())
        
        # Create task object without fragments (they will be added later)
        task = Task(
            task_id=task_id,
            chat_id=chat_id,
            file_path=file_path,
            fragments=[]  # Start with empty fragments list
        )
        
        # Store task
        self.tasks[task_id] = task
        
        # Save task to disk for persistence
        await self._save_task_to_disk(task)
        
        # Log task creation
        await self.system_logger.log_task_created(
            task_id=task_id,
            chat_id=chat_id,
            num_fragments=0  # No fragments yet
        )
        
        logger.info(f"Created task {task_id} for chat {chat_id} (fragments will be added iteratively)")
        
        return task_id
    
    async def process_task(self, task_id: str, progress_callback=None) -> Optional[str]:
        """
        Process a task through the entire pipeline
        Returns the path to the result file if successful, None otherwise
        """
        task = self.tasks.get(task_id)
        if not task:
            logger.error(f"Task {task_id} not found")
            return None
        
        async with self.task_semaphore:
            try:
                # Update task status
                task.status = TaskStatus.PROCESSING
                await self._save_task_to_disk(task)
                
                logger.info(f"Starting processing for task {task_id}")
                
                # Send initial progress message
                if progress_callback:
                    logger.info(f"Calling progress_callback for initial message (task {task_id})")
                    try:
                        await progress_callback(
                            f"🚀 *Начало обработки*\n\n"
                            f"📊 Всего фрагментов: {len(task.fragments)}\n"
                            f"⏳ Начинаю перефразирование..."
                        )
                    except Exception as e:
                        logger.error(f"Error calling progress_callback: {e}", exc_info=True)
                else:
                    logger.warning(f"No progress_callback provided for task {task_id}")
                
                # Step 1: Process each fragment through the paraphrasing agent
                paraphrased_fragments = await self._process_fragments(task, progress_callback)
                task.paraphrased_fragments = paraphrased_fragments
                
                # Send progress after paraphrasing
                if progress_callback:
                    try:
                        await progress_callback(
                            f"✅ *Перефразирование завершено*\n\n"
                            f"📝 Обработано: {len(paraphrased_fragments)}/{len(task.fragments)} фрагментов\n"
                            f"📄 Начинаю замену текста в документе..."
                        )
                    except Exception as e:
                        logger.error(f"Error calling progress_callback after paraphrasing: {e}", exc_info=True)
                
                # Step 2: Build the new document with replacements
                result_file_path = await self._build_document(task, progress_callback)
                
                # Update task with results
                task.result_file_path = result_file_path
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.now()
                
                # Save final task state
                await self._save_task_to_disk(task)
                
                # Save to database for future reference
                await self._save_document_to_db(task, result_file_path)
                
                # Log completion
                await self.system_logger.log_task_completed(
                    chat_id=task.chat_id,
                    task_id=task_id,
                    num_fragments=len(task.fragments)
                )
                
                logger.info(f"Task {task_id} completed successfully")
                
                # Schedule cleanup
                asyncio.create_task(self._schedule_cleanup(task_id))
                
                return result_file_path
                
            except Exception as e:
                error_str = str(e)
                from ..block3_paraphrasing.ai_providers import QuotaExceededError
                
                # Check if it's a quota error
                is_quota_error = (
                    isinstance(e, QuotaExceededError) or 
                    "quota" in error_str.lower() or 
                    "429" in error_str or 
                    "превышен лимит" in error_str.lower()
                )
                
                if is_quota_error:
                    # Save progress for quota errors - user can continue later
                    logger.warning(f"Quota exceeded for task {task_id}, saving progress...")
                    
                    # Count how many fragments were successfully processed
                    processed_count = sum(1 for f in task.paraphrased_fragments if f and f.strip())
                    
                    # Update task status to QUOTA_EXCEEDED (or keep as IN_PROGRESS)
                    task.status = TaskStatus.IN_PROGRESS  # Keep as in progress so it can be resumed
                    task.error_message = f"Quota exceeded. Processed {processed_count}/{len(task.fragments)} fragments."
                    task.metadata = task.metadata or {}
                    task.metadata["quota_exceeded"] = True
                    task.metadata["processed_count"] = processed_count
                    task.metadata["quota_error_time"] = datetime.now().isoformat()
                    
                    await self._save_task_to_disk(task)
                    
                    logger.info(f"Task {task_id} progress saved: {processed_count}/{len(task.fragments)} fragments processed")
                
                logger.error(f"Error processing task {task_id}: {e}")
                
                # Update task with error (if not quota error)
                if not is_quota_error:
                    task.status = TaskStatus.FAILED
                    task.error_message = str(e)
                    task.completed_at = datetime.now()
                    await self._save_task_to_disk(task)
                
                # Log error
                await self.system_logger.log_error(
                    task.chat_id,
                    f"task_{task_id}",
                    str(e)
                )
                
                raise
    
    async def _process_fragments(self, task: Task, progress_callback=None) -> List[str]:
        """Process fragments through the paraphrasing agent with bounded parallelism"""
        total_fragments = len(task.fragments)
        if total_fragments == 0:
            return []
        
        paraphrased_fragments: List[str] = [""] * total_fragments
        throttle_delay = settings.fragment_throttle_seconds
        processed_count = 0
        last_progress_update = 0
        
        async def process_single_fragment(index: int, fragment: str):
            """Process and store a single fragment result"""
            nonlocal processed_count, last_progress_update
            fragment_number = index + 1
            try:
                logger.info(f"Processing fragment {fragment_number}/{total_fragments} for task {task.task_id}")
                
                if throttle_delay > 0:
                    await asyncio.sleep(throttle_delay)
                
                async with self.fragment_semaphore:
                    paraphrased = await self.paraphrasing_agent.paraphrase(
                        text=fragment,
                        style="scientific-legal",
                        task_id=task.task_id,
                        fragment_index=fragment_number
                    )
                
                paraphrased_fragments[index] = paraphrased
                processed_count += 1
                
                await self.system_logger.log_fragment_processed(
                    task_id=task.task_id,
                    fragment_index=fragment_number,
                    total_fragments=total_fragments
                )
                
                # Send progress update every 5 fragments or at milestones (25%, 50%, 75%, 100%)
                progress_percent = int((processed_count / total_fragments) * 100)
                milestones = [25, 50, 75, 100]
                should_update = (
                    processed_count % 5 == 0 or  # Every 5 fragments (more frequent updates)
                    (progress_percent in milestones and progress_percent != last_progress_update) or  # At milestones
                    processed_count == total_fragments  # Final update
                )
                
                if should_update and progress_callback:
                    last_progress_update = progress_percent
                    progress_bar = "█" * (progress_percent // 5) + "░" * (20 - progress_percent // 5)
                    try:
                        await progress_callback(
                            f"🔄 *Перефразирование в процессе*\n\n"
                            f"📊 Прогресс: {processed_count}/{total_fragments} фрагментов\n"
                            f"📈 {progress_percent}% {progress_bar}\n"
                            f"⏳ Пожалуйста, подождите..."
                        )
                        logger.debug(f"Sent progress update: {processed_count}/{total_fragments} ({progress_percent}%)")
                    except Exception as e:
                        logger.error(f"Error sending progress update: {e}", exc_info=True)
                
            except Exception as e:
                error_str = str(e)
                # Check if it's a quota error
                from ..block3_paraphrasing.ai_providers import QuotaExceededError
                
                if isinstance(e, QuotaExceededError) or "quota" in error_str.lower() or "429" in error_str:
                    logger.error(f"Quota exceeded for fragment {fragment_number}: {e}")
                    # Store the original fragment if quota is exceeded
                    paraphrased_fragments[index] = fragment
                    # This will be handled at the task level
                    raise QuotaExceededError(str(e)) from e
                
                logger.error(f"Error processing fragment {fragment_number} for task {task.task_id}: {e}")
                
                paraphrased_fragments[index] = fragment
                
                await self.system_logger.log_error(
                    task.chat_id,
                    f"fragment_{fragment_number}",
                    str(e)
                )
        
        fragment_tasks = [
            asyncio.create_task(process_single_fragment(index, fragment))
            for index, fragment in enumerate(task.fragments)
        ]
        
        await asyncio.gather(*fragment_tasks)
        
        return paraphrased_fragments
    
    async def _build_document(self, task: Task, progress_callback=None) -> str:
        """Build the final document with replacements"""
        try:
            # Generate output file path
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"processed_{task.chat_id}_{timestamp}.docx"
            output_path = str(self.tasks_dir / output_filename)
            
            # Send progress message
            if progress_callback:
                await progress_callback(
                    f"📝 *Замена текста в документе*\n\n"
                    f"🔍 Ищу фрагменты в документе и заменяю их...\n"
                    f"⏳ Это может занять некоторое время..."
                )
            
            # Call document builder with progress callback
            success = await self.document_builder.replace_fragments(
                source_file_path=task.file_path,
                output_file_path=output_path,
                original_fragments=task.fragments,
                paraphrased_fragments=task.paraphrased_fragments,
                progress_callback=progress_callback
            )
            
            if not success:
                raise Exception("Document builder failed to create output file")
            
            logger.info(f"Document built successfully for task {task.task_id}")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error building document for task {task.task_id}: {e}")
            raise
    
    async def _save_task_to_disk(self, task: Task):
        """Save task state to disk for persistence"""
        try:
            task_file = self.tasks_dir / f"{task.task_id}.json"
            with open(task_file, 'w') as f:
                json.dump(task.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"Error saving task {task.task_id} to disk: {e}")
    
    async def _load_task_from_disk(self, task_id: str) -> Optional[Task]:
        """Load task from disk"""
        try:
            task_file = self.tasks_dir / f"{task_id}.json"
            if task_file.exists():
                with open(task_file, 'r') as f:
                    data = json.load(f)
                
                task = Task(
                    task_id=data["task_id"],
                    chat_id=data["chat_id"],
                    file_path=data["file_path"],
                    fragments=data["fragments"]
                )
                task.paraphrased_fragments = data.get("paraphrased_fragments", [])
                task.status = TaskStatus(data["status"])
                task.created_at = datetime.fromisoformat(data["created_at"])
                if data.get("completed_at"):
                    task.completed_at = datetime.fromisoformat(data["completed_at"])
                task.result_file_path = data.get("result_file_path")
                task.error_message = data.get("error_message")
                task.metadata = data.get("metadata", {})
                
                return task
        except Exception as e:
            logger.error(f"Error loading task {task_id} from disk: {e}")
            return None
    
    async def _schedule_cleanup(self, task_id: str):
        """Schedule cleanup of task files after retention period"""
        try:
            # Wait for retention period
            await asyncio.sleep(settings.file_retention_hours * 3600)
            
            # Clean up task
            await self.cleanup_task(task_id)
            
        except Exception as e:
            logger.error(f"Error in scheduled cleanup for task {task_id}: {e}")
    
    async def cleanup_task(self, task_id: str):
        """Clean up task and associated files"""
        task = self.tasks.get(task_id)
        if not task:
            task = await self._load_task_from_disk(task_id)
        
        if task:
            # Delete source file
            if task.file_path and os.path.exists(task.file_path):
                try:
                    os.remove(task.file_path)
                    logger.info(f"Deleted source file: {task.file_path}")
                except Exception as e:
                    logger.error(f"Error deleting source file: {e}")
            
            # Delete result file
            if task.result_file_path and os.path.exists(task.result_file_path):
                try:
                    os.remove(task.result_file_path)
                    logger.info(f"Deleted result file: {task.result_file_path}")
                except Exception as e:
                    logger.error(f"Error deleting result file: {e}")
            
            # Delete task file
            task_file = self.tasks_dir / f"{task_id}.json"
            if task_file.exists():
                try:
                    task_file.unlink()
                    logger.info(f"Deleted task file: {task_file}")
                except Exception as e:
                    logger.error(f"Error deleting task file: {e}")
            
            # Remove from memory
            if task_id in self.tasks:
                del self.tasks[task_id]
            
            logger.info(f"Cleaned up task {task_id}")
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status"""
        task = self.tasks.get(task_id)
        if not task:
            task = await self._load_task_from_disk(task_id)
        
        if task:
            return {
                "task_id": task.task_id,
                "status": task.status.value,
                "created_at": task.created_at.isoformat(),
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "fragments_count": len(task.fragments),
                "processed_count": len(task.paraphrased_fragments),
                "error_message": task.error_message
            }
        
        return None
    
    async def _save_document_to_db(self, task: Task, result_file_path: str):
        """Save document to database for future reference"""
        try:
            # Check if document already exists for this chat
            existing_doc = await self.database_manager.get_document_by_chat_id(task.chat_id)
            
            if existing_doc:
                # Update existing document with new version
                document = ParaphrasedDocument(
                    document_id=existing_doc.document_id,
                    chat_id=task.chat_id,
                    original_file_path=existing_doc.original_file_path,
                    current_file_path=result_file_path,
                    fragments=task.fragments,
                    paraphrased_fragments=task.paraphrased_fragments,
                    version=existing_doc.version + 1,
                    created_at=existing_doc.created_at,
                    updated_at=datetime.now(),
                    metadata={"task_id": task.task_id}
                )
            else:
                # Create new document
                document = ParaphrasedDocument(
                    document_id=task.task_id,
                    chat_id=task.chat_id,
                    original_file_path=task.file_path,
                    current_file_path=result_file_path,
                    fragments=task.fragments,
                    paraphrased_fragments=task.paraphrased_fragments,
                    version=1,
                    created_at=task.created_at,
                    updated_at=datetime.now(),
                    metadata={"task_id": task.task_id}
                )
            
            await self.database_manager.save_document(document)
            logger.info(f"Saved document {document.document_id} to database (version {document.version})")
        except Exception as e:
            logger.error(f"Failed to save document to database: {e}")
    
    async def load_existing_document(self, chat_id: int) -> Optional[ParaphrasedDocument]:
        """Load the most recent document for a chat from database"""
        try:
            document = await self.database_manager.get_document_by_chat_id(chat_id)
            if document:
                logger.info(f"Loaded existing document {document.document_id} for chat {chat_id}")
            return document
        except Exception as e:
            logger.error(f"Failed to load existing document: {e}")
            return None
    
    async def continue_with_existing_document(
        self, 
        chat_id: int, 
        new_fragments: List[str]
    ) -> Optional[str]:
        """
        Continue working with an existing document by adding new fragments
        
        Args:
            chat_id: Chat ID
            new_fragments: New fragments to paraphrase and add
            
        Returns:
            Path to updated document or None if failed
        """
        try:
            # Load existing document
            existing_doc = await self.load_existing_document(chat_id)
            if not existing_doc:
                logger.warning(f"No existing document found for chat {chat_id}")
                return None
            
            # Check if file still exists
            if not os.path.exists(existing_doc.current_file_path):
                logger.error(f"Existing document file not found: {existing_doc.current_file_path}")
                return None
            
            # Create new task with existing document as source
            task_id = str(uuid.uuid4())
            task = Task(
                task_id=task_id,
                chat_id=chat_id,
                file_path=existing_doc.current_file_path,  # Use current version as source
                fragments=new_fragments
            )
            
            # Process new fragments
            task.paraphrased_fragments = await self._process_fragments(task)
            
            # Build updated document (combining old and new fragments)
            # Merge fragments: existing + new
            all_fragments = existing_doc.fragments + new_fragments
            all_paraphrased = existing_doc.paraphrased_fragments + task.paraphrased_fragments
            
            # Create temporary task for building
            merge_task = Task(
                task_id=task_id,
                chat_id=chat_id,
                file_path=existing_doc.original_file_path,  # Always use original as source
                fragments=all_fragments
            )
            merge_task.paraphrased_fragments = all_paraphrased
            
            # Build document with all fragments
            result_file_path = await self._build_document(merge_task)
            
            # Save updated document to database
            updated_doc = ParaphrasedDocument(
                document_id=existing_doc.document_id,
                chat_id=chat_id,
                original_file_path=existing_doc.original_file_path,
                current_file_path=result_file_path,
                fragments=all_fragments,
                paraphrased_fragments=all_paraphrased,
                version=existing_doc.version + 1,
                created_at=existing_doc.created_at,
                updated_at=datetime.now(),
                metadata={"task_id": task_id, "previous_version": existing_doc.version}
            )
            
            await self.database_manager.save_document(updated_doc)
            logger.info(f"Updated document {updated_doc.document_id} to version {updated_doc.version}")
            
            return result_file_path
            
        except Exception as e:
            logger.error(f"Failed to continue with existing document: {e}")
            return None
