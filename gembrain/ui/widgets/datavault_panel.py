"""Datavault panel for managing stored data."""

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
    QComboBox,
    QTextEdit,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
)
from PyQt6.QtCore import Qt
from loguru import logger

from gembrain.core.services import DatavaultService, ExportService


class DatavaultPanel(QWidget):
    """Panel for managing datavault items."""

    def __init__(self, db_session, settings):
        """Initialize datavault panel.

        Args:
            db_session: Database session
            settings: Application settings
        """
        super().__init__()

        self.db_session = db_session
        self.settings = settings
        self.datavault_service = DatavaultService(db_session)

        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        """Setup user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Title
        header = QHBoxLayout()
        title = QLabel("Data Vault")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        header.addWidget(title)

        header.addStretch()

        delete_all_btn = QPushButton("Delete All Items")
        delete_all_btn.clicked.connect(self._delete_all_items)
        delete_all_btn.setStyleSheet("background-color: #d32f2f; color: white;")
        header.addWidget(delete_all_btn)

        new_btn = QPushButton("+ Store Data")
        new_btn.clicked.connect(self._store_data)
        header.addWidget(new_btn)

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.refresh)
        header.addWidget(refresh_btn)

        layout.addLayout(header)

        # Filter by filetype
        filter_layout = QHBoxLayout()
        filter_label = QLabel("Filter by type:")
        filter_layout.addWidget(filter_label)

        self.filetype_filter = QComboBox()
        self.filetype_filter.addItems([
            "All",
            "text",
            "py",
            "js",
            "json",
            "md",
            "csv",
            "html",
            "xml",
        ])
        self.filetype_filter.currentTextChanged.connect(self.refresh)
        filter_layout.addWidget(self.filetype_filter)

        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # Items list
        self.items_list = QListWidget()
        self.items_list.itemDoubleClicked.connect(self._show_item_details)
        layout.addWidget(self.items_list)

        # Footer with stats
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("color: #666;")
        layout.addWidget(self.stats_label)

    def refresh(self):
        """Refresh datavault items list."""
        logger.info("Refreshing datavault panel")

        # Clear list
        self.items_list.clear()

        # Get filter
        filetype_filter = self.filetype_filter.currentText()
        if filetype_filter == "All":
            filetype_filter = None

        # Get items
        items = self.datavault_service.get_all_items(filetype=filetype_filter)

        # Populate list
        for item in items:
            # Icon based on filetype
            icon = self._get_filetype_icon(item.filetype)

            # Truncate content to 80 chars
            content_preview = item.content[:80].replace("\n", " ")
            if len(item.content) > 80:
                content_preview += "..."

            # Show notes if present
            notes_str = f" [{item.notes}]" if item.notes else ""

            # Size info
            size_kb = len(item.content) / 1024
            size_str = f"{size_kb:.1f}KB" if size_kb > 0 else f"{len(item.content)}B"

            item_text = f"{icon} {item.filetype} ({size_str}): {content_preview}{notes_str}"
            list_item = QListWidgetItem(item_text)
            list_item.setData(Qt.ItemDataRole.UserRole, item.id)
            self.items_list.addItem(list_item)

        # Update stats
        total_size = sum(len(item.content) for item in items)
        size_mb = total_size / (1024 * 1024)
        self.stats_label.setText(
            f"{len(items)} items • Total size: {size_mb:.2f} MB"
        )

        logger.info(f"Loaded {len(items)} datavault items")

    def _get_filetype_icon(self, filetype: str) -> str:
        """Get icon for filetype."""
        icons = {
            "text": "📄",
            "py": "🐍",
            "js": "📜",
            "json": "📋",
            "md": "📝",
            "csv": "📊",
            "html": "🌐",
            "xml": "📰",
        }
        return icons.get(filetype, "📦")

    def _store_data(self):
        """Store new data in datavault."""
        dialog = DatavaultStoreDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                content, filetype, notes = dialog.get_values()

                item = self.datavault_service.store_item(
                    content=content,
                    filetype=filetype,
                    notes=notes,
                )

                logger.info(f"Stored datavault item: {item.id}")
                QMessageBox.information(self, "Success", f"Data stored successfully! (ID: {item.id})")
                self.refresh()

            except Exception as e:
                logger.error(f"Failed to store data: {e}")
                QMessageBox.critical(self, "Error", f"Failed to store data: {e}")

    def _show_item_details(self, list_item: QListWidgetItem):
        """Show datavault item details in a dialog."""
        item_id = list_item.data(Qt.ItemDataRole.UserRole)
        item = self.datavault_service.get_item(item_id)

        if not item:
            return

        # Create dialog
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Datavault Item {item.id}")
        dialog.setMinimumSize(600, 500)

        layout = QVBoxLayout(dialog)

        # Info
        info_text = f"""
<p><b>ID:</b> {item.id}</p>
<p><b>Type:</b> {item.filetype}</p>
{f'<p><b>Notes:</b> {item.notes}</p>' if item.notes else ''}
<p><b>Size:</b> {len(item.content)} bytes ({len(item.content) / 1024:.1f} KB)</p>
<p><b>Created:</b> {item.created_at.strftime('%Y-%m-%d %H:%M:%S')}</p>
<p><b>Updated:</b> {item.updated_at.strftime('%Y-%m-%d %H:%M:%S')}</p>
"""
        info_label = QLabel(info_text)
        info_label.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(info_label)

        # Content
        content_label = QLabel("<b>Content:</b>")
        layout.addWidget(content_label)

        content_edit = QTextEdit()
        content_edit.setPlainText(item.content)
        content_edit.setReadOnly(True)
        layout.addWidget(content_edit)

        # Buttons
        button_box = QDialogButtonBox()

        export_btn = QPushButton("Export to File")
        export_btn.clicked.connect(lambda: self._export_item(item))
        button_box.addButton(export_btn, QDialogButtonBox.ButtonRole.ActionRole)

        delete_btn = QPushButton("Delete")
        delete_btn.clicked.connect(lambda: self._delete_item(item.id, dialog))
        button_box.addButton(delete_btn, QDialogButtonBox.ButtonRole.RejectRole)

        close_btn = button_box.addButton(QDialogButtonBox.StandardButton.Close)
        close_btn.clicked.connect(dialog.accept)

        layout.addWidget(button_box)

        dialog.exec()

    def _delete_item(self, item_id: int, dialog: QDialog):
        """Delete datavault item."""
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete datavault item {item_id}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                success = self.datavault_service.delete_item(item_id)
                if success:
                    logger.info(f"Deleted datavault item: {item_id}")
                    dialog.accept()
                    self.refresh()
                else:
                    QMessageBox.warning(self, "Error", "Failed to delete item")
            except Exception as e:
                logger.error(f"Failed to delete item: {e}")
                QMessageBox.critical(self, "Error", f"Failed to delete item: {e}")

    def _delete_all_items(self):
        """Delete all datavault items with confirmation."""
        # Get count of items
        all_items = self.datavault_service.get_all_items()
        item_count = len(all_items)

        if item_count == 0:
            QMessageBox.information(self, "No Items", "There are no datavault items to delete.")
            return

        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Confirm Delete All",
            f"Are you sure you want to delete all {item_count} datavault items?\n\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                deleted_count = self.datavault_service.delete_all_items()
                QMessageBox.information(
                    self,
                    "Success",
                    f"Successfully deleted {deleted_count} datavault items."
                )
                self.refresh()
                logger.info(f"Deleted all {deleted_count} datavault items via UI")
            except Exception as e:
                logger.error(f"Failed to delete all items: {e}")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to delete items: {e}"
                )

    def _export_item(self, item):
        """Export datavault item to file."""
        try:
            # Get suggested filename
            suggested_filename = ExportService.get_suggested_filename(item)

            # Open file dialog
            filepath, _ = QFileDialog.getSaveFileName(
                self,
                "Export Datavault Item",
                suggested_filename,
                f"{item.filetype.upper()} Files (*.{item.filetype});;All Files (*.*)"
            )

            if filepath:
                # Export the item
                success = ExportService.export_datavault_item(item, filepath)

                if success:
                    QMessageBox.information(
                        self,
                        "Success",
                        f"Successfully exported datavault item to:\n{filepath}"
                    )
                    logger.info(f"Exported datavault item {item.id} to {filepath}")
                else:
                    QMessageBox.warning(
                        self,
                        "Export Failed",
                        "Failed to export the item. Please check the logs for details."
                    )

        except Exception as e:
            logger.error(f"Failed to export item {item.id}: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to export item: {e}"
            )


class DatavaultStoreDialog(QDialog):
    """Dialog for storing data in datavault."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Store Data in Vault")
        self.setMinimumSize(500, 400)

        layout = QVBoxLayout(self)

        # Filetype
        filetype_layout = QHBoxLayout()
        filetype_layout.addWidget(QLabel("File Type:"))
        self.filetype_combo = QComboBox()
        self.filetype_combo.addItems(["text", "py", "js", "json", "md", "csv", "html", "xml"])
        filetype_layout.addWidget(self.filetype_combo)
        filetype_layout.addStretch()
        layout.addLayout(filetype_layout)

        # Notes
        notes_layout = QHBoxLayout()
        notes_layout.addWidget(QLabel("Notes (optional):"))
        self.notes_input = QInputDialog.getText
        self.notes_edit = QLineEdit()
        self.notes_edit.setPlaceholderText("Brief description or tags")
        notes_layout.addWidget(self.notes_edit)
        layout.addLayout(notes_layout)

        # Content
        layout.addWidget(QLabel("Content:"))
        self.content_edit = QTextEdit()
        self.content_edit.setPlaceholderText("Enter or paste your data here...")
        layout.addWidget(self.content_edit)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_values(self):
        """Get dialog values."""
        return (
            self.content_edit.toPlainText(),
            self.filetype_combo.currentText(),
            self.notes_edit.text(),
        )


# Need to import QLineEdit for notes edit
from PyQt6.QtWidgets import QLineEdit
