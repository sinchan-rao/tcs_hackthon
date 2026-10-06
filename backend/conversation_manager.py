"""JSON-backed, privacy-conscious conversation storage for the hackathon demo."""

import json
import os
import re
import tempfile
import threading
from datetime import datetime, timezone


DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CONVERSATIONS_FILE = os.path.join(DATA_DIR, "conversations.json")
PRIVATE_RESPONSE_PLACEHOLDER = (
    "A private banking response was shown in this conversation. "
    "Please ask again and complete any required verification."
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_message_content(content: str) -> str:
    """Redact credentials and full account/card numbers before disk storage."""
    cleaned = content.strip()
    cleaned = re.sub(
        r"\b(pin|otp|password|cvv)\s*(?:is|:|=)?\s*\d{3,8}\b",
        r"\1: [REDACTED]",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\b(account(?:\s+number)?|card(?:\s+number)?)\s*(?:is|:|=)?\s*[\d -]{6,}\b",
        r"\1: [REDACTED]",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\b\d{13,19}\b", "[REDACTED NUMBER]", cleaned)
    return cleaned


class ConversationManager:
    """Stores separate conversations by opaque server-side session ID."""

    def __init__(self) -> None:
        self._lock = threading.Lock()

    def _load_all(self) -> list[dict]:
        if not os.path.exists(CONVERSATIONS_FILE):
            return []
        try:
            with open(CONVERSATIONS_FILE, "r", encoding="utf-8") as file:
                data = json.load(file)
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            return []

    def _save_all(self, conversations: list[dict]) -> None:
        os.makedirs(DATA_DIR, exist_ok=True)
        descriptor, temporary_path = tempfile.mkstemp(
            prefix="conversations_", suffix=".json", dir=DATA_DIR, text=True
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as file:
                json.dump(conversations, file, indent=2, ensure_ascii=False)
            os.replace(temporary_path, CONVERSATIONS_FILE)
        finally:
            if os.path.exists(temporary_path):
                os.remove(temporary_path)

    def find_by_session(self, session_id: str | None) -> dict | None:
        if not session_id:
            return None
        with self._lock:
            return next(
                (item for item in self._load_all() if item.get("session_id") == session_id),
                None,
            )

    def ensure_conversation(self, session_id: str, conversation_id: str) -> dict:
        with self._lock:
            conversations = self._load_all()
            existing = next(
                (item for item in conversations if item.get("conversation_id") == conversation_id),
                None,
            )
            if existing:
                return existing

            now = _now()
            conversation = {
                "conversation_id": conversation_id,
                "session_id": session_id,
                "created_at": now,
                "updated_at": now,
                "messages": [],
            }
            conversations.append(conversation)
            self._save_all(conversations)
            return conversation

    def get_messages(self, conversation_id: str) -> list[dict]:
        with self._lock:
            conversation = next(
                (item for item in self._load_all() if item.get("conversation_id") == conversation_id),
                None,
            )
            return list(conversation.get("messages", [])) if conversation else []

    def append_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        private_response: bool = False,
    ) -> None:
        if role not in {"user", "assistant"}:
            raise ValueError("Conversation role must be user or assistant")

        saved_content = PRIVATE_RESPONSE_PLACEHOLDER if private_response else _safe_message_content(content)
        with self._lock:
            conversations = self._load_all()
            conversation = next(
                (item for item in conversations if item.get("conversation_id") == conversation_id),
                None,
            )
            if not conversation:
                return
            conversation.setdefault("messages", []).append(
                {"role": role, "content": saved_content, "timestamp": _now()}
            )
            conversation["updated_at"] = _now()
            self._save_all(conversations)


conversation_manager = ConversationManager()
