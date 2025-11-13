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
    QSplitter,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QTextCursor
from loguru import logger

from ...agents.orchestrator import OrchestratorResponse, UIContext
from .conversation_view import ConversationView
from .technical_details_view import TechnicalDetailsView


class OrchestratorWorker(QThread):
    """Worker thread for running orchestrator in background."""

    # Signals
    finished = pyqtSignal(object)  # OrchestratorResponse
    error = pyqtSignal(str)  # Error message
    progress = pyqtSignal(object)  # Progress update (structured dict)

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
            def on_progress(progress_data):
                """Progress callback that emits signal.

                Args:
                    progress_data: Can be string (legacy) or dict (structured)
                """
                # Emit as-is (dict or string)
                self.progress.emit(progress_data)

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
        """Setup user interface with split-screen layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Title
        title = QLabel("Chat with GemBrain")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        # Split-screen: Conversation (top 55%) + Technical Details (bottom 45%)
        self.splitter = QSplitter(Qt.Orientation.Vertical)

        # Upper half: Conversation view (final outputs only)
        self.conversation_view = ConversationView()
        self.splitter.addWidget(self.conversation_view)

        # Lower half: Technical details view (reasoning, code, actions)
        self.technical_view = TechnicalDetailsView()
        self.splitter.addWidget(self.technical_view)

        # Set 55/45 split ratio (55% top, 45% bottom)
        # Total height = 1000 units, so 550 top, 450 bottom
        self.splitter.setSizes([550, 450])
        self.splitter.setStretchFactor(0, 55)  # Conversation gets 55%
        self.splitter.setStretchFactor(1, 45)  # Technical gets 45%

        layout.addWidget(self.splitter, stretch=1)

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
        self.conversation_view.show_welcome_message()

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

    def _on_progress_update(self, progress_data):
        """Handle progress update from worker thread.

        Args:
            progress_data: Progress data (dict with type, or legacy string)
        """
        # Handle both structured dict and legacy string format
        if isinstance(progress_data, dict):
            event_type = progress_data.get("type")

            if event_type == "iteration_start":
                # Show iteration marker in technical view
                iteration = progress_data.get("iteration", 0)
                max_iterations = progress_data.get("max_iterations", 0)
                self.technical_view.append_reasoning_iteration(iteration, max_iterations)

                # Show brief update in conversation view
                self.conversation_view.append_system_message(
                    f"Reasoning iteration {iteration}/{max_iterations}..."
                )

            elif event_type == "thought":
                # Show thought in technical view
                thought = progress_data.get("content", "")
                self.technical_view.append_reasoning_thought(thought)

            elif event_type == "observation":
                # Show observation in technical view
                observation = progress_data.get("content", "")
                self.technical_view.append_reasoning_observation(observation)

            elif event_type == "insights":
                # Show insights in technical view
                insights = progress_data.get("content", "")
                self.technical_view.append_reasoning_insights(insights)

            elif event_type == "actions_planned":
                # Show actions in technical view
                actions = progress_data.get("actions", [])
                self.technical_view.append_reasoning_action_plan(actions)

            elif event_type == "action_start":
                # Show action start in technical view
                action_type = progress_data.get("action_type", "unknown")
                details = progress_data.get("details", "")
                self.technical_view.append_action_start(action_type, details)

            elif event_type == "code_execution_start":
                # Show code execution start in technical view
                code = progress_data.get("code", "")
                self.technical_view.append_code_execution_start(code)
                self.technical_view.switch_to_code_tab()

            elif event_type == "reasoning_complete":
                # Show completion in technical view
                success = progress_data.get("success", True)
                message = progress_data.get("message", "")
                self.technical_view.append_reasoning_completion(success, message)

        elif isinstance(progress_data, str):
            # Legacy string format - just show in conversation view
            self.conversation_view.append_system_message(progress_data)

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
        """Append user message to conversation view."""
        self.conversation_view.append_user_message(text)

    def _append_agent_message(self, text: str):
        """Append agent message to conversation view."""
        self.conversation_view.append_agent_message(text)

    def _append_system_message(self, text: str):
        """Append system message to conversation view."""
        self.conversation_view.append_system_message(text)

    def _append_error_message(self, text: str):
        """Append error message to conversation view."""
        self.conversation_view.append_error_message(text)

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
            self.conversation_view.append_system_message("Processing your request...")
        else:
            self.send_btn.setText("Send")

    def _show_action_results(self, results):
        """Show action results in both conversation and technical views.

        Args:
            results: List of ActionResult objects
        """
        success_count = sum(1 for r in results if r.success)
        fail_count = len(results) - success_count

        # Show summary in conversation view
        self._append_system_message(
            f"✓ Executed {len(results)} actions: {success_count} succeeded, {fail_count} failed"
        )

        # Show detailed results in technical view (Actions tab)
        self.technical_view.append_actions_summary(len(results), success_count, fail_count)

        for result in results:
            # Add to technical view action history with full result data
            self.technical_view.append_action_result(
                result.action_type, result.success, result.message, result_data=result.data
            )

            # Special handling for code execution - show in Code Execution tab
            if result.action_type == "execute_code" and result.data:
                self._show_code_execution_result(result)

    def _show_code_execution_result(self, result):
        """Show code execution result in technical details view.

        Args:
            result: ActionResult from code execution
        """
        # Show in technical view (Code Execution tab)
        self.technical_view.append_code_execution_result(result.data)

        # Switch to code execution tab to show the result
        self.technical_view.switch_to_code_tab()
