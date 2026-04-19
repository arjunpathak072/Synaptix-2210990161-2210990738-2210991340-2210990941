"""Persistent chat storage: one JSON file per session."""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path


class ChatStore:
    """Save/load chat conversations to `.synaptix_db/chats/<session_id>.json`."""

    def __init__(self, repo_path: str) -> None:
        self._dir = Path(repo_path) / ".synaptix_db" / "chats"
        self._dir.mkdir(parents=True, exist_ok=True)

    def save(self, messages: list[dict], session_id: str | None = None) -> str:
        sid = session_id or f"{int(time.time())}-{uuid.uuid4().hex[:6]}"
        path = self._dir / f"{sid}.json"
        path.write_text(json.dumps(messages, indent=2))
        return sid

    def load(self, session_id: str) -> list[dict]:
        path = self._dir / f"{session_id}.json"
        try:
            return json.loads(path.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def list_sessions(self) -> list[str]:
        return sorted(p.stem for p in self._dir.glob("*.json"))
