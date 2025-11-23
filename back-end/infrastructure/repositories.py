"""Repository implementations (Adapters)"""
import time
import hashlib
import asyncio
from typing import Optional, List, Dict
from pathlib import Path

from domain.repositories import (
    SessionRepository,
    CacheRepository,
    VectorStoreRepository,
    IndexStatusRepository
)
from domain.entities import Session, IndexStatus
from core.faiss_adapter import FaissAdapter
from core.file_storage import FileStorage


class InMemorySessionRepository(SessionRepository):
    """In-memory session repository"""
    
    def __init__(self):
        self._sessions: Dict[str, Session] = {}
        self._pending_tasks: Dict[str, asyncio.Task] = {}
    
    async def get(self, session_id: str) -> Optional[Session]:
        return self._sessions.get(session_id)
    
    async def save(self, session: Session) -> None:
        self._sessions[session.session_id] = session
    
    async def delete(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False
    
    async def exists(self, session_id: str) -> bool:
        return session_id in self._sessions
    
    def set_pending_task(self, session_id: str, task: asyncio.Task) -> None:
        """Set pending extraction task"""
        self._pending_tasks[session_id] = task
    
    def get_pending_task(self, session_id: str) -> Optional[asyncio.Task]:
        """Get pending extraction task"""
        return self._pending_tasks.get(session_id)
    
    def remove_pending_task(self, session_id: str) -> None:
        """Remove pending task"""
        self._pending_tasks.pop(session_id, None)


class InMemoryCacheRepository(CacheRepository):
    """In-memory cache repository"""
    
    def __init__(self, default_ttl: int = 600):
        self._cache: Dict[str, tuple[float, str]] = {}  # (timestamp, value)
        self._default_ttl = default_ttl
    
    async def get(self, key: str) -> Optional[str]:
        if key not in self._cache:
            return None
        
        timestamp, value = self._cache[key]
        if time.time() - timestamp > self._default_ttl:
            del self._cache[key]
            return None
        
        return value
    
    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> None:
        # ttl parameter is kept for interface compatibility but not used
        self._cache[key] = (time.time(), value)
    
    async def delete(self, key: str) -> None:
        self._cache.pop(key, None)
    
    def generate_key(self, text: str) -> str:
        """Generate cache key from text"""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()


class FAISSVectorStoreRepository(VectorStoreRepository):
    """FAISS vector store repository implementation"""
    
    def __init__(self, index_root: Path):
        self.adapter = FaissAdapter(index_root)
    
    def has_index(self, session_id: str) -> bool:
        return self.adapter.has_index(session_id)
    
    def build_index(self, session_id: str, text: str) -> None:
        self.adapter.build_index(session_id, text)
    
    def query(self, session_id: str, query: str, k: int = 4) -> List[str]:
        return self.adapter.query(session_id, query, k=k)


class InMemoryIndexStatusRepository(IndexStatusRepository):
    """In-memory index status repository"""
    
    def __init__(self):
        self._statuses: Dict[str, IndexStatus] = {}
    
    async def get(self, session_id: str) -> Optional[IndexStatus]:
        return self._statuses.get(session_id)
    
    async def set(self, status: IndexStatus) -> None:
        self._statuses[status.session_id] = status

