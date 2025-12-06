"""Domain entities"""
from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class Session:
    """Session entity"""
    session_id: str
    text: Optional[str] = None
    created_at: Optional[datetime] = None
    extracted: bool = False


@dataclass
class IndexStatus:
    """Index build status entity"""
    session_id: str
    status: str  # pending, building, ready, failed
    chunks: Optional[int] = None
    error: Optional[str] = None


@dataclass
class SummaryCache:
    """Summary cache entity"""
    cache_key: str
    summary: str
    created_at: float
    ttl: int = 600  # 10 minutes default


@dataclass
class SessionHistory:
    """Session history entry for previously processed uploads."""
    session_id: str
    filename: str
    uploaded_at: datetime
    status: str  # uploaded, processing, ready, failed
    model: str | None = None
    agent_mode: bool = False
    characters: int | None = None
    pages: int | None = None
    words: int | None = None
    reading_minutes: int | None = None
    file_size: int | None = None