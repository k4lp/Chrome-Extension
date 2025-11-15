"""Conversation view widget - displays chat messages and final outputs only."""

import re

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLabel
from PyQt6.QtCore import Qt
from loguru import logger

try:
    import markdown

    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False
    logger.warning("markdown library not available - install with: pip install markdown")

try:
    from latex2mathml.converter import convert as latex_to_mathml

    LATEX_AVAILABLE = True
except ImportError:
    LATEX_AVAILABLE = False
    logger.warning("latex2mathml library not available - install with: pip install latex2mathml")


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
        # First, replace LaTeX expressions with MathML so Qt can render them properly
        processed_text = self._render_latex(text)

        if MARKDOWN_AVAILABLE:
            try:
                return markdown.markdown(
                    processed_text,
                    extensions=["fenced_code", "tables", "nl2br"],
                )
            except Exception as e:
                logger.warning(f"Markdown conversion failed: {e}")
                return processed_text.replace("\n", "<br>")
        else:
            # Fallback: simple newline to <br> conversion
            return processed_text.replace("\n", "<br>")

    def _render_latex(self, text: str) -> str:
        """Convert LaTeX expressions to MathML if the converter is available."""

        if not LATEX_AVAILABLE or not text:
            return text

        def _convert(expr: str, display: bool) -> str:
            stripped = expr.strip()
            if not stripped:
                return expr
            try:
                mathml = latex_to_mathml(stripped)
                wrapper = "div" if display else "span"
                cls = "math display" if display else "math inline"
                return f"<{wrapper} class='{cls}'>{mathml}</{wrapper}>"
            except Exception as exc:
                logger.debug(f"LaTeX conversion failed for '{stripped[:30]}...': {exc}")
                # Fallback to monospace representation so the user still sees raw LaTeX
                delimiter = "$$" if display else "$"
                return f"<code>{delimiter}{stripped}{delimiter}</code>"

        # Order matters: handle $$...$$ and \[...\] (display math) before inline patterns
        patterns = [
            (re.compile(r"\$\$(.+?)\$\$", re.DOTALL), True),
            (re.compile(r"\\\[(.+?)\\\]", re.DOTALL), True),
            (re.compile(r"\\\((.+?)\\\)", re.DOTALL), False),
            (re.compile(r"(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)", re.DOTALL), False),
        ]

        rendered = text
        for pattern, is_display in patterns:
            rendered = pattern.sub(lambda m: _convert(m.group(1), is_display), rendered)

        return rendered

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
