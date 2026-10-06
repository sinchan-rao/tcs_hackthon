"""Secure, server-side session records for FinChat conversations.

The browser receives only an opaque random identifier in an HttpOnly cookie.
Conversation identifiers and all session state remain on the server.
"""

import os
import secrets
import threading
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import Response


COOKIE_NAME = "bank_session"
COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 30


def _is_truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def cookie_secure_enabled() -> bool:
    """Use Secure cookies by default outside explicitly local development."""
    configured_value = os.getenv("BANK_COOKIE_SECURE")
    if configured_value is not None:
        return _is_truthy(configured_value)
    environment = os.getenv("APP_ENV", "development").strip().lower()
    return environment not in {"development", "dev", "local", "test"}


@dataclass(frozen=True)
class SessionRecord:
    session_id: str
    conversation_id: str
    created_at: str


class SessionManager:
    """Creates and validates opaque browser sessions for this prototype."""

    def __init__(self) -> None:
        self._sessions: dict[str, SessionRecord] = {}
        self._lock = threading.Lock()

    def ensure_session(self, session_id: str | None) -> tuple[SessionRecord, bool]:
        """Return an existing session or create a cryptographically random one."""
        with self._lock:
            if session_id:
                existing_session = self._sessions.get(session_id)
                if existing_session:
                    return existing_session, False

            record = SessionRecord(
                session_id=secrets.token_urlsafe(32),
                conversation_id=f"conv_{secrets.token_urlsafe(18)}",
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            self._sessions[record.session_id] = record
            return record, True

    def restore_session(self, session_id: str, conversation_id: str, created_at: str) -> SessionRecord:
        """Restore a server-side mapping after an application restart."""
        with self._lock:
            record = SessionRecord(
                session_id=session_id,
                conversation_id=conversation_id,
                created_at=created_at,
            )
            self._sessions[session_id] = record
            return record

    def create_session(self) -> SessionRecord:
        """Create a new session without deleting previous conversations."""
        return self.ensure_session(None)[0]

    def set_session_cookie(self, response: Response, session_id: str) -> None:
        """Attach an opaque cookie without exposing it to client-side scripts."""
        response.set_cookie(
            key=COOKIE_NAME,
            value=session_id,
            max_age=COOKIE_MAX_AGE_SECONDS,
            httponly=True,
            secure=cookie_secure_enabled(),
            samesite="lax",
            path="/",
        )


session_manager = SessionManager()
