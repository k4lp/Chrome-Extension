"""State management system for agent and application state."""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import json
from pathlib import Path
from loguru import logger


class AgentState(str, Enum):
    """Agent execution states."""

    IDLE = "idle"
    PROCESSING = "processing"
    EXECUTING_ACTIONS = "executing_actions"
    EXECUTING_CODE = "executing_code"
    WAITING_FOR_USER = "waiting_for_user"
    ERROR = "error"


class ConversationRole(str, Enum):
    """Conversation message roles."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    ACTION_RESULT = "action_result"


@dataclass
class Message:
    """A conversation message."""

    role: ConversationRole
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """Create from dictionary."""
        return cls(
            role=ConversationRole(data["role"]),
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ActionHistory:
    """History of executed actions."""

    action_type: str
    parameters: Dict[str, Any]
    result: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    success: bool = True
    execution_time: float = 0.0
    retry_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "action_type": self.action_type,
            "parameters": self.parameters,
            "result": self.result,
            "timestamp": self.timestamp.isoformat(),
            "success": self.success,
            "execution_time": self.execution_time,
            "retry_count": self.retry_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ActionHistory":
        """Create from dictionary."""
        return cls(
            action_type=data["action_type"],
            parameters=data["parameters"],
            result=data["result"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            success=data.get("success", True),
            execution_time=data.get("execution_time", 0.0),
            retry_count=data.get("retry_count", 0),
        )


@dataclass
class AgentContext:
    """Current context for agent processing."""

    retrieved_notes: List[Dict[str, Any]] = field(default_factory=list)
    retrieved_tasks: List[Dict[str, Any]] = field(default_factory=list)
    retrieved_projects: List[Dict[str, Any]] = field(default_factory=list)
    retrieved_memories: List[Dict[str, Any]] = field(default_factory=list)
    active_note_id: Optional[int] = None
    active_task_id: Optional[int] = None
    active_project_id: Optional[int] = None
    last_action_results: List[Dict[str, Any]] = field(default_factory=list)
    custom_context: Dict[str, Any] = field(default_factory=dict)

    def clear(self):
        """Clear all context."""
        self.retrieved_notes.clear()
        self.retrieved_tasks.clear()
        self.retrieved_projects.clear()
        self.retrieved_memories.clear()
        self.active_note_id = None
        self.active_task_id = None
        self.active_project_id = None
        self.last_action_results.clear()
        self.custom_context.clear()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentContext":
        """Create from dictionary."""
        return cls(**data)


class StateManager:
    """Manages application and agent state with persistence."""

    def __init__(self, persist_dir: Optional[Path] = None):
        """Initialize state manager.

        Args:
            persist_dir: Directory for state persistence (None = no persistence)
        """
        self.persist_dir = persist_dir
        if persist_dir:
            persist_dir.mkdir(parents=True, exist_ok=True)

        # Agent state
        self._agent_state = AgentState.IDLE
        self._agent_state_message: str = ""

        # Conversation history
        self._conversation: List[Message] = []
        self._max_conversation_length = 100  # Keep last 100 messages

        # Action history
        self._action_history: List[ActionHistory] = []
        self._max_action_history = 500  # Keep last 500 actions

        # Agent context
        self._context = AgentContext()

        # Session metadata
        self._session_start = datetime.now()
        self._session_id = f"session_{self._session_start.strftime('%Y%m%d_%H%M%S')}"

        # Load persisted state if available
        self._load_state()

        logger.info(f"🔄 StateManager initialized (session: {self._session_id})")

    # Agent State Management
    def set_agent_state(self, state: AgentState, message: str = ""):
        """Set current agent state.

        Args:
            state: New agent state
            message: Optional state message
        """
        old_state = self._agent_state
        self._agent_state = state
        self._agent_state_message = message

        logger.info(f"🔄 Agent state changed: {old_state.value} → {state.value}")
        if message:
            logger.info(f"   Message: {message}")

        self._persist_state()

    def get_agent_state(self) -> tuple[AgentState, str]:
        """Get current agent state.

        Returns:
            Tuple of (state, message)
        """
        return self._agent_state, self._agent_state_message

    def is_busy(self) -> bool:
        """Check if agent is busy.

        Returns:
            True if agent is processing
        """
        return self._agent_state in [
            AgentState.PROCESSING,
            AgentState.EXECUTING_ACTIONS,
            AgentState.EXECUTING_CODE,
        ]

    # Conversation Management
    def add_message(
        self, role: ConversationRole, content: str, metadata: Optional[Dict[str, Any]] = None
    ):
        """Add message to conversation.

        Args:
            role: Message role
            content: Message content
            metadata: Optional metadata
        """
        message = Message(role=role, content=content, metadata=metadata or {})
        self._conversation.append(message)

        # Trim conversation if too long
        if len(self._conversation) > self._max_conversation_length:
            self._conversation = self._conversation[-self._max_conversation_length :]

        logger.debug(f"💬 Added {role.value} message ({len(content)} chars)")
        self._persist_state()

    def get_conversation(
        self, last_n: Optional[int] = None, role_filter: Optional[ConversationRole] = None
    ) -> List[Message]:
        """Get conversation history.

        Args:
            last_n: Get only last N messages
            role_filter: Filter by role

        Returns:
            List of messages
        """
        messages = self._conversation

        if role_filter:
            messages = [m for m in messages if m.role == role_filter]

        if last_n:
            messages = messages[-last_n:]

        return messages

    def clear_conversation(self):
        """Clear conversation history."""
        self._conversation.clear()
        logger.info("🗑️ Conversation history cleared")
        self._persist_state()

    # Action History Management
    def add_action_result(
        self,
        action_type: str,
        parameters: Dict[str, Any],
        result: Dict[str, Any],
        success: bool = True,
        execution_time: float = 0.0,
        retry_count: int = 0,
    ):
        """Record an action execution.

        Args:
            action_type: Type of action
            parameters: Action parameters
            result: Action result
            success: Whether action succeeded
            execution_time: Execution time in seconds
            retry_count: Number of retries
        """
        action = ActionHistory(
            action_type=action_type,
            parameters=parameters,
            result=result,
            success=success,
            execution_time=execution_time,
            retry_count=retry_count,
        )
        self._action_history.append(action)

        # Trim history if too long
        if len(self._action_history) > self._max_action_history:
            self._action_history = self._action_history[-self._max_action_history :]

        logger.debug(f"📋 Recorded {action_type} action (success={success})")
        self._persist_state()

    def get_action_history(
        self,
        last_n: Optional[int] = None,
        action_type_filter: Optional[str] = None,
        success_only: bool = False,
    ) -> List[ActionHistory]:
        """Get action history.

        Args:
            last_n: Get only last N actions
            action_type_filter: Filter by action type
            success_only: Only return successful actions

        Returns:
            List of action history
        """
        actions = self._action_history

        if action_type_filter:
            actions = [a for a in actions if a.action_type == action_type_filter]

        if success_only:
            actions = [a for a in actions if a.success]

        if last_n:
            actions = actions[-last_n:]

        return actions

    def get_action_stats(self) -> Dict[str, Any]:
        """Get action execution statistics.

        Returns:
            Statistics dictionary
        """
        if not self._action_history:
            return {
                "total_actions": 0,
                "successful_actions": 0,
                "failed_actions": 0,
                "success_rate": 0.0,
                "total_execution_time": 0.0,
                "average_execution_time": 0.0,
                "total_retries": 0,
            }

        successful = sum(1 for a in self._action_history if a.success)
        failed = len(self._action_history) - successful
        total_time = sum(a.execution_time for a in self._action_history)
        total_retries = sum(a.retry_count for a in self._action_history)

        return {
            "total_actions": len(self._action_history),
            "successful_actions": successful,
            "failed_actions": failed,
            "success_rate": (successful / len(self._action_history)) * 100,
            "total_execution_time": total_time,
            "average_execution_time": total_time / len(self._action_history),
            "total_retries": total_retries,
        }

    # Context Management
    def get_context(self) -> AgentContext:
        """Get current agent context.

        Returns:
            Agent context
        """
        return self._context

    def update_context(self, **kwargs):
        """Update agent context.

        Args:
            **kwargs: Context fields to update
        """
        for key, value in kwargs.items():
            if hasattr(self._context, key):
                setattr(self._context, key, value)
                logger.debug(f"🔄 Updated context.{key}")

        self._persist_state()

    def clear_context(self):
        """Clear agent context."""
        self._context.clear()
        logger.info("🗑️ Agent context cleared")
        self._persist_state()

    # Session Management
    def get_session_info(self) -> Dict[str, Any]:
        """Get session information.

        Returns:
            Session info dictionary
        """
        uptime = (datetime.now() - self._session_start).total_seconds()

        return {
            "session_id": self._session_id,
            "session_start": self._session_start.isoformat(),
            "uptime_seconds": uptime,
            "agent_state": self._agent_state.value,
            "conversation_length": len(self._conversation),
            "action_count": len(self._action_history),
            "persist_enabled": self.persist_dir is not None,
        }

    def reset_session(self):
        """Reset session (clear all state)."""
        logger.warning("🔄 Resetting session - clearing all state")

        self._agent_state = AgentState.IDLE
        self._agent_state_message = ""
        self._conversation.clear()
        self._action_history.clear()
        self._context.clear()

        self._session_start = datetime.now()
        self._session_id = f"session_{self._session_start.strftime('%Y%m%d_%H%M%S')}"

        self._persist_state()

    # Persistence
    def _persist_state(self):
        """Persist state to disk if enabled."""
        if not self.persist_dir:
            return

        try:
            state_file = self.persist_dir / f"{self._session_id}_state.json"

            state_data = {
                "session_id": self._session_id,
                "session_start": self._session_start.isoformat(),
                "agent_state": self._agent_state.value,
                "agent_state_message": self._agent_state_message,
                "conversation": [m.to_dict() for m in self._conversation],
                "action_history": [a.to_dict() for a in self._action_history],
                "context": self._context.to_dict(),
            }

            state_file.write_text(json.dumps(state_data, indent=2))

        except Exception as e:
            logger.error(f"Failed to persist state: {e}")

    def _load_state(self):
        """Load persisted state if available."""
        if not self.persist_dir:
            return

        try:
            state_file = self.persist_dir / f"{self._session_id}_state.json"

            if not state_file.exists():
                return

            state_data = json.loads(state_file.read_text())

            self._session_id = state_data["session_id"]
            self._session_start = datetime.fromisoformat(state_data["session_start"])
            self._agent_state = AgentState(state_data["agent_state"])
            self._agent_state_message = state_data.get("agent_state_message", "")

            self._conversation = [Message.from_dict(m) for m in state_data.get("conversation", [])]
            self._action_history = [
                ActionHistory.from_dict(a) for a in state_data.get("action_history", [])
            ]
            self._context = AgentContext.from_dict(state_data.get("context", {}))

            logger.info(f"✅ Loaded persisted state from {state_file}")

        except Exception as e:
            logger.warning(f"Failed to load persisted state: {e}")
