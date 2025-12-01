"""
Database manager for storing paraphrased documents and their versions
Supports both SQLite and PostgreSQL
"""

import os
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class ParaphrasedDocument:
    """Represents a paraphrased document with version history"""
    
    def __init__(
        self,
        document_id: str,
        chat_id: int,
        original_file_path: str,
        current_file_path: str,
        fragments: List[str],
        paraphrased_fragments: List[str],
        version: int = 1,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.document_id = document_id
        self.chat_id = chat_id
        self.original_file_path = original_file_path
        self.current_file_path = current_file_path
        self.fragments = fragments
        self.paraphrased_fragments = paraphrased_fragments
        self.version = version
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "document_id": self.document_id,
            "chat_id": self.chat_id,
            "original_file_path": self.original_file_path,
            "current_file_path": self.current_file_path,
            "fragments": json.dumps(self.fragments, ensure_ascii=False),
            "paraphrased_fragments": json.dumps(self.paraphrased_fragments, ensure_ascii=False),
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": json.dumps(self.metadata, ensure_ascii=False)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ParaphrasedDocument':
        """Create from dictionary"""
        return cls(
            document_id=data["document_id"],
            chat_id=data["chat_id"],
            original_file_path=data["original_file_path"],
            current_file_path=data["current_file_path"],
            fragments=json.loads(data["fragments"]) if isinstance(data["fragments"], str) else data["fragments"],
            paraphrased_fragments=json.loads(data["paraphrased_fragments"]) if isinstance(data["paraphrased_fragments"], str) else data["paraphrased_fragments"],
            version=data["version"],
            created_at=datetime.fromisoformat(data["created_at"]) if isinstance(data["created_at"], str) else data["created_at"],
            updated_at=datetime.fromisoformat(data["updated_at"]) if isinstance(data["updated_at"], str) else data["updated_at"],
            metadata=json.loads(data["metadata"]) if isinstance(data["metadata"], str) else data["metadata"]
        )


class DatabaseManager:
    """Manages database operations for paraphrased documents"""
    
    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize database manager
        
        Args:
            database_url: Database connection URL (sqlite:///path or postgresql://...)
                         If None, uses DATABASE_URL from environment or defaults to SQLite
        """
        from ..config import settings
        
        self.database_url = database_url or settings.database_url
        self.is_postgres = self.database_url.startswith("postgresql://") or self.database_url.startswith("postgres://")
        self.connection = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize database connection and create tables"""
        if self._initialized:
            return
        
        try:
            if self.is_postgres:
                await self._init_postgres()
            else:
                await self._init_sqlite()
            
            await self._create_tables()
            self._initialized = True
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def _init_postgres(self):
        """Initialize PostgreSQL connection"""
        try:
            import asyncpg
            # Parse connection string
            # postgresql://user:pass@host:port/dbname
            import re
            match = re.match(r'postgres(ql)?://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', self.database_url)
            if not match:
                raise ValueError(f"Invalid PostgreSQL URL format: {self.database_url}")
            
            user, password, host, port, database = match.groups()
            
            self.connection = await asyncpg.connect(
                host=host,
                port=int(port),
                user=user,
                password=password,
                database=database
            )
            logger.info("Connected to PostgreSQL database")
        except ImportError:
            raise ImportError("asyncpg is required for PostgreSQL. Install with: pip install asyncpg")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise
    
    async def _init_sqlite(self):
        """Initialize SQLite connection"""
        try:
            import aiosqlite
            # Extract path from sqlite:///path
            db_path = self.database_url.replace("sqlite:///", "")
            # Ensure directory exists
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            
            self.connection = await aiosqlite.connect(db_path)
            # Enable foreign keys
            await self.connection.execute("PRAGMA foreign_keys = ON")
            logger.info(f"Connected to SQLite database: {db_path}")
        except ImportError:
            raise ImportError("aiosqlite is required for SQLite. Install with: pip install aiosqlite")
        except Exception as e:
            logger.error(f"Failed to connect to SQLite: {e}")
            raise
    
    async def _create_tables(self):
        """Create database tables"""
        if self.is_postgres:
            await self._create_tables_postgres()
        else:
            await self._create_tables_sqlite()
    
    async def _create_tables_postgres(self):
        """Create tables for PostgreSQL"""
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS paraphrased_documents (
                document_id TEXT PRIMARY KEY,
                chat_id BIGINT NOT NULL,
                original_file_path TEXT NOT NULL,
                current_file_path TEXT NOT NULL,
                fragments TEXT NOT NULL,
                paraphrased_fragments TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                metadata TEXT
            );
        """)
        
        # Create index for faster lookups
        await self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_paraphrased_documents_chat_id 
            ON paraphrased_documents(chat_id);
        """)
        
        await self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_paraphrased_documents_updated_at 
            ON paraphrased_documents(updated_at DESC);
        """)
        
        await self.connection.commit()
    
    async def _create_tables_sqlite(self):
        """Create tables for SQLite"""
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS paraphrased_documents (
                document_id TEXT PRIMARY KEY,
                chat_id INTEGER NOT NULL,
                original_file_path TEXT NOT NULL,
                current_file_path TEXT NOT NULL,
                fragments TEXT NOT NULL,
                paraphrased_fragments TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                metadata TEXT
            );
        """)
        
        # Create indexes
        await self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_paraphrased_documents_chat_id 
            ON paraphrased_documents(chat_id);
        """)
        
        await self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_paraphrased_documents_updated_at 
            ON paraphrased_documents(updated_at DESC);
        """)
        
        await self.connection.commit()
    
    async def save_document(self, document: ParaphrasedDocument) -> bool:
        """Save or update a paraphrased document"""
        try:
            await self.initialize()
            
            doc_dict = document.to_dict()
            
            if self.is_postgres:
                await self.connection.execute("""
                    INSERT INTO paraphrased_documents (
                        document_id, chat_id, original_file_path, current_file_path,
                        fragments, paraphrased_fragments, version, created_at, updated_at, metadata
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    ON CONFLICT (document_id) DO UPDATE SET
                        current_file_path = EXCLUDED.current_file_path,
                        fragments = EXCLUDED.fragments,
                        paraphrased_fragments = EXCLUDED.paraphrased_fragments,
                        version = EXCLUDED.version,
                        updated_at = EXCLUDED.updated_at,
                        metadata = EXCLUDED.metadata
                """, 
                    doc_dict["document_id"],
                    doc_dict["chat_id"],
                    doc_dict["original_file_path"],
                    doc_dict["current_file_path"],
                    doc_dict["fragments"],
                    doc_dict["paraphrased_fragments"],
                    doc_dict["version"],
                    doc_dict["created_at"],
                    doc_dict["updated_at"],
                    doc_dict["metadata"]
                )
                await self.connection.commit()
            else:
                await self.connection.execute("""
                    INSERT OR REPLACE INTO paraphrased_documents (
                        document_id, chat_id, original_file_path, current_file_path,
                        fragments, paraphrased_fragments, version, created_at, updated_at, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    doc_dict["document_id"],
                    doc_dict["chat_id"],
                    doc_dict["original_file_path"],
                    doc_dict["current_file_path"],
                    doc_dict["fragments"],
                    doc_dict["paraphrased_fragments"],
                    doc_dict["version"],
                    doc_dict["created_at"],
                    doc_dict["updated_at"],
                    doc_dict["metadata"]
                ))
                await self.connection.commit()
            
            logger.info(f"Saved document {document.document_id} (version {document.version})")
            return True
        except Exception as e:
            logger.error(f"Failed to save document: {e}")
            return False
    
    async def get_document_by_chat_id(self, chat_id: int) -> Optional[ParaphrasedDocument]:
        """Get the most recent document for a chat"""
        try:
            await self.initialize()
            
            if self.is_postgres:
                row = await self.connection.fetchrow("""
                    SELECT * FROM paraphrased_documents
                    WHERE chat_id = $1
                    ORDER BY updated_at DESC
                    LIMIT 1
                """, chat_id)
                if not row:
                    return None
                data = dict(row)
            else:
                cursor = await self.connection.execute("""
                    SELECT * FROM paraphrased_documents
                    WHERE chat_id = ?
                    ORDER BY updated_at DESC
                    LIMIT 1
                """, (chat_id,))
                row = await cursor.fetchone()
                if not row:
                    return None
                columns = [desc[0] for desc in cursor.description]
                data = dict(zip(columns, row))
            
            return ParaphrasedDocument.from_dict(data)
        except Exception as e:
            logger.error(f"Failed to get document: {e}")
            return None
    
    async def get_document_by_id(self, document_id: str) -> Optional[ParaphrasedDocument]:
        """Get document by ID"""
        try:
            await self.initialize()
            
            if self.is_postgres:
                row = await self.connection.fetchrow("""
                    SELECT * FROM paraphrased_documents
                    WHERE document_id = $1
                """, document_id)
                if not row:
                    return None
                data = dict(row)
            else:
                cursor = await self.connection.execute("""
                    SELECT * FROM paraphrased_documents
                    WHERE document_id = ?
                """, (document_id,))
                row = await cursor.fetchone()
                if not row:
                    return None
                columns = [desc[0] for desc in cursor.description]
                data = dict(zip(columns, row))
            
            return ParaphrasedDocument.from_dict(data)
        except Exception as e:
            logger.error(f"Failed to get document: {e}")
            return None
    
    async def list_documents_by_chat_id(self, chat_id: int) -> List[ParaphrasedDocument]:
        """List all documents for a chat"""
        try:
            await self.initialize()
            
            if self.is_postgres:
                rows = await self.connection.fetch("""
                    SELECT * FROM paraphrased_documents
                    WHERE chat_id = $1
                    ORDER BY updated_at DESC
                """, chat_id)
            else:
                cursor = await self.connection.execute("""
                    SELECT * FROM paraphrased_documents
                    WHERE chat_id = ?
                    ORDER BY updated_at DESC
                """, (chat_id,))
                rows = await cursor.fetchall()
            
            documents = []
            if self.is_postgres:
                for row in rows:
                    data = dict(row)
                    documents.append(ParaphrasedDocument.from_dict(data))
            else:
                cursor = await self.connection.execute("""
                    SELECT * FROM paraphrased_documents
                    WHERE chat_id = ?
                    ORDER BY updated_at DESC
                """, (chat_id,))
                rows = await cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                for row in rows:
                    data = dict(zip(columns, row))
                    documents.append(ParaphrasedDocument.from_dict(data))
            
            return documents
        except Exception as e:
            logger.error(f"Failed to list documents: {e}")
            return []
    
    async def close(self):
        """Close database connection"""
        if self.connection:
            if self.is_postgres:
                await self.connection.close()
            else:
                await self.connection.close()
            self.connection = None
            self._initialized = False

