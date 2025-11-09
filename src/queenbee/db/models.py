"""Database models and data access layer."""

import json
import logging
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from queenbee.db.connection import DatabaseManager

logger = logging.getLogger(__name__)


class AgentType(str, Enum):
    """Agent type enumeration."""

    QUEEN = "queen"
    DIVERGENT = "divergent"
    CONVERGENT = "convergent"
    CRITICAL = "critical"


class AgentStatus(str, Enum):
    """Agent status enumeration."""

    ACTIVE = "active"
    IDLE = "idle"
    TERMINATED = "terminated"


class SessionStatus(str, Enum):
    """Session status enumeration."""

    ACTIVE = "active"
    COMPLETED = "completed"
    TERMINATED = "terminated"


class MessageRole(str, Enum):
    """Message role enumeration."""

    USER = "user"
    QUEEN = "queen"
    SPECIALIST = "specialist"


class MemoryType(str, Enum):
    """Memory type enumeration."""

    WORKING = "working"
    REASONING = "reasoning"
    OBSERVATION = "observation"


class TaskStatus(str, Enum):
    """Task status enumeration."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class SessionRepository:
    """Repository for session operations."""

    def __init__(self, db: DatabaseManager):
        """Initialize repository.

        Args:
            db: Database manager.
        """
        self.db = db

    def create_session(self) -> UUID:
        """Create a new session.

        Returns:
            Session ID.
        """
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "INSERT INTO sessions (status) VALUES (%s) RETURNING id",
                (SessionStatus.ACTIVE.value,),
            )
            result = cursor.fetchone()
            session_id = result["id"]
            logger.info(f"Created session: {session_id}")
            return session_id

    def terminate_session(self, session_id: UUID) -> None:
        """Terminate a session.

        Args:
            session_id: Session ID to terminate.
        """
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "UPDATE sessions SET status = %s, ended_at = NOW() WHERE id = %s",
                (SessionStatus.TERMINATED.value, session_id),
            )
            logger.info(f"Terminated session: {session_id}")

    def terminate_all_active_sessions(self) -> int:
        """Terminate all active sessions (for system restart).

        Returns:
            Number of sessions terminated.
        """
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "UPDATE sessions SET status = %s, ended_at = NOW() "
                "WHERE status = %s RETURNING id",
                (SessionStatus.TERMINATED.value, SessionStatus.ACTIVE.value),
            )
            count = cursor.rowcount
            logger.info(f"Terminated {count} active sessions")
            return count


class AgentRepository:
    """Repository for agent operations."""

    def __init__(self, db: DatabaseManager):
        """Initialize repository.

        Args:
            db: Database manager.
        """
        self.db = db

    def create_agent(
        self,
        agent_type: AgentType,
        session_id: UUID,
        system_prompt: str,
        configuration: dict[str, Any] | None = None,
    ) -> UUID:
        """Create a new agent.

        Args:
            agent_type: Type of agent.
            session_id: Session ID.
            system_prompt: Agent's system prompt.
            configuration: Optional agent configuration.

        Returns:
            Agent ID.
        """
        agent_id = uuid4()
        config_json = json.dumps(configuration) if configuration else None

        with self.db.get_cursor() as cursor:
            cursor.execute(
                "INSERT INTO agents (id, type, session_id, system_prompt, configuration) "
                "VALUES (%s, %s, %s, %s, %s) RETURNING id",
                (agent_id, agent_type.value, session_id, system_prompt, config_json),
            )
            logger.info(f"Created agent: {agent_id} (type={agent_type.value})")
            return agent_id

    def update_agent_status(self, agent_id: UUID, status: AgentStatus) -> None:
        """Update agent status.

        Args:
            agent_id: Agent ID.
            status: New status.
        """
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "UPDATE agents SET status = %s WHERE id = %s",
                (status.value, agent_id),
            )
            logger.debug(f"Updated agent {agent_id} status to {status.value}")

    def update_agent_activity(self, agent_id: UUID) -> None:
        """Update agent last activity timestamp.

        Args:
            agent_id: Agent ID.
        """
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "UPDATE agents SET last_activity_at = NOW() WHERE id = %s",
                (agent_id,),
            )

    def get_idle_agents(self, idle_minutes: int) -> list[dict[str, Any]]:
        """Get agents that have been idle for specified time.

        Args:
            idle_minutes: Idle threshold in minutes.

        Returns:
            List of idle agent records.
        """
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM agents "
                "WHERE status != %s "
                "AND last_activity_at < NOW() - INTERVAL '%s minutes'",
                (AgentStatus.TERMINATED.value, idle_minutes),
            )
            return cursor.fetchall()


class ChatRepository:
    """Repository for chat history operations."""

    def __init__(self, db: DatabaseManager):
        """Initialize repository.

        Args:
            db: Database manager.
        """
        self.db = db

    def add_message(
        self,
        session_id: UUID,
        role: MessageRole,
        content: str,
        agent_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """Add message to chat history.

        Args:
            session_id: Session ID.
            role: Message role.
            content: Message content.
            agent_id: Optional agent ID.
            metadata: Optional metadata.

        Returns:
            Message ID.
        """
        metadata_json = json.dumps(metadata) if metadata else None

        with self.db.get_cursor() as cursor:
            cursor.execute(
                "INSERT INTO chat_history (session_id, agent_id, role, content, metadata) "
                "VALUES (%s, %s, %s, %s, %s) RETURNING id",
                (session_id, agent_id, role.value, content, metadata_json),
            )
            result = cursor.fetchone()
            return result["id"]

    def get_session_history(self, session_id: UUID, limit: int | None = None) -> list[dict[str, Any]]:
        """Get chat history for a session.

        Args:
            session_id: Session ID.
            limit: Optional limit on number of messages.

        Returns:
            List of chat messages.
        """
        with self.db.get_cursor() as cursor:
            query = "SELECT * FROM chat_history WHERE session_id = %s ORDER BY timestamp"
            if limit:
                query += f" LIMIT {limit}"

            cursor.execute(query, (session_id,))
            return cursor.fetchall()
