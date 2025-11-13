"""Context panel showing relevant information."""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QFrame,
)
from PyQt6.QtCore import Qt
from loguru import logger

from ...core.services import TaskService, MemoryService
from ...core.models import TaskStatus


class ContextPanel(QWidget):
    """Panel showing contextual information."""

    def __init__(self, db_session, settings):
        """Initialize context panel.

        Args:
            db_session: Database session
            settings: Application settings
        """
        super().__init__()

        self.db_session = db_session
        self.settings = settings
        self.task_service = TaskService(db_session)
        self.memory_service = MemoryService(db_session)

        self._setup_ui()

    def _setup_ui(self):
        """Setup user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Title
        title = QLabel("Today")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        # Today's tasks
        tasks_label = QLabel("Tasks:")
        tasks_label.setStyleSheet("font-weight: bold; margin-top: 8px;")
        layout.addWidget(tasks_label)

        self.tasks_list = QListWidget()
        self.tasks_list.setMaximumHeight(200)
        layout.addWidget(self.tasks_list)

        # Recent memories
        memories_label = QLabel("Recent Memories:")
        memories_label.setStyleSheet("font-weight: bold; margin-top: 8px;")
        layout.addWidget(memories_label)

        self.memories_list = QListWidget()
        self.memories_list.setMaximumHeight(200)
        layout.addWidget(self.memories_list)

        layout.addStretch()

    def refresh(self):
        """Refresh context panel."""
        # Refresh tasks
        self.tasks_list.clear()
        today_tasks = self.task_service.get_today_tasks()
        pending_tasks = self.task_service.get_tasks_by_status(TaskStatus.PENDING)[:5]
        all_tasks = today_tasks + [t for t in pending_tasks if t not in today_tasks]

        for task in all_tasks[:10]:
            icon = "✓" if task.status == TaskStatus.COMPLETED else "○"
            # Truncate content to 50 characters
            content_preview = task.content[:50] + "..." if len(task.content) > 50 else task.content
            item = QListWidgetItem(f"{icon} {content_preview}")
            self.tasks_list.addItem(item)

        if not all_tasks:
            item = QListWidgetItem("No tasks")
            item.setForeground(Qt.GlobalColor.gray)
            self.tasks_list.addItem(item)

        # Refresh memories
        self.memories_list.clear()
        recent_memories = self.memory_service.get_all_memories(limit=5)

        for memory in recent_memories:
            # Truncate content to 60 characters
            content_preview = memory.content[:60] + "..." if len(memory.content) > 60 else memory.content
            item = QListWidgetItem(content_preview)
            self.memories_list.addItem(item)

        if not recent_memories:
            item = QListWidgetItem("No recent memories")
            item.setForeground(Qt.GlobalColor.gray)
            self.memories_list.addItem(item)
