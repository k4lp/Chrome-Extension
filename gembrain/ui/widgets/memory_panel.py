"""Memory panel for managing memories."""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QLabel,
    QMessageBox,
    QInputDialog,
    QTextEdit,
    QDialog,
    QDialogButtonBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor, QFont
from loguru import logger

from ...core.services import MemoryService


class MemoryPanel(QWidget):
    """Panel for managing memories."""

    def __init__(self, db_session, settings):
        """Initialize memory panel.

        Args:
            db_session: Database session
            settings: Application settings
        """
        super().__init__()

        self.db_session = db_session
        self.settings = settings
        self.memory_service = MemoryService(db_session)

        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        """Setup user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Title
        header = QHBoxLayout()
        title = QLabel("Memories")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        header.addWidget(title)

        header.addStretch()

        delete_all_btn = QPushButton("Delete All Memories")
        delete_all_btn.clicked.connect(self._delete_all_memories)
        delete_all_btn.setStyleSheet("background-color: #d32f2f; color: white;")
        header.addWidget(delete_all_btn)

        new_btn = QPushButton("+ New Memory")
        new_btn.clicked.connect(self._create_memory)
        header.addWidget(new_btn)

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.refresh)
        header.addWidget(refresh_btn)

        layout.addLayout(header)

        # Memories list
        self.memories_list = QListWidget()
        self.memories_list.itemDoubleClicked.connect(self._show_memory_details)
        layout.addWidget(self.memories_list)

        # Footer with stats
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("color: #666;")
        layout.addWidget(self.stats_label)

    def refresh(self):
        """Refresh memories list."""
        logger.info("Refreshing memory panel")

        # Clear list
        self.memories_list.clear()

        # Get all memories
        memories = self.memory_service.get_all_memories()

        # Populate list with color coding
        for memory in memories:
            self._add_memory_to_list(memory)

        # Update stats
        self.stats_label.setText(f"{len(memories)} memories stored")

        logger.info(f"Loaded {len(memories)} memories")

    def _add_memory_to_list(self, memory):
        """Add memory to list widget with color coding."""
        # Truncate content to 100 chars
        content_preview = memory.content[:100] + "..." if len(memory.content) > 100 else memory.content

        # Add notes preview if present
        notes_str = f" [{memory.notes[:30]}...]" if memory.notes else ""

        # Icon and color for memories
        icon = "🧠"
        bg_color = "#e8eaf6"  # Light indigo
        fg_color = "#3f51b5"  # Indigo

        item_text = f"{icon}  {content_preview}{notes_str}"
        item = QListWidgetItem(item_text)
        item.setData(Qt.ItemDataRole.UserRole, memory.id)

        # Set background color and text color
        item.setBackground(QBrush(QColor(bg_color)))
        item.setForeground(QBrush(QColor(fg_color)))

        # Make text slightly bold for better visibility
        font = QFont()
        font.setPointSize(10)
        item.setFont(font)

        self.memories_list.addItem(item)

    def _create_memory(self):
        """Create a new memory."""
        # Create dialog for memory input
        dialog = MemoryInputDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            content, notes = dialog.get_values()

            if content:
                try:
                    memory = self.memory_service.create_memory(
                        content=content,
                        notes=notes,
                    )
                    logger.info(f"Created memory: {memory.id}")
                    QMessageBox.information(self, "Success", "Memory created successfully!")
                    self.refresh()
                except Exception as e:
                    logger.error(f"Failed to create memory: {e}")
                    QMessageBox.critical(self, "Error", f"Failed to create memory: {e}")

    def _show_memory_details(self, item: QListWidgetItem):
        """Show memory details in a dialog."""
        memory_id = item.data(Qt.ItemDataRole.UserRole)
        memory = self.memory_service.get_memory(memory_id)

        if not memory:
            return

        # Create dialog
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Memory {memory.id}")
        dialog.setMinimumSize(600, 400)

        layout = QVBoxLayout(dialog)

        # Info
        info_text = f"""
<p><b>ID:</b> {memory.id}</p>
{f'<p><b>Notes:</b> {memory.notes}</p>' if memory.notes else ''}
<p><b>Created:</b> {memory.created_at.strftime('%Y-%m-%d %H:%M:%S')}</p>
<p><b>Updated:</b> {memory.updated_at.strftime('%Y-%m-%d %H:%M:%S')}</p>
"""
        info_label = QLabel(info_text)
        info_label.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(info_label)

        # Content
        content_label = QLabel("<b>Content:</b>")
        layout.addWidget(content_label)

        content_edit = QTextEdit()
        content_edit.setPlainText(memory.content)
        content_edit.setReadOnly(True)
        layout.addWidget(content_edit)

        # Buttons
        button_box = QDialogButtonBox()

        delete_btn = QPushButton("Delete")
        delete_btn.clicked.connect(lambda: self._delete_memory(memory.id, dialog))
        button_box.addButton(delete_btn, QDialogButtonBox.ButtonRole.RejectRole)

        close_btn = button_box.addButton(QDialogButtonBox.StandardButton.Close)
        close_btn.clicked.connect(dialog.accept)

        layout.addWidget(button_box)

        dialog.exec()

    def _delete_memory(self, memory_id: int, dialog: QDialog):
        """Delete memory."""
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete memory {memory_id}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                success = self.memory_service.delete_memory(memory_id)
                if success:
                    logger.info(f"Deleted memory: {memory_id}")
                    dialog.accept()
                    self.refresh()
                else:
                    QMessageBox.warning(self, "Error", "Failed to delete memory")
            except Exception as e:
                logger.error(f"Failed to delete memory: {e}")
                QMessageBox.critical(self, "Error", f"Failed to delete memory: {e}")

    def _delete_all_memories(self):
        """Delete all memories with confirmation."""
        # Get count of memories
        all_memories = self.memory_service.get_all_memories()
        memory_count = len(all_memories)

        if memory_count == 0:
            QMessageBox.information(self, "No Memories", "There are no memories to delete.")
            return

        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Confirm Delete All",
            f"Are you sure you want to delete all {memory_count} memories?\n\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                deleted_count = self.memory_service.delete_all_memories()
                QMessageBox.information(
                    self,
                    "Success",
                    f"Successfully deleted {deleted_count} memories."
                )
                self.refresh()
                logger.info(f"Deleted all {deleted_count} memories via UI")
            except Exception as e:
                logger.error(f"Failed to delete all memories: {e}")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to delete memories: {e}"
                )


class MemoryInputDialog(QDialog):
    """Dialog for creating a new memory."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("New Memory")
        self.setMinimumSize(500, 350)

        layout = QVBoxLayout(self)

        # Notes (optional tags/description)
        notes_layout = QHBoxLayout()
        notes_layout.addWidget(QLabel("Notes/Tags (optional):"))
        self.notes_edit = QLineEdit()
        self.notes_edit.setPlaceholderText("e.g., important, code-insight, reminder")
        notes_layout.addWidget(self.notes_edit)
        layout.addLayout(notes_layout)

        # Content
        layout.addWidget(QLabel("Memory Content:"))
        self.content_edit = QTextEdit()
        self.content_edit.setPlaceholderText("Enter the memory content here...")
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
            self.notes_edit.text(),
        )


# Need to import QLineEdit
from PyQt6.QtWidgets import QLineEdit
