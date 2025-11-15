"""Main PyQt6 application."""

import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt
from loguru import logger

# Ensure project root (containing the gembrain package) is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gembrain.config.manager import get_config_manager
from gembrain.core.db import init_db, get_db, close_db
from gembrain.agents.orchestrator import Orchestrator
from gembrain.automation.engine import AutomationEngine
from gembrain.utils.logging import setup_logging
from gembrain.ui.main_window import MainWindow


class GemBrainApp:
    """Main application class."""

    def __init__(self):
        """Initialize application."""
        # Load configuration
        self.config_manager = get_config_manager()
        self.settings = self.config_manager.load()

        # Setup logging
        setup_logging(self.config_manager.get_data_dir(), debug=False)
        logger.info("Starting GemBrain")

        # Ensure directories exist
        self.config_manager.ensure_directories()

        # Initialize database
        init_db(self.settings.storage.db_path, echo=False)
        logger.info("Database initialized")

        # Create Qt application
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("GemBrain")
        self.app.setOrganizationName("GemBrain")

        # Set application style
        self._apply_stylesheet()

        # Initialize core components
        self.db_session = None
        self.orchestrator = None
        self.automation_engine = None
        self.main_window = None

    def _apply_stylesheet(self):
        """Apply QSS stylesheet."""
        # Load stylesheet
        styles_dir = Path(__file__).parent / "styles"
        style_file = styles_dir / "base.qss"

        if style_file.exists():
            with open(style_file, "r") as f:
                self.app.setStyleSheet(f.read())
        else:
            logger.warning(f"Stylesheet not found: {style_file}")

    def run(self) -> int:
        """Run the application.

        Returns:
            Exit code
        """
        try:
            # Get database session
            self.db_session = next(get_db())

            # Initialize orchestrator
            self.orchestrator = Orchestrator(self.db_session, self.settings)

            # Check if Gemini is configured
            if not self.orchestrator.is_configured():
                self._show_api_key_warning()

            # Initialize automation engine
            self.automation_engine = AutomationEngine(
                self.db_session, self.orchestrator, self.settings
            )
            self.automation_engine.start()
            logger.info("Automation engine started")

            # Create and show main window
            self.main_window = MainWindow(
                db_session=self.db_session,
                orchestrator=self.orchestrator,
                automation_engine=self.automation_engine,
                config_manager=self.config_manager,
            )
            self.main_window.show()

            # Run event loop
            exit_code = self.app.exec()

            # Cleanup
            self._cleanup()

            return exit_code

        except Exception as e:
            logger.error(f"Error running application: {e}")
            self._show_error("Application Error", str(e))
            self._cleanup()
            return 1

    def _cleanup(self):
        """Cleanup resources."""
        logger.info("Cleaning up")

        if self.automation_engine:
            self.automation_engine.stop()

        if self.db_session:
            self.db_session.close()

        close_db()
        logger.info("GemBrain stopped")

    def _show_api_key_warning(self):
        """Show warning about missing API key."""
        QMessageBox.warning(
            None,
            "Gemini API Key Required",
            "Gemini API key is not configured.\n\n"
            "Please go to Settings → Gemini and add your API key.\n\n"
            "You can get an API key from:\n"
            "https://makersuite.google.com/app/apikey",
        )

    def _show_error(self, title: str, message: str):
        """Show error dialog."""
        QMessageBox.critical(None, title, message)


def main():
    """Main entry point."""
    app = GemBrainApp()
    sys.exit(app.run())


if __name__ == "__main__":
    main()
