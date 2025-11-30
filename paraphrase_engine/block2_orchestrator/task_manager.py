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
        self.processing_lock = asyncio.Lock()
        
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
    
    async def process_task(self, task_id: str) -> Optional[str]:
        """
        Process a task through the entire pipeline
        Returns the path to the result file if successful, None otherwise
        """
        task = self.tasks.get(task_id)
        if not task:
            logger.error(f"Task {task_id} not found")
            return None
        
        async with self.processing_lock:
            try:
                # Update task status
                task.status = TaskStatus.PROCESSING
                await self._save_task_to_disk(task)
                
                logger.info(f"Starting processing for task {task_id}")
                
                # Step 1: Process each fragment through the paraphrasing agent
                paraphrased_fragments = await self._process_fragments(task)
                task.paraphrased_fragments = paraphrased_fragments
                
                # Step 2: Build the new document with replacements
                result_file_path = await self._build_document(task)
                
                # Update task with results
                task.result_file_path = result_file_path
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.now()
                
                # Save final task state
                await self._save_task_to_disk(task)
                
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
                logger.error(f"Error processing task {task_id}: {e}")
                
                # Update task with error
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
    
    async def _process_fragments(self, task: Task) -> List[str]:
        """Process fragments through the paraphrasing agent"""
        paraphrased_fragments = []
        total_fragments = len(task.fragments)
        
        for i, fragment in enumerate(task.fragments, 1):
            try:
                logger.info(f"Processing fragment {i}/{total_fragments} for task {task.task_id}")
                
                # Call the paraphrasing agent for each fragment
                paraphrased = await self.paraphrasing_agent.paraphrase(
                    text=fragment,
                    style="scientific-legal",  # As per requirements
                    task_id=task.task_id,
                    fragment_index=i
                )
                
                paraphrased_fragments.append(paraphrased)
                
                # Log progress
                await self.system_logger.log_fragment_processed(
                    task_id=task.task_id,
                    fragment_index=i,
                    total_fragments=total_fragments
                )
                
                # Small delay to avoid rate limiting
                if i < total_fragments:
                    await asyncio.sleep(1)
                    
            except Exception as e:
                logger.error(f"Error processing fragment {i} for task {task.task_id}: {e}")
                
                # Use original fragment if paraphrasing fails
                paraphrased_fragments.append(fragment)
                
                # Log the error but continue
                await self.system_logger.log_error(
                    task.chat_id,
                    f"fragment_{i}",
                    str(e)
                )
        
        return paraphrased_fragments
    
    async def _build_document(self, task: Task) -> str:
        """Build the final document with replacements"""
        try:
            # Generate output file path
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"processed_{task.chat_id}_{timestamp}.docx"
            output_path = str(self.tasks_dir / output_filename)
            
            # Call document builder
            success = await self.document_builder.replace_fragments(
                source_file_path=task.file_path,
                output_file_path=output_path,
                original_fragments=task.fragments,
                paraphrased_fragments=task.paraphrased_fragments
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
