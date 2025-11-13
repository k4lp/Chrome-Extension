"""Chat panel for interacting with the agent."""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QPushButton,
    QCheckBox,
    QLabel,
    QScrollArea,
    QFrame,
    QMessageBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QTextCursor
from loguru import logger

from ...agents.orchestrator import OrchestratorResponse, UIContext


class ChatPanel(QWidget):
    """Panel for chat interactions with the agent."""

    def __init__(self, db_session, orchestrator, settings):
        """Initialize chat panel.

        Args:
            db_session: Database session
            orchestrator: Orchestrator instance
            settings: Application settings
        """
        super().__init__()

        self.db_session = db_session
        self.orchestrator = orchestrator
        self.settings = settings

        self._setup_ui()

    def _setup_ui(self):
        """Setup user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Title
        title = QLabel("Chat with GemBrain")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        # Chat history
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_history.setPlaceholderText("Chat history will appear here...")
        layout.addWidget(self.chat_history, stretch=1)

        # Actions preview area (scrollable)
        actions_label = QLabel("Proposed Actions:")
        actions_label.setStyleSheet("font-weight: bold; margin-top: 8px;")
        layout.addWidget(actions_label)

        self.actions_scroll = QScrollArea()
        self.actions_scroll.setWidgetResizable(True)
        self.actions_scroll.setMaximumHeight(150)
        self.actions_widget = QWidget()
        self.actions_layout = QVBoxLayout(self.actions_widget)
        self.actions_layout.setContentsMargins(8, 8, 8, 8)
        self.actions_scroll.setWidget(self.actions_widget)
        layout.addWidget(self.actions_scroll)

        self.actions_scroll.hide()  # Hidden by default
        self.pending_actions = []

        # Input area
        input_frame = QFrame()
        input_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        input_layout = QVBoxLayout(input_frame)

        self.input_box = QTextEdit()
        self.input_box.setPlaceholderText("Type your message here...")
        self.input_box.setMaximumHeight(100)
        input_layout.addWidget(self.input_box)

        # Buttons row
        button_layout = QHBoxLayout()

        self.auto_apply_check = QCheckBox("Auto-apply actions")
        self.auto_apply_check.setChecked(self.settings.agent_behavior.auto_structured_actions)
        button_layout.addWidget(self.auto_apply_check)

        button_layout.addStretch()

        self.apply_btn = QPushButton("Apply Actions")
        self.apply_btn.clicked.connect(self._apply_actions)
        self.apply_btn.setEnabled(False)
        button_layout.addWidget(self.apply_btn)

        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self._send_message)
        self.send_btn.setDefault(True)
        button_layout.addWidget(self.send_btn)

        input_layout.addLayout(button_layout)
        layout.addWidget(input_frame)

        # Welcome message
        self._append_system_message(
            "Welcome to GemBrain! I'm your agentic second brain assistant.\n\n"
            "I can help you:\n"
            "• Capture and organize notes\n"
            "• Manage tasks and projects\n"
            "• Store long-term memories\n"
            "• Run daily/weekly reviews\n\n"
            "Just tell me what's on your mind, and I'll help structure it!"
        )

    def _send_message(self):
        """Send user message to orchestrator."""
        user_text = self.input_box.toPlainText().strip()
        if not user_text:
            return

        # Check if configured
        if not self.orchestrator.is_configured():
            QMessageBox.warning(
                self,
                "Not Configured",
                "Please configure your Gemini API key in Settings first.",
            )
            return

        # Clear input
        self.input_box.clear()

        # Show user message
        self._append_user_message(user_text)

        # Disable send button
        self.send_btn.setEnabled(False)
        self.send_btn.setText("Thinking...")

        try:
            # Get UI context
            ui_context = UIContext(active_panel="chat")

            # Call orchestrator
            auto_apply = self.auto_apply_check.isChecked()
            response = self.orchestrator.run_user_message(
                user_message=user_text,
                ui_context=ui_context,
                auto_apply_actions=auto_apply,
            )

            if response.error:
                self._append_error_message(f"Error: {response.error}")
            else:
                # Show agent reply
                self._append_agent_message(response.reply_text)

                # Handle actions
                if response.actions:
                    if auto_apply and response.action_results:
                        # Show results
                        self._append_system_message(
                            f"✓ Applied {len(response.action_results)} actions automatically."
                        )
                        for result in response.action_results:
                            if not result.success:
                                self._append_error_message(
                                    f"Action failed: {result.message}"
                                )
                    else:
                        # Show actions for review
                        self._show_actions(response.actions)

        except Exception as e:
            logger.error(f"Error in chat: {e}")
            self._append_error_message(f"Error: {str(e)}")

        finally:
            # Re-enable send button
            self.send_btn.setEnabled(True)
            self.send_btn.setText("Send")

    def _show_actions(self, actions):
        """Show actions for user review.

        Args:
            actions: List of action dictionaries
        """
        # Clear previous actions
        for i in reversed(range(self.actions_layout.count())):
            self.actions_layout.itemAt(i).widget().setParent(None)

        self.pending_actions = actions

        # Add action items
        for action in actions:
            action_text = f"{action.get('type', 'unknown')}: {str(action)[:100]}"
            label = QLabel(action_text)
            label.setWordWrap(True)
            label.setStyleSheet("padding: 4px; background: #f0f0f0; border-radius: 4px;")
            self.actions_layout.addWidget(label)

        self.actions_scroll.show()
        self.apply_btn.setEnabled(True)

        self._append_system_message(
            f"📋 {len(actions)} actions proposed. Review and click 'Apply Actions' to execute."
        )

    def _apply_actions(self):
        """Apply pending actions."""
        if not self.pending_actions:
            return

        try:
            results = self.orchestrator.apply_actions(self.pending_actions)

            success_count = sum(1 for r in results if r.success)
            fail_count = len(results) - success_count

            self._append_system_message(
                f"✓ Applied {success_count} actions. {fail_count} failed."
            )

            for result in results:
                if not result.success:
                    self._append_error_message(f"Failed: {result.message}")

            # Clear actions
            self.pending_actions = []
            self.actions_scroll.hide()
            self.apply_btn.setEnabled(False)

        except Exception as e:
            logger.error(f"Error applying actions: {e}")
            self._append_error_message(f"Error applying actions: {str(e)}")

    def _append_user_message(self, text: str):
        """Append user message to chat history."""
        self.chat_history.append(f"<b style='color: #0066cc;'>You:</b> {text}")
        self.chat_history.append("")

    def _append_agent_message(self, text: str):
        """Append agent message to chat history."""
        self.chat_history.append(f"<b style='color: #00aa00;'>GemBrain:</b> {text}")
        self.chat_history.append("")

    def _append_system_message(self, text: str):
        """Append system message to chat history."""
        self.chat_history.append(f"<i style='color: #666;'>{text}</i>")
        self.chat_history.append("")

    def _append_error_message(self, text: str):
        """Append error message to chat history."""
        self.chat_history.append(f"<b style='color: #cc0000;'>Error:</b> {text}")
        self.chat_history.append("")
