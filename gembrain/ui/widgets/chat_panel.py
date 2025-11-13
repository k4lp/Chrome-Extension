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


class OrchestratorWorker(QThread):
    """Worker thread for running orchestrator in background."""

    # Signals
    finished = pyqtSignal(object)  # OrchestratorResponse
    error = pyqtSignal(str)  # Error message
    progress = pyqtSignal(str)  # Progress update (iteration info)

    def __init__(self, orchestrator, user_message, ui_context, auto_apply):
        """Initialize worker.

        Args:
            orchestrator: Orchestrator instance
            user_message: User's message
            ui_context: UI context
            auto_apply: Whether to auto-apply actions
        """
        super().__init__()
        self.orchestrator = orchestrator
        self.user_message = user_message
        self.ui_context = ui_context
        self.auto_apply = auto_apply

    def run(self):
        """Run orchestrator in background thread."""
        try:
            logger.info("🧵 Worker thread started")

            # Define progress callback that emits our signal
            def on_progress(message: str):
                """Progress callback that emits signal."""
                self.progress.emit(message)

            # Call orchestrator with progress callback
            response = self.orchestrator.run_user_message(
                user_message=self.user_message,
                ui_context=self.ui_context,
                auto_apply_actions=self.auto_apply,
                progress_callback=on_progress,
            )

            logger.info("🧵 Worker thread completed successfully")
            self.finished.emit(response)

        except Exception as e:
            logger.error(f"🧵 Worker thread error: {e}")
            self.error.emit(str(e))


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
        self.worker = None  # Background worker thread

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
        """Send user message to orchestrator (runs in background thread)."""
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

        # Check if already processing
        if self.worker and self.worker.isRunning():
            logger.warning("Already processing a message")
            return

        # Clear input
        self.input_box.clear()

        # Show user message
        self._append_user_message(user_text)

        # Disable UI during processing (but keep it responsive)
        self._freeze_ui(True)

        # Get UI context
        ui_context = UIContext(active_panel="chat")

        # Create and start worker thread
        auto_apply = self.auto_apply_check.isChecked()
        self.worker = OrchestratorWorker(
            orchestrator=self.orchestrator,
            user_message=user_text,
            ui_context=ui_context,
            auto_apply=auto_apply,
        )

        # Connect signals
        self.worker.finished.connect(self._on_response_ready)
        self.worker.error.connect(self._on_worker_error)
        self.worker.progress.connect(self._on_progress_update)

        # Start worker
        logger.info("🚀 Starting background worker thread")
        self.worker.start()

    def _on_response_ready(self, response: OrchestratorResponse):
        """Handle response from worker thread.

        Args:
            response: OrchestratorResponse from orchestrator
        """
        logger.info("✅ Response ready from worker thread")

        if response.error:
            self._append_error_message(f"Error: {response.error}")
        else:
            # Show agent reply
            self._append_agent_message(response.reply_text)

            # Handle actions
            if response.actions:
                if self.auto_apply_check.isChecked() and response.action_results:
                    # Show results with details
                    self._show_action_results(response.action_results)
                else:
                    # Show actions for review
                    self._show_actions(response.actions)

        # Re-enable UI
        self._freeze_ui(False)

    def _on_worker_error(self, error_message: str):
        """Handle error from worker thread.

        Args:
            error_message: Error message
        """
        logger.error(f"❌ Worker error: {error_message}")
        self._append_error_message(f"Error: {error_message}")

        # Re-enable UI
        self._freeze_ui(False)

    def _on_progress_update(self, progress_message: str):
        """Handle progress update from worker thread.

        Args:
            progress_message: Progress message (e.g., "Iteration 3/50")
        """
        # Update the processing message with iteration progress
        cursor = self.chat_history.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock, QTextCursor.MoveMode.KeepAnchor)
        current_line = cursor.selectedText()

        # If last line is a processing message, update it
        if "Processing" in current_line or "Iteration" in current_line:
            cursor.removeSelectedText()
            cursor.deletePreviousChar()  # Remove newline

        # Append new progress
        self.chat_history.append(f"<i style='color: #999;'>{progress_message}</i>")

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

    def _freeze_ui(self, freeze: bool):
        """Freeze or unfreeze UI during processing.

        Args:
            freeze: Whether to freeze the UI
        """
        self.input_box.setEnabled(not freeze)
        self.send_btn.setEnabled(not freeze)
        self.auto_apply_check.setEnabled(not freeze)
        self.apply_btn.setEnabled(not freeze and len(self.pending_actions) > 0)

        if freeze:
            self.send_btn.setText("⏳ Processing...")
            self.chat_history.append("<i style='color: #999;'>Processing your request...</i>")
        else:
            self.send_btn.setText("Send")

    def _show_action_results(self, results):
        """Show action results with detailed output.

        Args:
            results: List of ActionResult objects
        """
        success_count = sum(1 for r in results if r.success)
        fail_count = len(results) - success_count

        self._append_system_message(
            f"<b>✓ Executed {len(results)} actions:</b> {success_count} succeeded, {fail_count} failed"
        )

        for result in results:
            # Show action type and message
            if result.success:
                icon = "✓"
                color = "#00aa00"
            else:
                icon = "✗"
                color = "#cc0000"

            self.chat_history.append(
                f"<b style='color: {color};'>{icon} {result.action_type}:</b> {result.message}"
            )

            # Special handling for code execution
            if result.action_type == "execute_code" and result.data:
                self._show_code_execution_result(result)

        self.chat_history.append("")

    def _show_code_execution_result(self, result):
        """Show code execution result with detailed output.

        Args:
            result: ActionResult from code execution
        """
        data = result.data

        # Create a nice code execution output box
        output_html = "<div style='background: #f5f5f5; border-left: 4px solid #1a1a1a; padding: 12px; margin: 8px 0; font-family: monospace;'>"

        if result.success:
            output_html += "<b style='color: #00aa00;'>✓ Code Execution Successful</b><br/>"

            # Show execution time if available
            if "execution_time" in data:
                output_html += f"<small>Execution time: {data.get('execution_time', 0):.3f}s</small><br/>"

            # Show stdout
            if data.get("stdout"):
                output_html += "<br/><b>Output:</b><br/>"
                output_html += f"<pre style='margin: 4px 0; white-space: pre-wrap;'>{data['stdout']}</pre>"

            # Show result
            if data.get("result"):
                output_html += "<br/><b>Result:</b><br/>"
                output_html += f"<code>{data['result']}</code>"

            # Show stderr if any
            if data.get("stderr"):
                output_html += "<br/><b style='color: #cc6600;'>Warnings:</b><br/>"
                output_html += f"<pre style='margin: 4px 0; color: #cc6600;'>{data['stderr']}</pre>"

        else:
            output_html += "<b style='color: #cc0000;'>✗ Code Execution Failed</b><br/>"

            # Show error
            if data.get("error"):
                output_html += "<br/><b>Error:</b><br/>"
                output_html += f"<pre style='margin: 4px 0; color: #cc0000; white-space: pre-wrap;'>{data['error']}</pre>"

            # Show stderr if any
            if data.get("stderr"):
                output_html += "<br/><b>STDERR:</b><br/>"
                output_html += f"<pre style='margin: 4px 0;'>{data['stderr']}</pre>"

        output_html += "</div>"
        self.chat_history.append(output_html)
