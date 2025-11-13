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

from ...core.services import TaskService, NoteService
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
        self.note_service = NoteService(db_session)

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

        # Recent notes
        notes_label = QLabel("Recent Notes:")
        notes_label.setStyleSheet("font-weight: bold; margin-top: 8px;")
        layout.addWidget(notes_label)

        self.notes_list = QListWidget()
        self.notes_list.setMaximumHeight(200)
        layout.addWidget(self.notes_list)

        layout.addStretch()

    def refresh(self):
        """Refresh context panel."""
        # Refresh tasks
        self.tasks_list.clear()
        today_tasks = self.task_service.get_today_tasks()
        todo_tasks = self.task_service.get_tasks_by_status(TaskStatus.TODO)[:5]
        all_tasks = today_tasks + [t for t in todo_tasks if t not in today_tasks]

        for task in all_tasks[:10]:
            icon = "✓" if task.status == TaskStatus.DONE else "○"
            item = QListWidgetItem(f"{icon} {task.title}")
            self.tasks_list.addItem(item)

        if not all_tasks:
            item = QListWidgetItem("No tasks")
            item.setForeground(Qt.GlobalColor.gray)
            self.tasks_list.addItem(item)

        # Refresh notes
        self.notes_list.clear()
        recent_notes = self.note_service.get_recent_notes(5)

        for note in recent_notes:
            item = QListWidgetItem(note.title)
            self.notes_list.addItem(item)

        if not recent_notes:
            item = QListWidgetItem("No recent notes")
            item.setForeground(Qt.GlobalColor.gray)
            self.notes_list.addItem(item)
