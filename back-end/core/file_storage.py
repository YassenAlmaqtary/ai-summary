from pathlib import Path
from typing import Optional


class FileStorage:
    """Simple file storage adapter for saving and reading extracted texts.

    Stores texts under `storage_root/texts/<session_id>.txt`.
    """

    def __init__(self, storage_root: Path):
        self.storage_root = Path(storage_root)
        self.text_root = self.storage_root / "texts"
        self.text_root.mkdir(parents=True, exist_ok=True)

    def save_text(self, session_id: str, text: str) -> str:
        p = self.text_root / f"{session_id}.txt"
        p.write_text(text, encoding="utf-8")
        return str(p)

    def read_text(self, session_id: str) -> Optional[str]:
        p = self.text_root / f"{session_id}.txt"
        if not p.exists():
            return None
        return p.read_text(encoding="utf-8")
