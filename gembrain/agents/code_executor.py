"""Code execution engine for running Python code from agent."""

import sys
import io
import traceback
from typing import Dict, Any, Tuple
from contextlib import redirect_stdout, redirect_stderr
from loguru import logger


class CodeExecutor:
    """Executes Python code in the current environment."""

    def __init__(self):
        """Initialize code executor."""
        self.execution_namespace = {
            '__builtins__': __builtins__,
            'sys': sys,
        }

    def execute(self, code: str, timeout: int = 30) -> Dict[str, Any]:
        """Execute Python code with unrestricted access.

        Args:
            code: Python code to execute
            timeout: Execution timeout in seconds (not enforced - use responsibly)

        Returns:
            Dictionary with stdout, stderr, result, and success status
        """
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        result = None
        error = None

        logger.warning(f"Executing code:\n{code}")

        try:
            # Redirect stdout and stderr
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                # Execute the code with full access
                exec(code, self.execution_namespace)

                # Try to get the last expression result if available
                if code.strip():
                    lines = code.strip().split('\n')
                    last_line = lines[-1].strip()

                    # If last line is an expression, evaluate it
                    if last_line and not any(last_line.startswith(kw) for kw in
                        ['def ', 'class ', 'import ', 'from ', 'if ', 'for ', 'while ',
                         'try:', 'with ', 'print(', '@']):
                        try:
                            result = eval(last_line, self.execution_namespace)
                        except:
                            pass

            success = True

        except Exception as e:
            error = traceback.format_exc()
            success = False
            logger.error(f"Code execution failed:\n{error}")

        stdout_text = stdout_capture.getvalue()
        stderr_text = stderr_capture.getvalue()

        return {
            "success": success,
            "stdout": stdout_text,
            "stderr": stderr_text,
            "result": result,
            "error": error,
        }

    def add_to_namespace(self, name: str, value: Any):
        """Add variable to execution namespace.

        Args:
            name: Variable name
            value: Variable value
        """
        self.execution_namespace[name] = value

    def get_namespace(self) -> Dict[str, Any]:
        """Get current execution namespace.

        Returns:
            Namespace dictionary
        """
        return self.execution_namespace.copy()

    def reset_namespace(self):
        """Reset execution namespace to defaults."""
        self.execution_namespace = {
            '__builtins__': __builtins__,
            'sys': sys,
        }
        logger.info("Code execution namespace reset")
