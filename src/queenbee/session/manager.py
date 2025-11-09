"""Session management."""

import logging
from uuid import UUID

from queenbee.db.connection import DatabaseManager
from queenbee.db.models import SessionRepository, SessionStatus

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages user sessions and lifecycle."""

    def __init__(self, db: DatabaseManager):
        """Initialize session manager.

        Args:
            db: Database manager.
        """
        self.db = db
        self.session_repo = SessionRepository(db)
        self._current_session_id: UUID | None = None

    def start_session(self) -> UUID:
        """Start a new session.

        Returns:
            Session ID.
        """
        # Terminate any active sessions from previous runs
        terminated_count = self.session_repo.terminate_all_active_sessions()
        if terminated_count > 0:
            logger.info(f"Cleaned up {terminated_count} orphaned session(s)")

        # Create new session
        self._current_session_id = self.session_repo.create_session()
        logger.info(f"Started new session: {self._current_session_id}")
        return self._current_session_id

    def end_session(self) -> None:
        """End the current session."""
        if self._current_session_id:
            self.session_repo.terminate_session(self._current_session_id)
            logger.info(f"Ended session: {self._current_session_id}")
            self._current_session_id = None

    @property
    def current_session_id(self) -> UUID | None:
        """Get current session ID."""
        return self._current_session_id

    def __enter__(self) -> "SessionManager":
        """Context manager entry."""
        self.start_session()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.end_session()
