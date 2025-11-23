"""
Dependency Injection Container
يوفر جميع التبعيات (Dependencies) للتطبيق
"""
from pathlib import Path
from typing import Optional

from domain.repositories import (
    SessionRepository,
    CacheRepository,
    VectorStoreRepository,
    IndexStatusRepository
)
from infrastructure.repositories import (
    InMemorySessionRepository,
    InMemoryCacheRepository,
    FAISSVectorStoreRepository,
    InMemoryIndexStatusRepository
)
from application.use_cases import (
    PDFExtractionUseCase,
    SummaryUseCase,
    LessonAgentUseCase,
    ChatAgentUseCase
)
from core.config import INDEX_ROOT
from pathlib import Path
from core.services import AgentService

# Global instances (singleton pattern)
_session_repo: Optional[SessionRepository] = None
_cache_repo: Optional[CacheRepository] = None
_vector_repo: Optional[VectorStoreRepository] = None
_index_status_repo: Optional[IndexStatusRepository] = None
_agent_service: Optional[AgentService] = None


def get_session_repository() -> SessionRepository:
    """Get session repository instance"""
    global _session_repo
    if _session_repo is None:
        _session_repo = InMemorySessionRepository()
    return _session_repo


def get_cache_repository() -> CacheRepository:
    """Get cache repository instance"""
    global _cache_repo
    if _cache_repo is None:
        _cache_repo = InMemoryCacheRepository(default_ttl=600)
    return _cache_repo


def get_vector_store_repository() -> VectorStoreRepository:
    """Get vector store repository instance"""
    global _vector_repo
    if _vector_repo is None:
        index_root = Path(INDEX_ROOT)
        index_root.mkdir(parents=True, exist_ok=True)
        _vector_repo = FAISSVectorStoreRepository(index_root)
    return _vector_repo


def get_index_status_repository() -> IndexStatusRepository:
    """Get index status repository instance"""
    global _index_status_repo
    if _index_status_repo is None:
        _index_status_repo = InMemoryIndexStatusRepository()
    return _index_status_repo


def get_agent_service() -> AgentService:
    """Get agent service instance"""
    global _agent_service
    if _agent_service is None:
        index_root = Path(INDEX_ROOT)
        index_root.mkdir(parents=True, exist_ok=True)
        _agent_service = AgentService(index_root=index_root)
    return _agent_service


def get_pdf_extraction_use_case() -> PDFExtractionUseCase:
    """Get PDF extraction use case"""
    return PDFExtractionUseCase(
        session_repo=get_session_repository()
    )


def get_summary_use_case() -> SummaryUseCase:
    """Get summary use case"""
    return SummaryUseCase(
        session_repo=get_session_repository(),
        cache_repo=get_cache_repository()
    )


def get_lesson_agent_use_case() -> LessonAgentUseCase:
    """Get lesson agent use case"""
    return LessonAgentUseCase(
        session_repo=get_session_repository(),
        vector_repo=get_vector_store_repository()
    )


def get_chat_agent_use_case() -> ChatAgentUseCase:
    """Get chat agent use case"""
    return ChatAgentUseCase(
        session_repo=get_session_repository(),
        vector_repo=get_vector_store_repository()
    )

