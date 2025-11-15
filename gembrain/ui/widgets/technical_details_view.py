"""Technical details view widget - displays reasoning logs, code execution, and actions."""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTextEdit,
    QLabel,
    QTabWidget,
    QPushButton,
    QHBoxLayout,
    QScrollArea,
    QFrame,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from loguru import logger

from gembrain.ui.widgets.collapsible_box import CollapsibleBox

try:
    import markdown
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False
    logger.warning("markdown library not available - install with: pip install markdown")


class TechnicalDetailsView(QWidget):
    """Widget for displaying technical details during agent execution.

    Responsible for:
    - Showing reasoning iterations (thought process) in collapsible sections
    - Showing code execution details (code + output) in structured format
    - Showing action execution history with proper structure
    """

    def __init__(self):
        """Initialize technical details view."""
        super().__init__()
        self.current_iteration = None
        self.current_code_section = None
        self._setup_ui()

    def _setup_ui(self):
        """Setup user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Header with title and clear button
        header = QHBoxLayout()
        title = QLabel("Technical Details")
        title.setStyleSheet("font-size: 16px; font-weight: bold; padding: 8px;")
        header.addWidget(title)

        header.addStretch()

        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self.clear_all_tabs)
        clear_btn.setMaximumWidth(100)
        header.addWidget(clear_btn)

        layout.addLayout(header)

        # Tab widget
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Tab 1: Reasoning Log (with scroll area for collapsible sections)
        reasoning_scroll = QScrollArea()
        reasoning_scroll.setWidgetResizable(True)
        reasoning_scroll.setStyleSheet("QScrollArea { border: none; background: #f5f5f5; }")

        self.reasoning_container = QWidget()
        self.reasoning_layout = QVBoxLayout(self.reasoning_container)
        self.reasoning_layout.setContentsMargins(8, 8, 8, 8)
        self.reasoning_layout.setSpacing(12)
        self.reasoning_layout.addStretch()  # Push content to top

        reasoning_scroll.setWidget(self.reasoning_container)
        self.tabs.addTab(reasoning_scroll, "🧠 Reasoning")

        # Tab 2: Code Execution (with scroll area for collapsible sections)
        code_scroll = QScrollArea()
        code_scroll.setWidgetResizable(True)
        code_scroll.setStyleSheet("QScrollArea { border: none; background: #f5f5f5; }")

        self.code_container = QWidget()
        self.code_layout = QVBoxLayout(self.code_container)
        self.code_layout.setContentsMargins(8, 8, 8, 8)
        self.code_layout.setSpacing(12)
        self.code_layout.addStretch()  # Push content to top

        code_scroll.setWidget(self.code_container)
        self.tabs.addTab(code_scroll, "💻 Code Execution")

        # Tab 3: Action History (with scroll area for structured actions)
        action_scroll = QScrollArea()
        action_scroll.setWidgetResizable(True)
        action_scroll.setStyleSheet("QScrollArea { border: none; background: #f5f5f5; }")

        self.action_container = QWidget()
        self.action_layout = QVBoxLayout(self.action_container)
        self.action_layout.setContentsMargins(8, 8, 8, 8)
        self.action_layout.setSpacing(12)
        self.action_layout.addStretch()  # Push content to top

        action_scroll.setWidget(self.action_container)
        self.tabs.addTab(action_scroll, "⚡ Actions")

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
                    extensions=['fenced_code', 'tables', 'nl2br', 'codehilite']
                )
            except Exception as e:
                logger.warning(f"Markdown conversion failed: {e}")
                return text.replace('\n', '<br>')
        else:
            # Fallback: simple newline to <br> conversion
            return text.replace('\n', '<br>')

    def _create_styled_text_widget(self, text: str, monospace: bool = False) -> QTextEdit:
        """Create a styled read-only text widget.

        Args:
            text: Text content
            monospace: Whether to use monospace font

        Returns:
            Styled QTextEdit widget
        """
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setHtml(text)
        text_edit.setMaximumHeight(300)
        text_edit.setStyleSheet(
            """
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                background: #fafafa;
                padding: 8px;
            }
            """
        )

        if monospace:
            font = QFont("Courier New")
            font.setStyleHint(QFont.StyleHint.Monospace)
            font.setPointSize(9)
            text_edit.setFont(font)

        return text_edit

    # ===========================================================================
    # REASONING TAB METHODS
    # ===========================================================================

    def append_reasoning_iteration(self, iteration: int, max_iterations: int):
        """Start a new reasoning iteration with collapsible section.

        Args:
            iteration: Current iteration number
            max_iterations: Maximum iterations allowed
        """
        # Create collapsible box for this iteration
        title = f"Iteration {iteration}/{max_iterations}"
        self.current_iteration = CollapsibleBox(title)
        self.current_iteration.set_expanded(True)  # Auto-expand current iteration

        # Insert before the stretch
        self.reasoning_layout.insertWidget(self.reasoning_layout.count() - 1, self.current_iteration)

        logger.debug(f"TechnicalDetailsView: Added iteration {iteration}/{max_iterations}")

    def append_reasoning_thought(self, thought: str):
        """Append reasoning thought to current iteration.

        Args:
            thought: Thought/reasoning text (FULL, UNTRUNCATED, in MARKDOWN format)
        """
        if not self.current_iteration:
            return

        # Convert markdown to HTML
        html_content = self._markdown_to_html(thought)

        # Create section label
        label = QLabel("<b style='color: #0066cc;'>💭 Complete Reasoning:</b>")
        label.setStyleSheet("padding: 4px 0;")

        # Create text widget
        text_widget = self._create_styled_text_widget(html_content, monospace=False)

        self.current_iteration.add_widget(label)
        self.current_iteration.add_widget(text_widget)

        logger.debug("TechnicalDetailsView: Added reasoning thought (markdown rendered)")

    def append_reasoning_observation(self, observation: str):
        """Append observation to current iteration.

        Args:
            observation: Observation text (FULL, EXACT)
        """
        if not self.current_iteration:
            return

        label = QLabel("<b style='color: #00aa00;'>🔍 Observations:</b>")
        label.setStyleSheet("padding: 4px 0;")

        text_widget = self._create_styled_text_widget(observation.replace('\n', '<br>'), monospace=False)

        self.current_iteration.add_widget(label)
        self.current_iteration.add_widget(text_widget)

    def append_reasoning_insights(self, insights: str):
        """Append insights gained to current iteration.

        Args:
            insights: Insights text (FULL, EXACT)
        """
        if not self.current_iteration:
            return

        label = QLabel("<b style='color: #cc6600;'>💡 Insights Gained:</b>")
        label.setStyleSheet("padding: 4px 0;")

        text_widget = self._create_styled_text_widget(insights.replace('\n', '<br>'), monospace=False)

        self.current_iteration.add_widget(label)
        self.current_iteration.add_widget(text_widget)

    def append_reasoning_action_plan(self, actions: list):
        """Append action plan to current iteration.

        Args:
            actions: List of planned actions (FULL details shown)
        """
        if not self.current_iteration:
            return

        label = QLabel(f"<b style='color: #cc6600;'>⚡ Actions Planned:</b> {len(actions)}")
        label.setStyleSheet("padding: 4px 0;")

        # Create structured action list
        html = "<table style='width: 100%; border-collapse: collapse;'>"
        for i, action in enumerate(actions, 1):
            action_type = action.get("type", "unknown")
            html += f"<tr><td style='padding: 4px; border-bottom: 1px solid #eee;'><b>{i}. {action_type}</b></td></tr>"

            # Show parameters
            params = {k: v for k, v in action.items() if k != "type"}
            if params:
                for key, value in params.items():
                    # Truncate very long values
                    if isinstance(value, str) and len(value) > 200:
                        display_value = value[:200] + f"... ({len(value)} chars)"
                    else:
                        display_value = str(value)
                    html += f"<tr><td style='padding: 2px 4px 2px 24px; color: #666; font-size: 11px;'>{key}: {display_value}</td></tr>"

        html += "</table>"

        text_widget = self._create_styled_text_widget(html, monospace=False)
        text_widget.setMaximumHeight(200)

        self.current_iteration.add_widget(label)
        self.current_iteration.add_widget(text_widget)

    def append_reasoning_action_result(self, action_type: str, success: bool, message: str, result_data: dict = None):
        """Append action execution result to current reasoning iteration (collapsible).

        Args:
            action_type: Type of action executed
            success: Whether action succeeded
            message: Result message
            result_data: Optional result data (for code execution: stdout, stderr, result, error)
        """
        if not self.current_iteration:
            return

        # Create collapsible section for this action result
        status_icon = "✅" if success else "❌"
        collapsible_title = f"{status_icon} {action_type}"
        action_result_box = CollapsibleBox(collapsible_title)
        action_result_box.set_expanded(False)  # Collapsed by default to keep UI clean

        # Status message
        color = "#00aa00" if success else "#cc0000"
        status_label = QLabel(f"<b style='color: {color};'>Status:</b> {message}")
        status_label.setStyleSheet("padding: 4px; font-size: 11px;")
        action_result_box.add_widget(status_label)

        # For code execution, show all outputs
        if action_type == "execute_code" and result_data:
            stdout = result_data.get("stdout", "")
            stderr = result_data.get("stderr", "")
            result = result_data.get("result")
            error = result_data.get("error", "")
            exec_time = result_data.get("execution_time", 0.0)

            # Execution time
            time_label = QLabel(f"<b>⏱️ Execution Time:</b> {exec_time:.3f}s")
            time_label.setStyleSheet("padding: 2px; font-size: 10px;")
            action_result_box.add_widget(time_label)

            # Stdout output
            if stdout:
                output_label = QLabel("<b style='color: #0066cc;'>📤 Output (stdout):</b>")
                output_label.setStyleSheet("padding: 4px 0; font-size: 10px;")
                output_html = f"<pre style='background: #f0f8ff; padding: 6px; border-radius: 3px; color: #000; font-size: 10px;'>{stdout}</pre>"
                output_widget = self._create_styled_text_widget(output_html, monospace=True)
                output_widget.setMaximumHeight(150)
                action_result_box.add_widget(output_label)
                action_result_box.add_widget(output_widget)

            # Return value
            if result is not None:
                result_label = QLabel("<b style='color: #00aa00;'>🎯 Return Value:</b>")
                result_label.setStyleSheet("padding: 4px 0; font-size: 10px;")
                result_html = f"<pre style='background: #f0fff0; padding: 6px; border-radius: 3px; font-size: 10px;'>{str(result)}</pre>"
                result_widget = self._create_styled_text_widget(result_html, monospace=True)
                result_widget.setMaximumHeight(150)
                action_result_box.add_widget(result_label)
                action_result_box.add_widget(result_widget)

            # Stderr output
            if stderr:
                stderr_label = QLabel("<b style='color: #ff6600;'>⚠️ Stderr:</b>")
                stderr_label.setStyleSheet("padding: 4px 0; font-size: 10px;")
                stderr_html = f"<pre style='background: #fff8f0; padding: 6px; border-radius: 3px; color: #ff6600; font-size: 10px;'>{stderr}</pre>"
                stderr_widget = self._create_styled_text_widget(stderr_html, monospace=True)
                stderr_widget.setMaximumHeight(150)
                action_result_box.add_widget(stderr_label)
                action_result_box.add_widget(stderr_widget)

            # Error
            if error:
                error_label = QLabel("<b style='color: #cc0000;'>❌ Error:</b>")
                error_label.setStyleSheet("padding: 4px 0; font-size: 10px;")
                error_html = f"<pre style='background: #fff0f0; padding: 6px; border-radius: 3px; color: #cc0000; font-size: 10px;'>{error}</pre>"
                error_widget = self._create_styled_text_widget(error_html, monospace=True)
                error_widget.setMaximumHeight(150)
                action_result_box.add_widget(error_label)
                action_result_box.add_widget(error_widget)

        # For other actions, show result data if available
        elif result_data:
            import json
            data_label = QLabel("<b>📋 Result Data:</b>")
            data_label.setStyleSheet("padding: 4px 0; font-size: 10px;")
            data_str = json.dumps(result_data, indent=2, default=str)
            data_html = f"<pre style='background: #f8f8f8; padding: 6px; border-radius: 3px; font-size: 10px;'>{data_str}</pre>"
            data_widget = self._create_styled_text_widget(data_html, monospace=True)
            data_widget.setMaximumHeight(150)
            action_result_box.add_widget(data_label)
            action_result_box.add_widget(data_widget)

        # Add to current iteration
        self.current_iteration.add_widget(action_result_box)
        logger.debug(f"TechnicalDetailsView: Added action result {action_type} to reasoning iteration")

    def append_reasoning_completion(self, success: bool, message: str, summary_data: dict = None):
        """Append completion status to current iteration.

        Args:
            success: Whether reasoning completed successfully
            message: Completion message
            summary_data: Optional summary data dictionary
        """
        if not self.current_iteration:
            return

        status_icon = "✅" if success else "❌"
        color = "#00aa00" if success else "#cc0000"

        label = QLabel(f"<b style='color: {color};'>{status_icon} Status:</b> {message}")
        label.setStyleSheet("padding: 8px 0;")

        self.current_iteration.add_widget(label)

    # ===========================================================================
    # CODE EXECUTION TAB METHODS
    # ===========================================================================

    def append_code_execution_start(self, code: str):
        """Append code execution start.

        Args:
            code: Python code being executed (FULL, no truncation)
        """
        # Create collapsible box for this code execution
        import time
        timestamp = time.strftime("%H:%M:%S")
        title = f"Code Execution - {timestamp}"

        self.current_code_section = CollapsibleBox(title)
        self.current_code_section.set_expanded(True)  # Auto-expand

        # Code section
        code_label = QLabel("<b style='color: #0066cc;'>📝 Code:</b>")
        code_label.setStyleSheet("padding: 4px 0;")

        # Format code with syntax highlighting (simple)
        code_html = f"<pre style='background: #f8f8f8; padding: 8px; border-radius: 4px; overflow-x: auto;'>{code}</pre>"
        code_widget = self._create_styled_text_widget(code_html, monospace=True)
        code_widget.setMaximumHeight(400)

        self.current_code_section.add_widget(code_label)
        self.current_code_section.add_widget(code_widget)

        # Insert before the stretch
        self.code_layout.insertWidget(self.code_layout.count() - 1, self.current_code_section)

        logger.debug("TechnicalDetailsView: Added code execution start")

    def append_code_execution_result(self, result_data: dict):
        """Append code execution result.

        Args:
            result_data: Dictionary with stdout, stderr, result, error, execution_time, success
        """
        if not self.current_code_section:
            return

        success = result_data.get("success", False)
        exec_time = result_data.get("execution_time", 0.0)
        stdout = result_data.get("stdout", "")
        stderr = result_data.get("stderr", "")
        result = result_data.get("result")
        error = result_data.get("error", "")

        # Status section
        status_icon = "✅" if success else "❌"
        status_color = "#00aa00" if success else "#cc0000"
        status_label = QLabel(f"<b style='color: {status_color};'>{status_icon} Status:</b> {'Success' if success else 'Failed'} ({exec_time:.3f}s)")
        status_label.setStyleSheet("padding: 8px 0;")
        self.current_code_section.add_widget(status_label)

        # Output section (if any)
        if stdout:
            output_label = QLabel("<b style='color: #0066cc;'>📤 Output (stdout):</b>")
            output_label.setStyleSheet("padding: 4px 0;")

            output_html = f"<pre style='background: #f0f8ff; padding: 8px; border-radius: 4px; color: #000;'>{stdout}</pre>"
            output_widget = self._create_styled_text_widget(output_html, monospace=True)
            output_widget.setMaximumHeight(200)

            self.current_code_section.add_widget(output_label)
            self.current_code_section.add_widget(output_widget)

        # Result section (if any)
        if result is not None:
            result_label = QLabel("<b style='color: #00aa00;'>🎯 Return Value:</b>")
            result_label.setStyleSheet("padding: 4px 0;")

            result_html = f"<pre style='background: #f0fff0; padding: 8px; border-radius: 4px;'>{str(result)}</pre>"
            result_widget = self._create_styled_text_widget(result_html, monospace=True)
            result_widget.setMaximumHeight(200)

            self.current_code_section.add_widget(result_label)
            self.current_code_section.add_widget(result_widget)

        # Error section (if any)
        if error:
            error_label = QLabel("<b style='color: #cc0000;'>❌ Error:</b>")
            error_label.setStyleSheet("padding: 4px 0;")

            error_html = f"<pre style='background: #fff0f0; padding: 8px; border-radius: 4px; color: #cc0000;'>{error}</pre>"
            error_widget = self._create_styled_text_widget(error_html, monospace=True)
            error_widget.setMaximumHeight(200)

            self.current_code_section.add_widget(error_label)
            self.current_code_section.add_widget(error_widget)

        # Stderr section (if any)
        if stderr:
            stderr_label = QLabel("<b style='color: #ff8800;'>⚠️ Warnings (stderr):</b>")
            stderr_label.setStyleSheet("padding: 4px 0;")

            stderr_html = f"<pre style='background: #fff8f0; padding: 8px; border-radius: 4px; color: #ff8800;'>{stderr}</pre>"
            stderr_widget = self._create_styled_text_widget(stderr_html, monospace=True)
            stderr_widget.setMaximumHeight(200)

            self.current_code_section.add_widget(stderr_label)
            self.current_code_section.add_widget(stderr_widget)

        logger.debug(f"TechnicalDetailsView: Added code execution result (success={success})")

    # ===========================================================================
    # ACTIONS TAB METHODS
    # ===========================================================================

    def append_action_start(self, action_type: str, details: str = "", action_data: dict = None):
        """Append action execution start.

        Args:
            action_type: Type of action
            details: Optional action details (deprecated - use action_data)
            action_data: Full action dictionary with all parameters
        """
        # Create a frame for this action
        import time
        timestamp = time.strftime("%H:%M:%S")

        frame = QFrame()
        frame.setStyleSheet(
            """
            QFrame {
                border: 2px solid #0066cc;
                border-radius: 6px;
                background: white;
                padding: 12px;
                margin: 4px;
            }
            """
        )

        frame_layout = QVBoxLayout(frame)
        frame_layout.setSpacing(8)

        # Header
        header_label = QLabel(f"<b style='color: #0066cc; font-size: 13px;'>⚡ {action_type}</b> <span style='color: #999; font-size: 11px;'>({timestamp})</span>")
        frame_layout.addWidget(header_label)

        # Parameters (if provided)
        if action_data:
            params = {k: v for k, v in action_data.items() if k != "type"}
            if params:
                params_html = "<table style='font-size: 11px; margin-left: 12px;'>"
                for key, value in params.items():
                    if isinstance(value, str) and len(value) > 150:
                        display_value = value[:150] + f"... ({len(value)} chars)"
                    else:
                        display_value = str(value)
                    params_html += f"<tr><td style='color: #666; padding-right: 8px;'>{key}:</td><td>{display_value}</td></tr>"
                params_html += "</table>"

                params_label = QLabel(params_html)
                frame_layout.addWidget(params_label)

        # Status indicator
        status_label = QLabel("<span style='color: #0066cc;'>⏳ Executing...</span>")
        status_label.setObjectName("status_label")
        frame_layout.addWidget(status_label)

        # Store reference for updating
        frame.setProperty("action_type", action_type)

        # Insert before the stretch
        self.action_layout.insertWidget(self.action_layout.count() - 1, frame)

    def append_action_result(self, action_type: str, success: bool, message: str, result_data: dict = None):
        """Append action execution result.

        Args:
            action_type: Type of action
            success: Whether action succeeded
            message: Result message
            result_data: Optional result data
        """
        # Find the last action frame with this action_type
        for i in range(self.action_layout.count() - 1, -1, -1):
            item = self.action_layout.itemAt(i)
            if item and item.widget():
                frame = item.widget()
                if frame.property("action_type") == action_type:
                    # Update the status label
                    status_label = frame.findChild(QLabel, "status_label")
                    if status_label:
                        icon = "✅" if success else "❌"
                        color = "#00aa00" if success else "#cc0000"
                        status_label.setText(f"<span style='color: {color};'>{icon} {message}</span>")

                    # Update border color
                    if success:
                        frame.setStyleSheet(
                            """
                            QFrame {
                                border: 2px solid #00aa00;
                                border-radius: 6px;
                                background: white;
                                padding: 12px;
                                margin: 4px;
                            }
                            """
                        )
                    else:
                        frame.setStyleSheet(
                            """
                            QFrame {
                                border: 2px solid #cc0000;
                                border-radius: 6px;
                                background: white;
                                padding: 12px;
                                margin: 4px;
                            }
                            """
                        )
                    break

    # ===========================================================================
    # UTILITY METHODS
    # ===========================================================================

    def switch_to_code_tab(self):
        """Switch to the code execution tab."""
        self.tabs.setCurrentIndex(1)

    def switch_to_actions_tab(self):
        """Switch to the actions tab."""
        self.tabs.setCurrentIndex(2)

    def clear_all_tabs(self):
        """Clear all content from all tabs."""
        # Clear reasoning
        while self.reasoning_layout.count() > 1:  # Keep the stretch
            item = self.reasoning_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Clear code execution
        while self.code_layout.count() > 1:  # Keep the stretch
            item = self.code_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Clear actions
        while self.action_layout.count() > 1:  # Keep the stretch
            item = self.action_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.current_iteration = None
        self.current_code_section = None

        logger.debug("TechnicalDetailsView: Cleared all tabs")
