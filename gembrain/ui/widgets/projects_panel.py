"""Projects panel for managing projects."""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QLabel,
    QTextEdit,
    QInputDialog,
)
from PyQt6.QtCore import Qt
from loguru import logger

from ...core.services import ProjectService


class ProjectsPanel(QWidget):
    """Panel for managing projects."""

    def __init__(self, db_session, settings):
        """Initialize projects panel.

        Args:
            db_session: Database session
            settings: Application settings
        """
        super().__init__()

        self.db_session = db_session
        self.settings = settings
        self.project_service = ProjectService(db_session)

        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        """Setup user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Title
        header = QHBoxLayout()
        title = QLabel("Projects")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        header.addWidget(title)

        header.addStretch()

        new_btn = QPushButton("+ New Project")
        new_btn.clicked.connect(self._create_project)
        header.addWidget(new_btn)

        layout.addLayout(header)

        # Projects list
        self.projects_list = QListWidget()
        self.projects_list.currentItemChanged.connect(self._on_project_selected)
        layout.addWidget(self.projects_list)

        # Project details
        self.details = QTextEdit()
        self.details.setReadOnly(True)
        self.details.setMaximumHeight(200)
        layout.addWidget(self.details)

    def refresh(self):
        """Refresh projects list."""
        self.projects_list.clear()
        projects = self.project_service.get_all_projects()

        for project in projects:
            item = QListWidgetItem(f"{project.name} ({project.status.value})")
            item.setData(Qt.ItemDataRole.UserRole, project.id)
            self.projects_list.addItem(item)

    def _on_project_selected(self, current, previous):
        """Handle project selection."""
        if not current:
            return

        project_id = current.data(Qt.ItemDataRole.UserRole)
        summary = self.project_service.get_project_summary(project_id)

        if summary:
            details_text = f"""
<h3>{summary['project'].name}</h3>
<p><b>Status:</b> {summary['project'].status.value}</p>
<p><b>Description:</b> {summary['project'].description or 'No description'}</p>
<p><b>Tasks:</b> {summary['total_tasks']} total, {summary['completed_tasks']} completed, {summary['active_tasks']} active</p>
            """
            self.details.setHtml(details_text)

    def _create_project(self):
        """Create new project."""
        name, ok = QInputDialog.getText(self, "New Project", "Project name:")

        if ok and name:
            self.project_service.create_project(name)
            self.refresh()
            logger.info(f"Created project: {name}")
