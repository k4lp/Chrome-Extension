"""Main application window."""

import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QListWidget,
    QStackedWidget,
    QLabel,
    QPushButton,
    QMessageBox,
    QInputDialog,
)
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal
from PyQt6.QtGui import QAction
from loguru import logger

from .widgets.chat_panel import ChatPanel
from .widgets.tasks_panel import TasksPanel
from .widgets.goals_panel import GoalsPanel
from .widgets.memory_panel import MemoryPanel
from .widgets.datavault_panel import DatavaultPanel
from .widgets.context_panel import ContextPanel
from .widgets.status_bar import CustomStatusBar
from .widgets.settings_dialog import SettingsDialog
from ..automation.engine import AutomationEngine


class TestRunnerThread(QThread):
    """Background thread that runs pytest and records logs."""

    finished = pyqtSignal(bool, str)

    def __init__(self, workspace_path: Path, log_dir: Path):
        super().__init__()
        self.workspace_path = Path(workspace_path)
        self.log_dir = Path(log_dir)

    def run(self):
        """Execute pytest via subprocess and save the output to a log file."""
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_path = self.log_dir / f"test_run_{timestamp}.log"

            cmd = [sys.executable, "-m", "pytest", "-q"]
            logger.info(f"Running test suite via menu: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                cwd=str(self.workspace_path),
                capture_output=True,
                text=True,
            )

            log_contents = (
                f"Command: {' '.join(cmd)}\n"
                f"Return Code: {result.returncode}\n\n"
                f"--- STDOUT ---\n{result.stdout}\n"
                f"--- STDERR ---\n{result.stderr}\n"
            )
            log_path.write_text(log_contents, encoding="utf-8")

            self.finished.emit(result.returncode == 0, str(log_path))
        except Exception as exc:  # pragma: no cover - defensive UI logging
            logger.error(f"Test runner failed: {exc}")
            error_log = self.log_dir / "test_run_error.log"
            error_log.write_text(str(exc), encoding="utf-8")
            self.finished.emit(False, str(error_log))


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self, db_session, orchestrator, automation_engine, config_manager):
        """Initialize main window.

        Args:
            db_session: Database session
            orchestrator: Orchestrator instance
            automation_engine: Automation engine instance
            config_manager: Configuration manager
        """
        super().__init__()

        self.db_session = db_session
        self.orchestrator = orchestrator
        self.automation_engine = automation_engine
        self.config_manager = config_manager
        self.settings = config_manager.settings
        self._test_runner_thread: Optional[TestRunnerThread] = None

        self._setup_ui()
        self._setup_menu()
        self._apply_settings()

    def _setup_ui(self):
        """Setup user interface."""
        self.setWindowTitle("GemBrain - Second Brain")

        # Set window size from settings
        self.resize(
            self.settings.ui.window_width,
            self.settings.ui.window_height,
        )

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)

        # Main layout (3 columns)
        main_layout = QHBoxLayout(central)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # LEFT: Navigation sidebar
        self.nav_widget = self._create_nav_sidebar()
        main_layout.addWidget(self.nav_widget)

        # CENTER: Stacked panels
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack, stretch=3)

        # Create panels
        self.chat_panel = ChatPanel(self.db_session, self.orchestrator, self.settings)
        self.tasks_panel = TasksPanel(self.db_session, self.settings)
        self.goals_panel = GoalsPanel(self.db_session, self.settings)
        self.memory_panel = MemoryPanel(self.db_session, self.settings)
        self.datavault_panel = DatavaultPanel(self.db_session, self.settings)

        # Add panels to stack
        self.stack.addWidget(self.chat_panel)
        self.stack.addWidget(self.tasks_panel)
        self.stack.addWidget(self.goals_panel)
        self.stack.addWidget(self.memory_panel)
        self.stack.addWidget(self.datavault_panel)

        # RIGHT: Context panel
        if self.settings.ui.show_context_panel:
            self.context_panel = ContextPanel(self.db_session, self.settings)
            main_layout.addWidget(self.context_panel, stretch=1)
        else:
            self.context_panel = None

        # Status bar
        self.status_bar = CustomStatusBar(self.settings)
        self.setStatusBar(self.status_bar)

        # Connect navigation
        self.nav_list.currentRowChanged.connect(self._on_nav_changed)
        self.nav_list.setCurrentRow(0)  # Start with Chat

    def _create_nav_sidebar(self) -> QWidget:
        """Create navigation sidebar.

        Returns:
            Navigation widget
        """
        widget = QWidget()
        widget.setObjectName("navSidebar")
        widget.setMinimumWidth(180)
        widget.setMaximumWidth(200)

        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # App title
        title = QLabel("GemBrain")
        title.setObjectName("appTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold; padding: 20px;")
        layout.addWidget(title)

        # Navigation list
        self.nav_list = QListWidget()
        self.nav_list.setObjectName("navList")
        self.nav_list.addItem("💬 Chat")
        self.nav_list.addItem("✓ Tasks")
        self.nav_list.addItem("🎯 Goals")
        self.nav_list.addItem("🧠 Memory")
        self.nav_list.addItem("📦 Vault")
        layout.addWidget(self.nav_list)

        # Settings button at bottom
        settings_btn = QPushButton("⚙ Settings")
        settings_btn.setObjectName("settingsButton")
        settings_btn.clicked.connect(self._open_settings)
        layout.addWidget(settings_btn)

        return widget

    def _setup_menu(self):
        """Setup menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        backup_action = QAction("&Backup Database", self)
        backup_action.triggered.connect(self._backup_database)
        file_menu.addAction(backup_action)

        migrate_action = QAction("&Migrate to New Schema", self)
        migrate_action.triggered.connect(self._migrate_database)
        file_menu.addAction(migrate_action)

        file_menu.addSeparator()

        delete_all_action = QAction("🗑️ Delete &All Data...", self)
        delete_all_action.triggered.connect(self._delete_all_data)
        file_menu.addAction(delete_all_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Automation menu
        automation_menu = menubar.addMenu("&Automation")

        daily_review_action = QAction("Run &Daily Review", self)
        daily_review_action.triggered.connect(lambda: self._run_automation("daily_review"))
        automation_menu.addAction(daily_review_action)

        weekly_review_action = QAction("Run &Weekly Review", self)
        weekly_review_action.triggered.connect(lambda: self._run_automation("weekly_review"))
        automation_menu.addAction(weekly_review_action)

        resurface_action = QAction("&Resurface Notes", self)
        resurface_action.triggered.connect(lambda: self._run_automation("resurface_notes"))
        automation_menu.addAction(resurface_action)

        automation_menu.addSeparator()

        test_action = QAction("Run &Full Test Suite", self)
        test_action.triggered.connect(self._run_tests_from_menu)
        automation_menu.addAction(test_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _apply_settings(self):
        """Apply settings to UI."""
        # Font settings
        font = self.font()
        font.setFamily(self.settings.ui.font_family)
        font.setPointSize(self.settings.ui.font_size)
        self.setFont(font)

    def _on_nav_changed(self, index: int):
        """Handle navigation change.

        Args:
            index: Selected index
        """
        self.stack.setCurrentIndex(index)
        self.status_bar.set_panel_name(self.nav_list.currentItem().text())

        # Refresh context panel
        if self.context_panel:
            self.context_panel.refresh()

    def _open_settings(self):
        """Open settings dialog."""
        dialog = SettingsDialog(self.config_manager, self)
        if dialog.exec():
            # Settings were saved, apply changes
            self.settings = self.config_manager.settings

            # Reconfigure orchestrator
            self.orchestrator.reconfigure(self.settings)

            # Restart automation engine with new settings
            self.automation_engine.stop()
            self.automation_engine = AutomationEngine(
                self.db_session, self.orchestrator, self.settings
            )
            self.automation_engine.start()

            # Refresh UI
            self._apply_settings()
            QMessageBox.information(
                self,
                "Settings Applied",
                "Settings have been saved and applied successfully.",
            )

    def _backup_database(self):
        """Backup database."""
        try:
            from shutil import copy
            from datetime import datetime
            from pathlib import Path

            backup_dir = Path(self.settings.storage.backup_dir)
            backup_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"gembrain_backup_{timestamp}.db"

            copy(self.settings.storage.db_path, backup_path)

            QMessageBox.information(
                self,
                "Backup Complete",
                f"Database backed up to:\n{backup_path}",
            )
            logger.info(f"Database backed up to {backup_path}")

        except Exception as e:
            logger.error(f"Backup failed: {e}")
            QMessageBox.critical(
                self,
                "Backup Failed",
                f"Failed to backup database:\n{str(e)}",
            )

    def _migrate_database(self):
        """Migrate database to new schema."""
        # Show warning dialog
        warning = QMessageBox(self)
        warning.setIcon(QMessageBox.Icon.Warning)
        warning.setWindowTitle("Migrate to New Schema")
        warning.setText("⚠️ WARNING: This will DELETE ALL existing data!")
        warning.setInformativeText(
            "This migration will:\n\n"
            "1. Create a backup of your current database\n"
            "2. Drop all existing tables (Notes, Projects, old Tasks, etc.)\n"
            "3. Create new tables (Tasks, Memory, Goals, Datavault)\n"
            "4. Restart the application\n\n"
            "ALL YOUR CURRENT DATA WILL BE LOST!\n\n"
            "Do you want to proceed?"
        )
        warning.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        warning.setDefaultButton(QMessageBox.StandardButton.No)

        if warning.exec() != QMessageBox.StandardButton.Yes:
            return

        try:
            # Step 1: Create backup first
            from shutil import copy
            from datetime import datetime
            from pathlib import Path

            backup_dir = Path(self.settings.storage.backup_dir)
            backup_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"gembrain_pre_migration_{timestamp}.db"

            copy(self.settings.storage.db_path, backup_path)
            logger.info(f"Created pre-migration backup at {backup_path}")

            # Step 2: Close current database connection
            if self.db_session:
                self.db_session.close()

            from ..core.db import close_db, recreate_db
            close_db()

            # Step 3: Recreate database with new schema
            recreate_db(self.settings.storage.db_path)
            logger.info("Database migrated to new schema")

            # Step 4: Show success message
            QMessageBox.information(
                self,
                "Migration Complete",
                f"Database migrated successfully!\n\n"
                f"Backup saved to:\n{backup_path}\n\n"
                f"Please restart the application."
            )

            # Close the application so user can restart
            self.close()

        except Exception as e:
            logger.error(f"Migration failed: {e}")
            QMessageBox.critical(
                self,
                "Migration Failed",
                f"Failed to migrate database:\n{str(e)}\n\n"
                f"Your original database should still be intact."
            )

    def _delete_all_data(self):
        """Delete all data (Tasks, Goals, Memories, Datavault items)."""
        # Show strong warning dialog
        warning = QMessageBox(self)
        warning.setIcon(QMessageBox.Icon.Warning)
        warning.setWindowTitle("Delete All Data")
        warning.setText("⚠️ WARNING: This will DELETE ALL DATA!")
        warning.setInformativeText(
            "This action will permanently delete:\n\n"
            "• All Tasks (pending, ongoing, paused, completed)\n"
            "• All Goals (pending, completed)\n"
            "• All Memories\n"
            "• All Datavault items\n\n"
            "This action CANNOT BE UNDONE!\n\n"
            "Are you absolutely sure you want to proceed?"
        )
        warning.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        warning.setDefaultButton(QMessageBox.StandardButton.No)

        # Require confirmation
        if warning.exec() != QMessageBox.StandardButton.Yes:
            return

        # Double confirmation for safety
        confirm_text, ok = QInputDialog.getText(
            self,
            "Confirm Delete All",
            "Type 'DELETE ALL' to confirm (case-sensitive):",
        )

        if not ok or confirm_text != "DELETE ALL":
            QMessageBox.information(
                self,
                "Cancelled",
                "Delete all operation cancelled."
            )
            return

        try:
            from ..core.services import (
                TaskService,
                MemoryService,
                GoalService,
                DatavaultService,
            )

            # Initialize services
            task_service = TaskService(self.db_session)
            memory_service = MemoryService(self.db_session)
            goal_service = GoalService(self.db_session)
            datavault_service = DatavaultService(self.db_session)

            # Count items before deletion
            tasks_count = len(task_service.get_all_tasks())
            goals_count = len(goal_service.get_all_goals())
            memories_count = len(memory_service.get_all_memories())
            datavault_count = len(datavault_service.get_all_items())

            # Delete all tasks
            for task in task_service.get_all_tasks():
                task_service.delete_task(task.id)

            # Delete all goals
            for goal in goal_service.get_all_goals():
                goal_service.delete_goal(goal.id)

            # Delete all memories
            for memory in memory_service.get_all_memories():
                memory_service.delete_memory(memory.id)

            # Delete all datavault items
            for item in datavault_service.get_all_items():
                datavault_service.delete_item(item.id)

            logger.warning("=" * 80)
            logger.warning("DELETE ALL DATA - EXECUTED")
            logger.warning(f"Deleted {tasks_count} tasks")
            logger.warning(f"Deleted {goals_count} goals")
            logger.warning(f"Deleted {memories_count} memories")
            logger.warning(f"Deleted {datavault_count} datavault items")
            logger.warning("=" * 80)

            # Refresh all panels
            self.tasks_panel.refresh()
            self.goals_panel.refresh()
            self.memory_panel.refresh()
            self.datavault_panel.refresh()
            if self.context_panel:
                self.context_panel.refresh()

            QMessageBox.information(
                self,
                "Delete All Complete",
                f"Successfully deleted all data:\n\n"
                f"• {tasks_count} Tasks\n"
                f"• {goals_count} Goals\n"
                f"• {memories_count} Memories\n"
                f"• {datavault_count} Datavault items\n\n"
                f"All data has been permanently removed."
            )

        except Exception as e:
            logger.error(f"Delete all failed: {e}")
            QMessageBox.critical(
                self,
                "Delete All Failed",
                f"Failed to delete all data:\n{str(e)}"
            )

    def _run_automation(self, name: str):
        """Run automation manually.

        Args:
            name: Automation name
        """
        try:
            self.status_bar.set_status(f"Running {name}...")
            self.automation_engine.run_automation_now(name)
            self.status_bar.set_status(f"{name} completed", 5000)

            # Refresh panels
            if self.context_panel:
                self.context_panel.refresh()
            self.tasks_panel.refresh()
            self.goals_panel.refresh()
            self.memory_panel.refresh()
            self.datavault_panel.refresh()

            QMessageBox.information(
                self,
                "Automation Complete",
                f"{name} has been executed successfully.",
            )

        except Exception as e:
            logger.error(f"Automation {name} failed: {e}")
            QMessageBox.critical(
                self,
                "Automation Failed",
                f"Failed to run {name}:\n{str(e)}",
            )

    def _run_tests_from_menu(self):
        """Trigger the full pytest suite and capture logs for sharing."""
        if self._test_runner_thread and self._test_runner_thread.isRunning():
            QMessageBox.information(
                self,
                "Tests Already Running",
                "Please wait for the current test run to finish.",
            )
            return

        log_dir = Path(self.settings.storage.backup_dir).expanduser().resolve().parent / "test_logs"
        self._test_runner_thread = TestRunnerThread(Path.cwd(), log_dir)
        self._test_runner_thread.finished.connect(self._on_tests_finished)
        self.status_bar.set_status("Running test suite...", 0)
        self._test_runner_thread.start()

    def _on_tests_finished(self, success: bool, log_path: str):
        """Handle completion of the background test runner."""
        self.status_bar.set_status(
            "Test suite passed" if success else "Test suite failed", 10000
        )

        message = (
            f"All tests passed.\n\nLogs saved to:\n{log_path}"
            if success
            else f"Some tests failed.\n\nLogs saved to:\n{log_path}"
        )
        if success:
            QMessageBox.information(self, "Test Suite Complete", message)
        else:
            QMessageBox.warning(self, "Test Suite Failed", message)

        logger.info(f"Test suite finished (success={success}). Log file: {log_path}")
        self._test_runner_thread = None

    def _show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About GemBrain",
            "<h2>GemBrain</h2>"
            "<p>A Gemini-powered agentic second brain desktop application</p>"
            "<p>Version 0.1.0</p>"
            "<p>Built with PyQt6 and Google Gemini AI</p>"
            "<p><a href='https://github.com/yourusername/gembrain'>GitHub</a></p>",
        )

    def closeEvent(self, event):
        """Handle window close event."""
        logger.info("Main window closing")
        event.accept()
