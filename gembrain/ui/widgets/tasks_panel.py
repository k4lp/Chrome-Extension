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

        new_btn = QPushButton("+ New Task")
        new_btn.clicked.connect(self._create_task)
        header.addWidget(new_btn)

        layout.addLayout(header)

        # Tabs for different task views
        self.tabs = QTabWidget()

        self.todo_list = self._create_task_list()
        self.tabs.addTab(self.todo_list, "To Do")

        self.doing_list = self._create_task_list()
        self.tabs.addTab(self.doing_list, "Doing")

        self.done_list = self._create_task_list()
        self.tabs.addTab(self.done_list, "Done")

        layout.addWidget(self.tabs)

        # Task lists context menus
        for task_list in [self.todo_list, self.doing_list, self.done_list]:
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
        self._refresh_list(self.todo_list, TaskStatus.TODO)
        self._refresh_list(self.doing_list, TaskStatus.DOING)
        self._refresh_list(self.done_list, TaskStatus.DONE)

    def _refresh_list(self, list_widget: QListWidget, status: TaskStatus):
        """Refresh a specific task list.

        Args:
            list_widget: List widget to refresh
            status: Task status to filter by
        """
        list_widget.clear()
        tasks = self.task_service.get_tasks_by_status(status)

        for task in tasks:
            due_str = f" - Due: {task.due_date.date()}" if task.due_date else ""
            project_str = f" [{task.project.name}]" if task.project else ""
            text = f"{task.title}{project_str}{due_str}"

            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, task.id)
            list_widget.addItem(item)

    def _create_task(self):
        """Create new task."""
        from PyQt6.QtWidgets import QInputDialog

        title, ok = QInputDialog.getText(self, "New Task", "Task title:")

        if ok and title:
            self.task_service.create_task(title)
            self.refresh()
            logger.info(f"Created task: {title}")

    def _toggle_task_status(self, item: QListWidgetItem):
        """Toggle task status.

        Args:
            item: List item
        """
        task_id = item.data(Qt.ItemDataRole.UserRole)
        task = self.task_service.get_task(task_id)

        if not task:
            return

        # Cycle through statuses
        if task.status == TaskStatus.TODO:
            new_status = TaskStatus.DOING
        elif task.status == TaskStatus.DOING:
            new_status = TaskStatus.DONE
        else:
            new_status = TaskStatus.TODO

        self.task_service.update_task(task_id, status=new_status)
        self.refresh()
        logger.info(f"Updated task {task_id} status to {new_status}")
