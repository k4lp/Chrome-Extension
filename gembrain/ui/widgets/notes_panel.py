"""Notes panel for managing notes."""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QTextEdit,
    QLineEdit,
    QPushButton,
    QLabel,
    QSplitter,
    QMessageBox,
)
from PyQt6.QtCore import Qt
from loguru import logger

from ...core.services import NoteService


class NotesPanel(QWidget):
    """Panel for managing notes."""

    def __init__(self, db_session, settings):
        """Initialize notes panel.

        Args:
            db_session: Database session
            settings: Application settings
        """
        super().__init__()

        self.db_session = db_session
        self.settings = settings
        self.note_service = NoteService(db_session)
        self.current_note = None

        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        """Setup user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Title and search
        header = QHBoxLayout()
        title = QLabel("Notes")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        header.addWidget(title)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search notes...")
        self.search_box.textChanged.connect(self._on_search)
        header.addWidget(self.search_box)

        new_btn = QPushButton("+ New Note")
        new_btn.clicked.connect(self._create_note)
        header.addWidget(new_btn)

        layout.addLayout(header)

        # Splitter for list and editor
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Notes list
        self.notes_list = QListWidget()
        self.notes_list.currentItemChanged.connect(self._on_note_selected)
        splitter.addWidget(self.notes_list)

        # Editor area
        editor_widget = QWidget()
        editor_layout = QVBoxLayout(editor_widget)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Note title...")
        self.title_edit.setStyleSheet("font-size: 16px; font-weight: bold; padding: 8px;")
        editor_layout.addWidget(self.title_edit)

        self.content_edit = QTextEdit()
        self.content_edit.setPlaceholderText("Note content (markdown supported)...")
        editor_layout.addWidget(self.content_edit)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self._delete_note)
        button_layout.addWidget(self.delete_btn)

        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self._save_note)
        button_layout.addWidget(self.save_btn)

        editor_layout.addLayout(button_layout)
        splitter.addWidget(editor_widget)

        splitter.setSizes([300, 700])
        layout.addWidget(splitter)

    def refresh(self):
        """Refresh notes list."""
        self.notes_list.clear()
        notes = self.note_service.get_all_notes()

        for note in notes:
            item = QListWidgetItem(f"{note.title}")
            item.setData(Qt.ItemDataRole.UserRole, note.id)
            if note.pinned:
                item.setText(f"📌 {note.title}")
            self.notes_list.addItem(item)

    def _on_search(self, query: str):
        """Handle search query change."""
        if not query:
            self.refresh()
            return

        self.notes_list.clear()
        notes = self.note_service.search_notes(query)

        for note in notes:
            item = QListWidgetItem(f"{note.title}")
            item.setData(Qt.ItemDataRole.UserRole, note.id)
            self.notes_list.addItem(item)

    def _on_note_selected(self, current, previous):
        """Handle note selection."""
        if not current:
            return

        note_id = current.data(Qt.ItemDataRole.UserRole)
        self.current_note = self.note_service.get_note(note_id)

        if self.current_note:
            self.title_edit.setText(self.current_note.title)
            self.content_edit.setText(self.current_note.content)

    def _create_note(self):
        """Create new note."""
        note = self.note_service.create_note("Untitled Note", "")
        self.refresh()

        # Select new note
        for i in range(self.notes_list.count()):
            item = self.notes_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == note.id:
                self.notes_list.setCurrentItem(item)
                break

    def _save_note(self):
        """Save current note."""
        if not self.current_note:
            return

        title = self.title_edit.text().strip()
        content = self.content_edit.toPlainText()

        if not title:
            QMessageBox.warning(self, "Invalid Title", "Note title cannot be empty.")
            return

        self.note_service.update_note(
            self.current_note.id,
            title=title,
            content=content,
        )

        self.refresh()
        logger.info(f"Saved note: {title}")

    def _delete_note(self):
        """Delete current note."""
        if not self.current_note:
            return

        reply = QMessageBox.question(
            self,
            "Delete Note",
            f"Are you sure you want to delete '{self.current_note.title}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.note_service.delete_note(self.current_note.id)
            self.current_note = None
            self.title_edit.clear()
            self.content_edit.clear()
            self.refresh()
