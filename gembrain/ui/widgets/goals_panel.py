"""Goals panel for managing goals."""

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
    QInputDialog,
)
from PyQt6.QtCore import Qt
from loguru import logger

from ...core.services import GoalService
from ...core.models import GoalStatus


class GoalsPanel(QWidget):
    """Panel for managing goals."""

    def __init__(self, db_session, settings):
        """Initialize goals panel.

        Args:
            db_session: Database session
            settings: Application settings
        """
        super().__init__()

        self.db_session = db_session
        self.settings = settings
        self.goal_service = GoalService(db_session)

        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        """Setup user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Title
        header = QHBoxLayout()
        title = QLabel("Goals")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        header.addWidget(title)

        header.addStretch()

        new_btn = QPushButton("+ New Goal")
        new_btn.clicked.connect(self._create_goal)
        header.addWidget(new_btn)

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.refresh)
        header.addWidget(refresh_btn)

        layout.addLayout(header)

        # Tabs for different goal views
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)

        # Pending tab
        self.pending_list = QListWidget()
        self.pending_list.itemDoubleClicked.connect(self._toggle_goal_status)
        self.tabs.addTab(self.pending_list, "Pending")

        # Completed tab
        self.completed_list = QListWidget()
        self.completed_list.itemDoubleClicked.connect(self._toggle_goal_status)
        self.tabs.addTab(self.completed_list, "Completed")

        # All tab
        self.all_list = QListWidget()
        self.all_list.itemDoubleClicked.connect(self._show_goal_details)
        self.tabs.addTab(self.all_list, "All")

        layout.addWidget(self.tabs)

        # Footer with stats
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("color: #666;")
        layout.addWidget(self.stats_label)

    def refresh(self):
        """Refresh all goal lists."""
        logger.info("Refreshing goals panel")

        # Clear all lists
        self.pending_list.clear()
        self.completed_list.clear()
        self.all_list.clear()

        # Get goals by status
        pending_goals = self.goal_service.get_all_goals(GoalStatus.PENDING)
        completed_goals = self.goal_service.get_all_goals(GoalStatus.COMPLETED)
        all_goals = self.goal_service.get_all_goals()

        # Populate pending list
        for goal in pending_goals:
            self._add_goal_to_list(self.pending_list, goal, "○")

        # Populate completed list
        for goal in completed_goals:
            self._add_goal_to_list(self.completed_list, goal, "✓")

        # Populate all list
        for goal in all_goals:
            icon = "✓" if goal.status == GoalStatus.COMPLETED else "○"
            self._add_goal_to_list(self.all_list, goal, icon)

        # Update stats
        self.stats_label.setText(
            f"{len(pending_goals)} pending • {len(completed_goals)} completed • {len(all_goals)} total"
        )

        logger.info(f"Loaded {len(all_goals)} goals")

    def _add_goal_to_list(self, list_widget: QListWidget, goal, icon: str):
        """Add goal to list widget."""
        # Truncate content to 100 chars
        content_preview = goal.content[:100] + "..." if len(goal.content) > 100 else goal.content

        # Add notes preview if present
        notes_str = f" ({goal.notes[:30]}...)" if goal.notes else ""

        item_text = f"{icon} {content_preview}{notes_str}"
        item = QListWidgetItem(item_text)
        item.setData(Qt.ItemDataRole.UserRole, goal.id)
        list_widget.addItem(item)

    def _create_goal(self):
        """Create a new goal."""
        content, ok = QInputDialog.getText(
            self, "New Goal", "Goal description (what needs to be achieved):"
        )

        if ok and content:
            try:
                goal = self.goal_service.create_goal(
                    content=content,
                    notes="",
                    status=GoalStatus.PENDING,
                )
                logger.info(f"Created goal: {goal.id}")
                QMessageBox.information(self, "Success", "Goal created successfully!")
                self.refresh()
            except Exception as e:
                logger.error(f"Failed to create goal: {e}")
                QMessageBox.critical(self, "Error", f"Failed to create goal: {e}")

    def _toggle_goal_status(self, item: QListWidgetItem):
        """Toggle goal status between pending and completed."""
        goal_id = item.data(Qt.ItemDataRole.UserRole)
        goal = self.goal_service.get_goal(goal_id)

        if not goal:
            return

        # Toggle status
        new_status = (
            GoalStatus.COMPLETED if goal.status == GoalStatus.PENDING else GoalStatus.PENDING
        )

        try:
            self.goal_service.update_goal(goal_id, status=new_status)
            logger.info(f"Updated goal {goal_id} status to {new_status}")
            self.refresh()
        except Exception as e:
            logger.error(f"Failed to update goal: {e}")
            QMessageBox.critical(self, "Error", f"Failed to update goal: {e}")

    def _show_goal_details(self, item: QListWidgetItem):
        """Show goal details in a dialog."""
        goal_id = item.data(Qt.ItemDataRole.UserRole)
        goal = self.goal_service.get_goal(goal_id)

        if not goal:
            return

        status_text = "Completed" if goal.status == GoalStatus.COMPLETED else "Pending"

        details = f"""
<h3>Goal Details</h3>
<p><b>Status:</b> {status_text}</p>
<p><b>Content:</b><br>{goal.content}</p>
{f'<p><b>Notes:</b><br>{goal.notes}</p>' if goal.notes else ''}
<p><b>Created:</b> {goal.created_at.strftime('%Y-%m-%d %H:%M')}</p>
<p><b>Updated:</b> {goal.updated_at.strftime('%Y-%m-%d %H:%M')}</p>
"""

        msg = QMessageBox(self)
        msg.setWindowTitle("Goal Details")
        msg.setText(details)
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.exec()
