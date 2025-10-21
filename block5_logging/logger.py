"""
Block 5: End-to-end Logging and Monitoring
Records all operations for debugging, monitoring, and performance analysis
"""

import logging
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
import structlog

# Optional imports for Google Sheets
try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False
    gspread = None
    Credentials = None

from ..config import settings

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


class SystemLogger:
    """Comprehensive logging system for all operations"""
    
    def __init__(self):
        self.structured_logger = structlog.get_logger()
        self.google_sheets_client = None
        self.worksheet = None
        self._initialize_google_sheets()
        
        # Local log file path
        self.log_dir = Path(settings.temp_files_dir) / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Log files
        self.operations_log = self.log_dir / "operations.jsonl"
        self.errors_log = self.log_dir / "errors.jsonl"
        self.results_log = self.log_dir / "results.jsonl"
    
    def _initialize_google_sheets(self):
        """Initialize Google Sheets connection for logging"""
        if not GSPREAD_AVAILABLE:
            logger.info("Google Sheets not available (gspread not installed), using local logging only")
            self.google_sheets_client = None
            return
            
        try:
            if settings.google_sheets_credentials_path and settings.google_sheets_spreadsheet_id:
                # Load credentials
                creds = Credentials.from_service_account_file(
                    settings.google_sheets_credentials_path,
                    scopes=['https://www.googleapis.com/auth/spreadsheets']
                )
                
                # Initialize client
                self.google_sheets_client = gspread.authorize(creds)
                
                # Open spreadsheet
                spreadsheet = self.google_sheets_client.open_by_key(
                    settings.google_sheets_spreadsheet_id
                )
                
                # Get or create worksheets
                self._ensure_worksheets(spreadsheet)
                
                logger.info("Google Sheets logging initialized")
            else:
                logger.info("Google Sheets credentials not configured, using local logging only")
                
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets: {e}")
            self.google_sheets_client = None
    
    def _ensure_worksheets(self, spreadsheet):
        """Ensure required worksheets exist"""
        worksheet_names = [ws.title for ws in spreadsheet.worksheets()]
        
        # Define required worksheets and their headers
        required_sheets = {
            "Tasks": [
                "Timestamp", "Task ID", "Chat ID", "User", "Status",
                "Fragments Count", "Processing Time", "Error"
            ],
            "Operations": [
                "Timestamp", "Task ID", "Operation", "Provider", "Duration",
                "Success", "Error Message"
            ],
            "Results": [
                "Timestamp", "Task ID", "Fragment Index", "Original Text",
                "Paraphrased Text", "Provider Used", "Score"
            ],
            "Errors": [
                "Timestamp", "Chat ID", "Operation", "Error Type",
                "Error Message", "Stack Trace"
            ]
        }
        
        for sheet_name, headers in required_sheets.items():
            if sheet_name not in worksheet_names:
                # Create worksheet
                worksheet = spreadsheet.add_worksheet(
                    title=sheet_name,
                    rows=1000,
                    cols=len(headers)
                )
                # Add headers
                worksheet.update('A1', [headers])
            else:
                worksheet = spreadsheet.worksheet(sheet_name)
                # Ensure headers are correct
                try:
                    current_headers = worksheet.row_values(1)
                    if current_headers != headers:
                        worksheet.update('A1', [headers])
                except:
                    worksheet.update('A1', [headers])
    
    async def _append_to_sheet(self, worksheet_name: str, data: List[Any]):
        """Append data to Google Sheets worksheet"""
        if self.google_sheets_client:
            try:
                spreadsheet = self.google_sheets_client.open_by_key(
                    settings.google_sheets_spreadsheet_id
                )
                worksheet = spreadsheet.worksheet(worksheet_name)
                worksheet.append_row(data)
            except Exception as e:
                logger.error(f"Failed to append to Google Sheets: {e}")
    
    async def _write_local_log(self, log_file: Path, data: Dict[str, Any]):
        """Write to local log file"""
        try:
            with open(log_file, 'a') as f:
                f.write(json.dumps(data) + '\n')
        except Exception as e:
            logger.error(f"Failed to write local log: {e}")
    
    # Task logging methods
    
    async def log_task_start(self, chat_id: int, user_name: str):
        """Log when a user starts a new task"""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "event": "task_start",
            "chat_id": chat_id,
            "user_name": user_name
        }
        
        self.structured_logger.info("task_started", chat_id=chat_id, user_name=user_name)
        await self._write_local_log(self.operations_log, log_data)
    
    async def log_task_created(self, task_id: str, chat_id: int, num_fragments: int):
        """Log task creation"""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "event": "task_created",
            "task_id": task_id,
            "chat_id": chat_id,
            "num_fragments": num_fragments
        }
        
        self.structured_logger.info("task_created", task_id=task_id, chat_id=chat_id, num_fragments=num_fragments)
        await self._write_local_log(self.operations_log, log_data)
        
        # Log to Google Sheets
        await self._append_to_sheet("Tasks", [
            datetime.now().isoformat(),
            task_id,
            chat_id,
            "",  # User name (to be filled)
            "created",
            num_fragments,
            "",  # Processing time
            ""   # Error
        ])
    
    async def log_task_completed(self, chat_id: int, task_id: str, num_fragments: int):
        """Log task completion"""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "event": "task_completed",
            "task_id": task_id,
            "chat_id": chat_id,
            "num_fragments": num_fragments
        }
        
        self.structured_logger.info("task_completed", task_id=task_id, chat_id=chat_id, num_fragments=num_fragments)
        await self._write_local_log(self.operations_log, log_data)
    
    # File operations logging
    
    async def log_file_received(self, chat_id: int, file_name: str, file_size_mb: float):
        """Log file reception"""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "event": "file_received",
            "chat_id": chat_id,
            "file_name": file_name,
            "file_size_mb": file_size_mb
        }
        
        self.structured_logger.info("file_received", chat_id=chat_id, file_name=file_name, file_size_mb=file_size_mb)
        await self._write_local_log(self.operations_log, log_data)
    
    async def log_fragments_received(self, chat_id: int, num_fragments: int):
        """Log fragments reception"""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "event": "fragments_received",
            "chat_id": chat_id,
            "num_fragments": num_fragments
        }
        
        self.structured_logger.info("fragments_received", chat_id=chat_id, num_fragments=num_fragments)
        await self._write_local_log(self.operations_log, log_data)
    
    # Paraphrasing operations logging
    
    async def log_paraphrase_start(
        self,
        task_id: Optional[str],
        fragment_index: Optional[int],
        text_length: int
    ):
        """Log start of paraphrasing"""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "event": "paraphrase_start",
            "task_id": task_id,
            "fragment_index": fragment_index,
            "text_length": text_length
        }
        
        self.structured_logger.info("paraphrase_start", task_id=task_id, fragment_index=fragment_index, text_length=text_length)
        await self._write_local_log(self.operations_log, log_data)
    
    async def log_paraphrase_complete(
        self,
        task_id: Optional[str],
        fragment_index: Optional[int],
        provider_used: str,
        original_text: str,
        paraphrased_text: str
    ):
        """Log paraphrase completion with results"""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "event": "paraphrase_complete",
            "task_id": task_id,
            "fragment_index": fragment_index,
            "provider_used": provider_used,
            "original_length": len(original_text),
            "paraphrased_length": len(paraphrased_text)
        }
        
        self.structured_logger.info("paraphrase_complete", task_id=task_id, fragment_index=fragment_index, provider_used=provider_used)
        await self._write_local_log(self.operations_log, log_data)
        
        # Save results for quality analysis
        results_data = {
            "timestamp": datetime.now().isoformat(),
            "task_id": task_id,
            "fragment_index": fragment_index,
            "original_text": original_text[:500],  # Truncate for storage
            "paraphrased_text": paraphrased_text[:500],
            "provider_used": provider_used
        }
        await self._write_local_log(self.results_log, results_data)
        
        # Log to Google Sheets
        await self._append_to_sheet("Results", [
            datetime.now().isoformat(),
            task_id or "",
            fragment_index or 0,
            original_text[:100] + "..." if len(original_text) > 100 else original_text,
            paraphrased_text[:100] + "..." if len(paraphrased_text) > 100 else paraphrased_text,
            provider_used,
            ""  # Score
        ])
    
    async def log_fragment_processed(
        self,
        task_id: str,
        fragment_index: int,
        total_fragments: int
    ):
        """Log fragment processing progress"""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "event": "fragment_processed",
            "task_id": task_id,
            "fragment_index": fragment_index,
            "total_fragments": total_fragments,
            "progress_percent": (fragment_index / total_fragments) * 100
        }
        
        self.structured_logger.info("fragment_processed", task_id=task_id, fragment_index=fragment_index, total_fragments=total_fragments)
        await self._write_local_log(self.operations_log, log_data)
    
    # Document operations logging
    
    async def log_document_processed(
        self,
        source_path: str,
        output_path: str,
        total_fragments: int,
        replaced_fragments: int,
        skipped_fragments: int
    ):
        """Log document processing completion"""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "event": "document_processed",
            "source_path": source_path,
            "output_path": output_path,
            "total_fragments": total_fragments,
            "replaced_fragments": replaced_fragments,
            "skipped_fragments": skipped_fragments,
            "success_rate": (replaced_fragments / total_fragments * 100) if total_fragments > 0 else 0
        }
        
        self.structured_logger.info("document_processed", source_path=source_path, output_path=output_path, total_fragments=total_fragments)
        await self._write_local_log(self.operations_log, log_data)
    
    async def log_fragment_replaced(
        self,
        fragment_index: int,
        original_length: int,
        paraphrased_length: int
    ):
        """Log successful fragment replacement"""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "event": "fragment_replaced",
            "fragment_index": fragment_index,
            "original_length": original_length,
            "paraphrased_length": paraphrased_length,
            "length_change_percent": ((paraphrased_length - original_length) / original_length * 100) if original_length > 0 else 0
        }
        
        self.structured_logger.debug("fragment_replaced", fragment_index=fragment_index, original_length=original_length, paraphrased_length=paraphrased_length)
        await self._write_local_log(self.operations_log, log_data)
    
    async def log_fragment_not_found(self, fragment_index: int, fragment_text: str):
        """Log when a fragment is not found in document"""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "event": "fragment_not_found",
            "fragment_index": fragment_index,
            "fragment_preview": fragment_text
        }
        
        self.structured_logger.warning("fragment_not_found", fragment_index=fragment_index, fragment_preview=fragment_text[:100])
        await self._write_local_log(self.operations_log, log_data)
    
    # Error logging
    
    async def log_error(self, chat_id: int, operation: str, error_message: str):
        """Log errors with high priority"""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "event": "error",
            "chat_id": chat_id,
            "operation": operation,
            "error_message": error_message,
            "severity": "high"
        }
        
        self.structured_logger.error("error_occurred", chat_id=chat_id, operation=operation, error_message=error_message)
        await self._write_local_log(self.errors_log, log_data)
        
        # Log to Google Sheets
        await self._append_to_sheet("Errors", [
            datetime.now().isoformat(),
            chat_id,
            operation,
            "application_error",
            error_message[:500],  # Truncate long errors
            ""  # Stack trace (if available)
        ])
    
    # API call logging
    
    async def log_api_call(
        self,
        provider: str,
        success: bool,
        duration_seconds: float,
        error: Optional[str] = None
    ):
        """Log API calls to AI providers"""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "event": "api_call",
            "provider": provider,
            "success": success,
            "duration_seconds": duration_seconds,
            "error": error
        }
        
        level = "info" if success else "warning"
        getattr(self.structured_logger, level)("api_call", provider=provider, success=success, duration_seconds=duration_seconds, error=error)
        await self._write_local_log(self.operations_log, log_data)
        
        # Log to Google Sheets
        await self._append_to_sheet("Operations", [
            datetime.now().isoformat(),
            "",  # Task ID (to be filled by caller)
            "api_call",
            provider,
            duration_seconds,
            success,
            error or ""
        ])
    
    # Analytics methods
    
    async def get_daily_stats(self) -> Dict[str, Any]:
        """Get daily statistics from logs"""
        stats = {
            "date": datetime.now().date().isoformat(),
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "total_fragments": 0,
            "api_calls": {},
            "errors": []
        }
        
        # Read and analyze local logs
        try:
            if self.operations_log.exists():
                with open(self.operations_log, 'r') as f:
                    for line in f:
                        try:
                            log_entry = json.loads(line)
                            # Analyze log entry
                            if log_entry.get("event") == "task_created":
                                stats["total_tasks"] += 1
                            elif log_entry.get("event") == "task_completed":
                                stats["completed_tasks"] += 1
                            elif log_entry.get("event") == "api_call":
                                provider = log_entry.get("provider", "unknown")
                                if provider not in stats["api_calls"]:
                                    stats["api_calls"][provider] = {"success": 0, "failed": 0}
                                if log_entry.get("success"):
                                    stats["api_calls"][provider]["success"] += 1
                                else:
                                    stats["api_calls"][provider]["failed"] += 1
                        except json.JSONDecodeError:
                            continue
            
            if self.errors_log.exists():
                with open(self.errors_log, 'r') as f:
                    for line in f:
                        try:
                            log_entry = json.loads(line)
                            stats["errors"].append({
                                "operation": log_entry.get("operation"),
                                "message": log_entry.get("error_message", "")[:100]
                            })
                            stats["failed_tasks"] += 1
                        except json.JSONDecodeError:
                            continue
        
        except Exception as e:
            logger.error(f"Error getting daily stats: {e}")
        
        return stats
