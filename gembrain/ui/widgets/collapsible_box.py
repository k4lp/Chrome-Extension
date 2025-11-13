"""Collapsible box widget for organizing content sections."""

from PyQt6.QtWidgets import QWidget, QToolButton, QVBoxLayout, QFrame, QSizePolicy
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtSignal
from PyQt6.QtGui import QFont


class CollapsibleBox(QWidget):
    """A collapsible box widget with a toggle button and content area."""

    toggled = pyqtSignal(bool)

    def __init__(self, title: str = "", parent=None):
        """Initialize collapsible box.

        Args:
            title: Title text for the toggle button
            parent: Parent widget
        """
        super().__init__(parent)

        self.toggle_button = QToolButton()
        self.toggle_button.setStyleSheet(
            """
            QToolButton {
                border: none;
                background: transparent;
                font-weight: bold;
                font-size: 13px;
                padding: 4px;
                text-align: left;
            }
            QToolButton:hover {
                background: rgba(0, 0, 0, 0.05);
            }
            """
        )
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.toggle_button.setArrowType(Qt.ArrowType.RightArrow)
        self.toggle_button.setText(title)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(False)

        self.content_area = QFrame()
        self.content_area.setStyleSheet(
            """
            QFrame {
                border: 1px solid #ccc;
                border-radius: 4px;
                background: white;
                padding: 8px;
                margin-left: 20px;
            }
            """
        )
        self.content_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.content_area.setMaximumHeight(0)
        self.content_area.setMinimumHeight(0)

        self.toggle_animation = QPropertyAnimation(self.content_area, b"maximumHeight")
        self.toggle_animation.setDuration(200)
        self.toggle_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)

        # Layout
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 4)
        layout.addWidget(self.toggle_button)
        layout.addWidget(self.content_area)

        # Content layout inside frame
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(8, 8, 8, 8)
        self.content_layout.setSpacing(4)

        # Connect
        self.toggle_button.clicked.connect(self.toggle)

    def toggle(self):
        """Toggle the collapsible section."""
        checked = self.toggle_button.isChecked()
        arrow_type = Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow
        self.toggle_button.setArrowType(arrow_type)

        if checked:
            content_height = self.content_area.sizeHint().height()
            self.toggle_animation.setStartValue(0)
            self.toggle_animation.setEndValue(content_height)
        else:
            self.toggle_animation.setStartValue(self.content_area.maximumHeight())
            self.toggle_animation.setEndValue(0)

        self.toggle_animation.start()
        self.toggled.emit(checked)

    def set_expanded(self, expanded: bool):
        """Set expansion state without animation.

        Args:
            expanded: True to expand, False to collapse
        """
        self.toggle_button.setChecked(expanded)
        arrow_type = Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow
        self.toggle_button.setArrowType(arrow_type)

        if expanded:
            self.content_area.setMaximumHeight(16777215)  # Max height
        else:
            self.content_area.setMaximumHeight(0)

    def add_widget(self, widget: QWidget):
        """Add a widget to the content area.

        Args:
            widget: Widget to add
        """
        self.content_layout.addWidget(widget)

    def clear_content(self):
        """Clear all widgets from content area."""
        while self.content_layout.count():
            child = self.content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
