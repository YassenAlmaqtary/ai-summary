from typing import List, Protocol


class VectorStorePort(Protocol):
    def has_index(self, key: str) -> bool:
        ...

    def build_index(self, session_id: str, text: str) -> None:
        ...

    def query(self, key: str, query: str, k: int = 4) -> List[str]:
        ...


class StoragePort(Protocol):
    def save_text(self, session_id: str, text: str) -> str:
        """Save text and return stored path or identifier"""

    def read_text(self, session_id: str) -> str:
        """Return stored text for session_id"""
