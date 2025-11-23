from pathlib import Path
import logging
from typing import List

log = logging.getLogger("ai-summary.faiss_adapter")

try:
    from ai.agent import VectorStoreManager, build_and_persist_faiss
except Exception:
    VectorStoreManager = None
    build_and_persist_faiss = None


class FaissAdapter:
    """Adapter that exposes a minimal VectorStorePort using local FAISS utilities.

    This adapter wraps the existing `ai.agent` utilities when available.
    """

    def __init__(self, index_root: Path):
        self.index_root = Path(index_root)
        self._vsm = None
        if VectorStoreManager is not None:
            try:
                self._vsm = VectorStoreManager(self.index_root)
            except Exception:
                self._vsm = None

    def has_index(self, key: str) -> bool:
        if self._vsm is None:
            return False
        return self._vsm.has_index(key)

    def build_index(self, session_id: str, text: str) -> None:
        if build_and_persist_faiss is None:
            log.warning("FAISS build not available in this environment")
            return
        build_and_persist_faiss(session_id, text, self.index_root)

    def query(self, key: str, query: str, k: int = 4) -> List[str]:
        if self._vsm is None:
            return []
        return self._vsm.query(key, query, k=k)
