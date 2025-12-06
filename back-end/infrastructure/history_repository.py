"""
Session history repository stored in a JSON file.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from domain.entities import SessionHistory
from domain.repositories import SessionHistoryRepository


class JsonSessionHistoryRepository(SessionHistoryRepository):
    """Persist session history entries in a JSON file."""

    def __init__(self, history_file: Path, max_entries: int = 100):
        self.history_file = Path(history_file)
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        self.max_entries = max_entries
        self._lock = asyncio.Lock()

    async def upsert(self, entry: SessionHistory) -> None:
        async with self._lock:
            entries = self._load_entries()
            entries = [e for e in entries if e["session_id"] != entry.session_id]
            entries.insert(0, self._serialize(entry))
            entries = entries[: self.max_entries]
            self._save_entries(entries)

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
        async with self._lock:
            entries = self._load_entries()
            updated = False
            for entry in entries:
                if entry["session_id"] == session_id:
                    entry["status"] = status
                    if characters is not None:
                        entry["characters"] = characters
                    if pages is not None:
                        entry["pages"] = pages
                    if words is not None:
                        entry["words"] = words
                    if reading_minutes is not None:
                        entry["reading_minutes"] = reading_minutes
                    updated = True
                    break
            if not updated:
                # create minimal entry if missing
                entries.insert(
                    0,
                    {
                        "session_id": session_id,
                        "filename": "",
                        "uploaded_at": datetime.utcnow().isoformat(),
                        "status": status,
                        "model": None,
                        "agent_mode": False,
                        "characters": characters,
                        "pages": pages,
                        "words": words,
                        "reading_minutes": reading_minutes,
                    },
                )
            entries = entries[: self.max_entries]
            self._save_entries(entries)

    async def list_recent(self, limit: int = 20) -> List[SessionHistory]:
        async with self._lock:
            entries = self._load_entries()
        return [self._deserialize(e) for e in entries[:limit]]

    async def get(self, session_id: str) -> Optional[SessionHistory]:
        async with self._lock:
            entries = self._load_entries()
        for entry in entries:
            if entry["session_id"] == session_id:
                return self._deserialize(entry)
        return None

    def _load_entries(self) -> List[dict]:
        if not self.history_file.exists():
            return []
        try:
            data = json.loads(self.history_file.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except Exception:
            pass
        return []

    def _save_entries(self, entries: List[dict]) -> None:
        self.history_file.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _serialize(entry: SessionHistory) -> dict:
        return {
            "session_id": entry.session_id,
            "filename": entry.filename,
            "uploaded_at": entry.uploaded_at.isoformat(),
            "status": entry.status,
            "model": entry.model,
            "agent_mode": entry.agent_mode,
            "characters": entry.characters,
            "pages": entry.pages,
            "words": entry.words,
            "reading_minutes": entry.reading_minutes,
            "file_size": entry.file_size,
        }

    @staticmethod
    def _deserialize(payload: dict) -> SessionHistory:
        uploaded_at = payload.get("uploaded_at")
        if isinstance(uploaded_at, str):
            try:
                uploaded_at_dt = datetime.fromisoformat(uploaded_at)
            except ValueError:
                uploaded_at_dt = datetime.utcnow()
        else:
            uploaded_at_dt = datetime.utcnow()
        return SessionHistory(
            session_id=payload.get("session_id", ""),
            filename=payload.get("filename", ""),
            uploaded_at=uploaded_at_dt,
            status=payload.get("status", "unknown"),
            model=payload.get("model"),
            agent_mode=payload.get("agent_mode", False),
            characters=payload.get("characters"),
            pages=payload.get("pages"),
            words=payload.get("words"),
            reading_minutes=payload.get("reading_minutes"),
            file_size=payload.get("file_size"),
        )

