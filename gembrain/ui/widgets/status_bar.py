"""Custom status bar."""

from PyQt6.QtWidgets import QStatusBar, QLabel
from PyQt6.QtCore import Qt


class CustomStatusBar(QStatusBar):
    """Custom status bar with additional information."""

    def __init__(self, settings):
        """Initialize status bar.

        Args:
            settings: Application settings
        """
        super().__init__()

        self.settings = settings

        # Model label
        self.model_label = QLabel()
        self.addPermanentWidget(self.model_label)
        self._update_model_label()

        # Panel label
        self.panel_label = QLabel("Chat")
        self.addPermanentWidget(self.panel_label)

        self.showMessage("Ready")

    def _update_model_label(self):
        """Update model label."""
        model = self.settings.api.default_model
        self.model_label.setText(f"Model: {model}")

    def set_panel_name(self, name: str):
        """Set current panel name.

        Args:
            name: Panel name
        """
        self.panel_label.setText(name)

    def set_status(self, message: str, timeout: int = 0):
        """Set status message.

        Args:
            message: Status message
            timeout: Timeout in milliseconds (0 = permanent)
        """
        self.showMessage(message, timeout)
