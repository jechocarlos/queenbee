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
    CLASSIFIER = "classifier"
    DIVERGENT = "divergent"
    CONVERGENT = "convergent"
    CRITICAL = "critical"
    PRAGMATIST = "pragmatist"
    USER_PROXY = "user_proxy"
    QUANTIFIER = "quantifier"
    SUMMARIZER = "summarizer"
    WEB_SEARCHER = "web_searcher"


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
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute(
                    "UPDATE agents SET status = %s WHERE id = %s",
                    (status.value, agent_id),
                )
                logger.debug(f"Updated agent {agent_id} status to {status.value}")
        except Exception as e:
            # Log but don't crash if we can't update status (e.g., connection closed during shutdown)
            logger.warning(f"Could not update agent {agent_id} status to {status.value}: {e}")

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


class TaskRepository:
    """Repository for task operations."""

    def __init__(self, db: DatabaseManager):
        """Initialize repository.

        Args:
            db: Database manager.
        """
        self.db = db

    def create_task(
        self,
        session_id: UUID,
        assigned_by: UUID,
        assigned_to: list[UUID],
        description: str,
    ) -> UUID:
        """Create a new task.

        Args:
            session_id: Session ID.
            assigned_by: Agent ID that created the task (usually Queen).
            assigned_to: List of agent IDs assigned to work on this task.
            description: Task description.

        Returns:
            Task ID.
        """
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "INSERT INTO tasks (session_id, assigned_by, assigned_to, description, status) "
                "VALUES (%s, %s, %s, %s, %s) RETURNING id",
                (session_id, assigned_by, assigned_to, description, TaskStatus.PENDING.value),
            )
            result = cursor.fetchone()
            return result["id"]

    def get_task(self, task_id: UUID) -> dict[str, Any] | None:
        """Get task by ID.

        Args:
            task_id: Task ID.

        Returns:
            Task data or None if not found.
        """
        with self.db.get_cursor() as cursor:
            cursor.execute("SELECT * FROM tasks WHERE id = %s", (task_id,))
            return cursor.fetchone()

    def get_pending_tasks(self, session_id: UUID | None = None) -> list[dict[str, Any]]:
        """Get pending tasks.

        Args:
            session_id: Optional session ID filter.

        Returns:
            List of pending tasks.
        """
        with self.db.get_cursor() as cursor:
            if session_id:
                cursor.execute(
                    "SELECT * FROM tasks WHERE status = %s AND session_id = %s ORDER BY created_at",
                    (TaskStatus.PENDING.value, session_id),
                )
            else:
                cursor.execute(
                    "SELECT * FROM tasks WHERE status = %s ORDER BY created_at",
                    (TaskStatus.PENDING.value,),
                )
            return cursor.fetchall()

    def update_task_status(self, task_id: UUID, status: TaskStatus) -> None:
        """Update task status.

        Args:
            task_id: Task ID.
            status: New status.
        """
        with self.db.get_cursor() as cursor:
            if status == TaskStatus.COMPLETED:
                cursor.execute(
                    "UPDATE tasks SET status = %s, completed_at = NOW() WHERE id = %s",
                    (status.value, task_id),
                )
            else:
                cursor.execute(
                    "UPDATE tasks SET status = %s WHERE id = %s",
                    (status.value, task_id),
                )

    def set_task_result(self, task_id: UUID, result: str) -> None:
        """Set task result.

        Args:
            task_id: Task ID.
            result: Task result (typically JSON string).
        """
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "UPDATE tasks SET result = %s WHERE id = %s",
                (result, task_id),
            )

    def get_session_tasks(self, session_id: UUID) -> list[dict[str, Any]]:
        """Get all tasks for a session.

        Args:
            session_id: Session ID.

        Returns:
            List of tasks.
        """
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM tasks WHERE session_id = %s ORDER BY created_at DESC",
                (session_id,),
            )
            return cursor.fetchall()


class RateLimitRepository:
    """Repository for provider rate limit data access."""

    def __init__(self, db: DatabaseManager):
        """Initialize rate limit repository.

        Args:
            db: Database manager.
        """
        self.db = db

    def get_rate_limit_reset(self, provider: str, model: str) -> int | None:
        """Get rate limit reset timestamp for a provider/model.

        Args:
            provider: Provider name (e.g., 'openrouter').
            model: Model name.

        Returns:
            Unix timestamp in milliseconds, or None if not found.
        """
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "SELECT rate_limit_reset FROM provider_rate_limits WHERE provider = %s AND model = %s",
                (provider, model),
            )
            result = cursor.fetchone()
            return result["rate_limit_reset"] if result else None

    def set_rate_limit_reset(
        self,
        provider: str,
        model: str,
        reset_timestamp_ms: int,
        remaining: int | None = None,
        limit: int | None = None,
    ) -> None:
        """Set rate limit reset timestamp for a provider/model.

        Args:
            provider: Provider name (e.g., 'openrouter').
            model: Model name.
            reset_timestamp_ms: Unix timestamp in milliseconds when rate limit resets.
            remaining: Remaining requests (optional).
            limit: Total request limit (optional).
        """
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO provider_rate_limits (provider, model, rate_limit_reset, rate_limit_remaining, rate_limit_limit, updated_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
                ON CONFLICT (provider, model) 
                DO UPDATE SET 
                    rate_limit_reset = EXCLUDED.rate_limit_reset,
                    rate_limit_remaining = EXCLUDED.rate_limit_remaining,
                    rate_limit_limit = EXCLUDED.rate_limit_limit,
                    updated_at = NOW()
                """,
                (provider, model, reset_timestamp_ms, remaining, limit),
            )

    def is_rate_limited(self, provider: str, model: str) -> bool:
        """Check if provider/model is currently rate limited.

        Args:
            provider: Provider name (e.g., 'openrouter').
            model: Model name.

        Returns:
            True if rate limited, False otherwise.
        """
        reset_ms = self.get_rate_limit_reset(provider, model)
        if reset_ms is None:
            return False
        
        import time
        current_time_ms = int(time.time() * 1000)
        return current_time_ms < reset_ms

    def clear_rate_limit(self, provider: str, model: str) -> None:
        """Clear rate limit for a provider/model.

        Args:
            provider: Provider name (e.g., 'openrouter').
            model: Model name.
        """
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "UPDATE provider_rate_limits SET rate_limit_reset = 0, updated_at = NOW() WHERE provider = %s AND model = %s",
                (provider, model),
            )
