"""Technical details view widget - displays reasoning logs, code execution, and actions."""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTextEdit,
    QLabel,
    QTabWidget,
    QPushButton,
    QHBoxLayout,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from loguru import logger

try:
    import markdown
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False
    logger.warning("markdown library not available - install with: pip install markdown")


class TechnicalDetailsView(QWidget):
    """Widget for displaying technical details during agent execution.

    Responsible for:
    - Showing reasoning iterations (thought process)
    - Showing code execution details (stdout, stderr, results)
    - Showing action execution history

    Does NOT show:
    - Final conversation output (that's in ConversationView)
    """

    def __init__(self):
        """Initialize technical details view."""
        super().__init__()
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

        # Tab 1: Reasoning Log
        self.reasoning_log = QTextEdit()
        self.reasoning_log.setReadOnly(True)
        self.reasoning_log.setPlaceholderText("Reasoning iterations will appear here...")
        self._set_monospace_font(self.reasoning_log)
        self.tabs.addTab(self.reasoning_log, "🧠 Reasoning")

        # Tab 2: Code Execution
        self.code_execution_log = QTextEdit()
        self.code_execution_log.setReadOnly(True)
        self.code_execution_log.setPlaceholderText("Code execution details will appear here...")
        self._set_monospace_font(self.code_execution_log)
        self.tabs.addTab(self.code_execution_log, "💻 Code Execution")

        # Tab 3: Action History
        self.action_history_log = QTextEdit()
        self.action_history_log.setReadOnly(True)
        self.action_history_log.setPlaceholderText("Action execution history will appear here...")
        self._set_monospace_font(self.action_history_log)
        self.tabs.addTab(self.action_history_log, "⚡ Actions")

    def _set_monospace_font(self, text_edit: QTextEdit):
        """Set monospace font for better code/log display.

        Args:
            text_edit: QTextEdit widget to style
        """
        font = QFont("Courier New")
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setPointSize(10)
        text_edit.setFont(font)

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

    # Reasoning Log Methods
    def append_reasoning_iteration(self, iteration: int, max_iterations: int):
        """Append reasoning iteration marker.

        Args:
            iteration: Current iteration number
            max_iterations: Maximum iterations allowed
        """
        self.reasoning_log.append(
            f"<b style='color: #0066cc;'>═══ Iteration {iteration}/{max_iterations} ═══</b>"
        )
        logger.debug(f"TechnicalDetailsView: Added iteration {iteration}/{max_iterations}")

    def append_reasoning_thought(self, thought: str):
        """Append reasoning thought to log.

        Args:
            thought: Thought/reasoning text (FULL, UNTRUNCATED, in MARKDOWN format)
        """
        # Convert markdown to HTML and show EXACT reasoning - no truncation, no summarization
        html_content = self._markdown_to_html(thought)
        self.reasoning_log.append(f"<b style='color: #0066cc;'>💭 Complete Reasoning:</b>")
        self.reasoning_log.insertHtml(f"<div style='margin-left: 16px;'>{html_content}</div>")
        self.reasoning_log.append("")
        self.reasoning_log.append("")

    def append_reasoning_observation(self, observation: str):
        """Append observation to reasoning log.

        Args:
            observation: Observation text (FULL, EXACT)
        """
        self.reasoning_log.append(f"<b style='color: #00aa00;'>🔍 Observations:</b>")
        self.reasoning_log.append(f"<div style='margin-left: 16px; white-space: pre-wrap;'>{observation}</div>")
        self.reasoning_log.append("")

    def append_reasoning_insights(self, insights: str):
        """Append insights gained to reasoning log.

        Args:
            insights: Insights text (FULL, EXACT)
        """
        self.reasoning_log.append(f"<b style='color: #cc6600;'>💡 Insights Gained:</b>")
        self.reasoning_log.append(f"<div style='margin-left: 16px; white-space: pre-wrap;'>{insights}</div>")
        self.reasoning_log.append("")

    def append_reasoning_action_plan(self, actions: list):
        """Append action plan to reasoning log.

        Args:
            actions: List of planned actions (FULL details shown)
        """
        self.reasoning_log.append(f"<b style='color: #cc6600;'>⚡ Actions Planned:</b> {len(actions)}")
        self.reasoning_log.append("<div style='margin-left: 16px;'>")

        for i, action in enumerate(actions, 1):
            action_type = action.get("type", "unknown")

            # Show full action details, not just type
            self.reasoning_log.append(f"<b>{i}. {action_type}</b>")

            # Show action parameters (except 'type')
            params = {k: v for k, v in action.items() if k != "type"}
            if params:
                for key, value in params.items():
                    # Truncate very long values but show substantial portion
                    if isinstance(value, str) and len(value) > 500:
                        display_value = value[:500] + "... (truncated)"
                    else:
                        display_value = str(value)
                    self.reasoning_log.append(f"   • {key}: {display_value}")

        self.reasoning_log.append("</div>")
        self.reasoning_log.append("")

    def append_reasoning_completion(self, success: bool, message: str = "", summary_data: dict = None):
        """Append reasoning completion status with optional summary.

        Args:
            success: Whether reasoning completed successfully
            message: Optional completion message
            summary_data: Optional dictionary with summary info (iterations, actions_count, etc.)
        """
        self.reasoning_log.append("<div style='border-top: 2px solid #0066cc; margin: 16px 0; padding-top: 16px;'>")

        if success:
            self.reasoning_log.append(f"<b style='color: #00aa00; font-size: 14px;'>✓ Reasoning Complete</b>")
        else:
            self.reasoning_log.append(f"<b style='color: #cc0000; font-size: 14px;'>✗ Reasoning Failed</b>")

        if message:
            self.reasoning_log.append(f"<i style='color: #666;'>{message}</i>")

        # Show summary data if provided
        if summary_data:
            self.reasoning_log.append("<div style='margin-top: 8px; margin-left: 16px; font-family: monospace;'>")
            for key, value in summary_data.items():
                self.reasoning_log.append(f"  <b>{key}:</b> {value}")
            self.reasoning_log.append("</div>")

        self.reasoning_log.append("</div>")
        self.reasoning_log.append("")

    # Code Execution Methods
    def append_code_execution_start(self, code: str):
        """Append code execution start.

        Args:
            code: Python code being executed (FULL, EXACT code shown)
        """
        # Show EXACT code - no truncation
        self.code_execution_log.append(
            "<div style='background: #f5f5f5; border-left: 4px solid #0066cc; padding: 12px; margin: 8px 0;'>"
            "<b style='color: #0066cc;'>▶ Executing Code:</b><br/>"
            f"<pre style='margin: 8px 0; white-space: pre-wrap; font-family: \"Courier New\", monospace; font-size: 12px;'>{code}</pre>"
            "</div>"
        )
        logger.debug(f"TechnicalDetailsView: Added code execution start ({len(code)} chars)")

    def append_code_execution_result(self, result_data: dict):
        """Append code execution result.

        Args:
            result_data: Dictionary with execution results (stdout, stderr, result, error)
        """
        success = result_data.get("success", False)
        stdout = result_data.get("stdout", "")
        stderr = result_data.get("stderr", "")
        result = result_data.get("result")
        error = result_data.get("error")
        exec_time = result_data.get("execution_time", 0)

        html = "<div style='background: #f5f5f5; border-left: 4px solid {}; padding: 8px; margin: 4px 0;'>".format(
            "#00aa00" if success else "#cc0000"
        )

        if success:
            html += f"<b style='color: #00aa00;'>✓ Execution Successful</b> ({exec_time:.3f}s)<br/>"

            if stdout:
                html += "<br/><b>Output:</b><br/>"
                html += f"<pre style='margin: 4px 0;'>{stdout}</pre>"

            if result:
                html += "<br/><b>Result:</b><br/>"
                html += f"<code>{result}</code>"

            if stderr:
                html += "<br/><b style='color: #cc6600;'>Warnings:</b><br/>"
                html += f"<pre style='margin: 4px 0; color: #cc6600;'>{stderr}</pre>"
        else:
            html += f"<b style='color: #cc0000;'>✗ Execution Failed</b> ({exec_time:.3f}s)<br/>"

            if error:
                html += "<br/><b>Error:</b><br/>"
                html += f"<pre style='margin: 4px 0; color: #cc0000;'>{error}</pre>"

            if stderr:
                html += "<br/><b>STDERR:</b><br/>"
                html += f"<pre style='margin: 4px 0;'>{stderr}</pre>"

        html += "</div>"
        self.code_execution_log.append(html)
        logger.debug(f"TechnicalDetailsView: Added code execution result (success={success})")

    # Action History Methods
    def append_action_start(self, action_type: str, details: str = "", action_data: dict = None):
        """Append action execution start.

        Args:
            action_type: Type of action
            details: Optional action details (deprecated - use action_data)
            action_data: Full action dictionary with all parameters
        """
        self.action_history_log.append(f"<b style='color: #0066cc;'>⚡ Executing: {action_type}</b>")

        # Show full action parameters
        if action_data:
            params = {k: v for k, v in action_data.items() if k != "type"}
            if params:
                self.action_history_log.append("<div style='margin-left: 16px; font-family: monospace;'>")
                for key, value in params.items():
                    # Show substantial portion of parameters
                    if isinstance(value, str) and len(value) > 300:
                        display_value = value[:300] + f"... (+{len(value)-300} chars)"
                    else:
                        display_value = str(value)
                    self.action_history_log.append(f"  {key}: {display_value}")
                self.action_history_log.append("</div>")
        elif details:
            self.action_history_log.append(f"<i style='margin-left: 16px;'>{details}</i>")

        logger.debug(f"TechnicalDetailsView: Added action start: {action_type}")

    def append_action_result(self, action_type: str, success: bool, message: str, result_data: dict = None):
        """Append action execution result.

        Args:
            action_type: Type of action
            success: Whether action succeeded
            message: Result message
            result_data: Optional additional result data from ActionResult.data
        """
        icon = "✓" if success else "✗"
        color = "#00aa00" if success else "#cc0000"

        self.action_history_log.append(
            f"<b style='color: {color};'>{icon} {action_type}:</b> {message}"
        )

        # Show additional result data if available
        if result_data:
            self.action_history_log.append("<div style='margin-left: 16px; font-family: monospace; font-size: 11px;'>")
            for key, value in result_data.items():
                # Skip very verbose fields but show important ones
                if key in ["items", "memories", "projects", "notes", "tasks"]:
                    # Just show count for collections
                    count = len(value) if isinstance(value, list) else "unknown"
                    self.action_history_log.append(f"  {key}: {count} items")
                elif isinstance(value, str) and len(value) > 200:
                    self.action_history_log.append(f"  {key}: {value[:200]}... (+{len(value)-200} chars)")
                else:
                    self.action_history_log.append(f"  {key}: {value}")
            self.action_history_log.append("</div>")

        self.action_history_log.append("")
        logger.debug(f"TechnicalDetailsView: Added action result: {action_type} (success={success})")

    def append_actions_summary(self, total: int, succeeded: int, failed: int):
        """Append action execution summary.

        Args:
            total: Total actions executed
            succeeded: Number of successful actions
            failed: Number of failed actions
        """
        self.action_history_log.append(
            f"<b>Action Summary:</b> {succeeded}/{total} succeeded, {failed} failed"
        )
        self.action_history_log.append("")

    # Utility Methods
    def clear_reasoning_log(self):
        """Clear reasoning log."""
        self.reasoning_log.clear()
        logger.debug("TechnicalDetailsView: Cleared reasoning log")

    def clear_code_execution_log(self):
        """Clear code execution log."""
        self.code_execution_log.clear()
        logger.debug("TechnicalDetailsView: Cleared code execution log")

    def clear_action_history_log(self):
        """Clear action history log."""
        self.action_history_log.clear()
        logger.debug("TechnicalDetailsView: Cleared action history log")

    def clear_all_tabs(self):
        """Clear all technical detail logs."""
        self.clear_reasoning_log()
        self.clear_code_execution_log()
        self.clear_action_history_log()
        logger.info("TechnicalDetailsView: Cleared all logs")

    def switch_to_reasoning_tab(self):
        """Switch to reasoning tab."""
        self.tabs.setCurrentIndex(0)

    def switch_to_code_tab(self):
        """Switch to code execution tab."""
        self.tabs.setCurrentIndex(1)

    def switch_to_actions_tab(self):
        """Switch to actions tab."""
        self.tabs.setCurrentIndex(2)
