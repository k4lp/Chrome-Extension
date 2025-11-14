"""Tasks panel for managing tasks."""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QLabel,
    QTabWidget,
    QMessageBox,
)
from PyQt6.QtCore import Qt
from loguru import logger

from ...core.services import TaskService
from ...core.models import TaskStatus


class TasksPanel(QWidget):
    """Panel for managing tasks."""

    def __init__(self, db_session, settings):
        """Initialize tasks panel.

        Args:
            db_session: Database session
            settings: Application settings
        """
        super().__init__()

        self.db_session = db_session
        self.settings = settings
        self.task_service = TaskService(db_session)

        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        """Setup user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Title
        header = QHBoxLayout()
        title = QLabel("Tasks")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        header.addWidget(title)

        header.addStretch()

        delete_all_btn = QPushButton("Delete All Tasks")
        delete_all_btn.clicked.connect(self._delete_all_tasks)
        delete_all_btn.setStyleSheet("background-color: #d32f2f; color: white;")
        header.addWidget(delete_all_btn)

        new_btn = QPushButton("+ New Task")
        new_btn.clicked.connect(self._create_task)
        header.addWidget(new_btn)

        layout.addLayout(header)

        # Tabs for different task views
        self.tabs = QTabWidget()

        self.pending_list = self._create_task_list()
        self.tabs.addTab(self.pending_list, "Pending")

        self.ongoing_list = self._create_task_list()
        self.tabs.addTab(self.ongoing_list, "Ongoing")

        self.completed_list = self._create_task_list()
        self.tabs.addTab(self.completed_list, "Completed")

        layout.addWidget(self.tabs)

        # Task lists context menus
        for task_list in [self.pending_list, self.ongoing_list, self.completed_list]:
            task_list.itemDoubleClicked.connect(self._toggle_task_status)

    def _create_task_list(self) -> QListWidget:
        """Create a task list widget.

        Returns:
            QListWidget
        """
        task_list = QListWidget()
        task_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        return task_list

    def refresh(self):
        """Refresh all task lists."""
        self._refresh_list(self.pending_list, TaskStatus.PENDING)
        self._refresh_list(self.ongoing_list, TaskStatus.ONGOING)
        self._refresh_list(self.completed_list, TaskStatus.COMPLETED)

    def _refresh_list(self, list_widget: QListWidget, status: TaskStatus):
        """Refresh a specific task list.

        Args:
            list_widget: List widget to refresh
            status: Task status to filter by
        """
        list_widget.clear()
        tasks = self.task_service.get_tasks_by_status(status)

        for task in tasks:
            # Truncate content to 100 characters for display
            content_preview = task.content[:100] + "..." if len(task.content) > 100 else task.content
            notes_str = f" ({task.notes[:30]}...)" if task.notes else ""
            text = f"{content_preview}{notes_str}"

            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, task.id)
            list_widget.addItem(item)

    def _create_task(self):
        """Create new task."""
        from PyQt6.QtWidgets import QInputDialog

        content, ok = QInputDialog.getText(self, "New Task", "Task content:")

        if ok and content:
            self.task_service.create_task(content)
            self.refresh()
            logger.info(f"Created task: {content[:50]}...")

    def _toggle_task_status(self, item: QListWidgetItem):
        """Toggle task status.

        Args:
            item: List item
        """
        task_id = item.data(Qt.ItemDataRole.UserRole)
        task = self.task_service.get_task(task_id)

        if not task:
            return

        # Cycle through statuses: pending → ongoing → completed → pending
        if task.status == TaskStatus.PENDING:
            new_status = TaskStatus.ONGOING
        elif task.status == TaskStatus.ONGOING:
            new_status = TaskStatus.COMPLETED
        else:
            new_status = TaskStatus.PENDING

        self.task_service.update_task(task_id, status=new_status)
        self.refresh()
        logger.info(f"Updated task {task_id} status to {new_status}")

    def _delete_all_tasks(self):
        """Delete all tasks with confirmation."""
        # Get count of tasks
        all_tasks = self.task_service.get_all_tasks()
        task_count = len(all_tasks)

        if task_count == 0:
            QMessageBox.information(self, "No Tasks", "There are no tasks to delete.")
            return

        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Confirm Delete All",
            f"Are you sure you want to delete all {task_count} tasks?\n\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                deleted_count = self.task_service.delete_all_tasks()
                QMessageBox.information(
                    self,
                    "Success",
                    f"Successfully deleted {deleted_count} tasks."
                )
                self.refresh()
                logger.info(f"Deleted all {deleted_count} tasks via UI")
            except Exception as e:
                logger.error(f"Failed to delete all tasks: {e}")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to delete tasks: {e}"
                )
