from pathlib import Path
import logging
from typing import List, Optional

from .config import INDEX_ROOT, UPLOAD_DIR
from .file_storage import FileStorage
from .faiss_adapter import FaissAdapter
from ai.agent import build_lesson_prompt, stream_agent_response

log = logging.getLogger("ai-summary.services")


class UploadService:
    def __init__(self, storage_root: Path = UPLOAD_DIR):
        self.storage = FileStorage(storage_root)

    def save_text(self, session_id: str, text: str) -> str:
        return self.storage.save_text(session_id, text)


class AgentService:
    def __init__(self, index_root: Path = INDEX_ROOT):
        self.index_root = Path(index_root)
        self.adapter = FaissAdapter(self.index_root)

    def retrieve(self, session_id: str, query: str, k: int = 4) -> List[str]:
        return self.adapter.query(session_id, query, k=k)

    def build_index(self, session_id: str, text: str) -> None:
        self.adapter.build_index(session_id, text)

    def build_prompt(self, core_text: str, retrieved: Optional[List[str]] = None, language: str = "العربية") -> str:
        return build_lesson_prompt(core_text, retrieved, language)

    async def stream_response(self, prompt: str, model: Optional[str] = None):
        async for chunk in stream_agent_response(prompt, model=model):
            yield chunk
