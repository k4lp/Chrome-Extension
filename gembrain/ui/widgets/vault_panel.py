"""Vault panel for managing stored items."""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QLabel,
)
from PyQt6.QtCore import Qt
from loguru import logger

from ...core.services import VaultService


class VaultPanel(QWidget):
    """Panel for managing vault items."""

    def __init__(self, db_session, settings):
        """Initialize vault panel.

        Args:
            db_session: Database session
            settings: Application settings
        """
        super().__init__()

        self.db_session = db_session
        self.settings = settings
        self.vault_service = VaultService(db_session)

        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        """Setup user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Title
        header = QHBoxLayout()
        title = QLabel("Vault")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        header.addWidget(title)

        header.addStretch()

        new_btn = QPushButton("+ Add Item")
        new_btn.clicked.connect(self._add_item)
        header.addWidget(new_btn)

        layout.addLayout(header)

        # Vault items list
        self.vault_list = QListWidget()
        self.vault_list.itemDoubleClicked.connect(self._open_item)
        layout.addWidget(self.vault_list)

    def refresh(self):
        """Refresh vault list."""
        self.vault_list.clear()
        items = self.vault_service.get_all_items()

        for item in items:
            icon = self._get_icon(item.type.value)
            list_item = QListWidgetItem(f"{icon} {item.title}")
            list_item.setData(Qt.ItemDataRole.UserRole, item.id)
            self.vault_list.addItem(list_item)

    def _get_icon(self, item_type: str) -> str:
        """Get icon for item type."""
        icons = {
            "file": "📄",
            "url": "🔗",
            "snippet": "✂️",
            "other": "📦",
        }
        return icons.get(item_type, "📦")

    def _add_item(self):
        """Add new vault item."""
        from PyQt6.QtWidgets import QInputDialog

        title, ok = QInputDialog.getText(self, "Add Item", "Item title:")

        if ok and title:
            from ...core.models import VaultItemType

            self.vault_service.add_item(title, VaultItemType.OTHER, "")
            self.refresh()
            logger.info(f"Added vault item: {title}")

    def _open_item(self, item: QListWidgetItem):
        """Open vault item.

        Args:
            item: List item
        """
        item_id = item.data(Qt.ItemDataRole.UserRole)
        vault_item = self.vault_service.get_item(item_id)

        if vault_item and vault_item.path_or_url:
            from PyQt6.QtGui import QDesktopServices
            from PyQt6.QtCore import QUrl

            QDesktopServices.openUrl(QUrl(vault_item.path_or_url))
