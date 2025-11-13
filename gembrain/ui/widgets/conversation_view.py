"""Conversation view widget - displays chat messages and final outputs only."""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLabel
from PyQt6.QtCore import Qt
from loguru import logger

try:
    import markdown
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False
    logger.warning("markdown library not available - install with: pip install markdown")


class ConversationView(QWidget):
    """Widget for displaying conversation messages (user, agent, system).

    Responsible for:
    - Showing user messages
    - Showing agent responses (final output only)
    - Showing system messages (welcome, action summaries)
    - Clean, focused conversation history

    Does NOT show:
    - Reasoning iterations
    - Code execution details
    - Low-level action logs
    """

    def __init__(self):
        """Initialize conversation view."""
        super().__init__()
        self._setup_ui()

    def _setup_ui(self):
        """Setup user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Title
        title = QLabel("Conversation")
        title.setStyleSheet("font-size: 16px; font-weight: bold; padding: 8px;")
        layout.addWidget(title)

        # Chat history text area
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_history.setPlaceholderText("Chat history will appear here...")
        layout.addWidget(self.chat_history)

    def _markdown_to_html(self, text: str) -> str:
        """Convert markdown text to HTML.

        Args:
            text: Markdown text

        Returns:
            HTML string
        """
        if MARKDOWN_AVAILABLE:
            try:
                return markdown.markdown(
                    text,
                    extensions=['fenced_code', 'tables', 'nl2br']
                )
            except Exception as e:
                logger.warning(f"Markdown conversion failed: {e}")
                return text.replace('\n', '<br>')
        else:
            # Fallback: simple newline to <br> conversion
            return text.replace('\n', '<br>')

    def append_user_message(self, text: str):
        """Append user message to conversation.

        Args:
            text: User's message text
        """
        self.chat_history.append(f"<b style='color: #0066cc;'>You:</b> {text}")
        self.chat_history.append("")
        logger.debug(f"ConversationView: Added user message")

    def append_agent_message(self, text: str):
        """Append agent response to conversation.

        Args:
            text: Agent's response text (final output only, in markdown format)
        """
        # Convert markdown to HTML
        html_content = self._markdown_to_html(text)

        # Add with header
        self.chat_history.append(f"<b style='color: #00aa00;'>GemBrain:</b>")
        self.chat_history.insertHtml(f"<div style='margin-left: 16px;'>{html_content}</div>")
        self.chat_history.append("")
        logger.debug(f"ConversationView: Added agent message (markdown rendered)")

    def append_system_message(self, text: str):
        """Append system message to conversation.

        Args:
            text: System message text (welcome, summaries, etc.)
        """
        self.chat_history.append(f"<i style='color: #666;'>{text}</i>")
        self.chat_history.append("")
        logger.debug(f"ConversationView: Added system message")

    def append_error_message(self, text: str):
        """Append error message to conversation.

        Args:
            text: Error message text
        """
        self.chat_history.append(f"<b style='color: #cc0000;'>Error:</b> {text}")
        self.chat_history.append("")
        logger.debug(f"ConversationView: Added error message")

    def show_welcome_message(self):
        """Show welcome message at startup."""
        self.append_system_message(
            "Welcome to GemBrain! I'm your agentic second brain assistant.\\n\\n"
            "I can help you:\\n"
            "• Capture and organize notes\\n"
            "• Manage tasks and projects\\n"
            "• Store long-term memories\\n"
            "• Run daily/weekly reviews\\n\\n"
            "Just tell me what's on your mind, and I'll help structure it!"
        )

    def clear_history(self):
        """Clear all conversation history."""
        self.chat_history.clear()
        logger.debug("ConversationView: Cleared history")
