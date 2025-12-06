"""Repository interfaces (Ports)"""
from abc import ABC, abstractmethod
from typing import Optional, List
from domain.entities import Session, IndexStatus, SessionHistory


class SessionRepository(ABC):
    """Repository interface for session management"""
    
    @abstractmethod
    async def get(self, session_id: str) -> Optional[Session]:
        """Get session by ID"""
        pass
    
    @abstractmethod
    async def save(self, session: Session) -> None:
        """Save session"""
        pass
    
    @abstractmethod
    async def delete(self, session_id: str) -> bool:
        """Delete session"""
        pass
    
    @abstractmethod
    async def exists(self, session_id: str) -> bool:
        """Check if session exists"""
        pass


class CacheRepository(ABC):
    """Repository interface for caching"""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[str]:
        """Get cached value"""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: str, ttl: int) -> None:
        """Set cached value with TTL"""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete cached value"""
        pass


class VectorStoreRepository(ABC):
    """Repository interface for vector store operations"""
    
    @abstractmethod
    def has_index(self, session_id: str) -> bool:
        """Check if index exists"""
        pass
    
    @abstractmethod
    def build_index(self, session_id: str, text: str) -> None:
        """Build index for session"""
        pass
    
    @abstractmethod
    def query(self, session_id: str, query: str, k: int = 4) -> List[str]:
        """Query index"""
        pass


class IndexStatusRepository(ABC):
    """Repository interface for index status"""
    
    @abstractmethod
    async def get(self, session_id: str) -> Optional[IndexStatus]:
        """Get index status"""
        pass
    
    @abstractmethod
    async def set(self, status: IndexStatus) -> None:
        """Set index status"""
        pass


class SessionHistoryRepository(ABC):
    """Repository interface for session history"""

    @abstractmethod
    async def upsert(self, entry: SessionHistory) -> None:
        """Create or update a history entry"""
        pass

    @abstractmethod
    async def update_status(
        self,
        session_id: str,
        status: str,
        *,
        characters: Optional[int] = None,
        pages: Optional[int] = None,
        words: Optional[int] = None,
        reading_minutes: Optional[int] = None,
    ) -> None:
        """Update status for a given session"""
        pass

    @abstractmethod
    async def list_recent(self, limit: int = 20) -> List[SessionHistory]:
        """List recent history entries"""
        pass

    @abstractmethod
    async def get(self, session_id: str) -> Optional[SessionHistory]:
        """Get history entry by session"""
        pass

