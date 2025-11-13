"""Code execution engine for running Python code from agent."""

import sys
import io
import traceback
import time
from typing import Dict, Any, Tuple, Optional
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime
from loguru import logger


class CodeExecutor:
    """Executes Python code in the current environment with GemBrain API access."""

    def __init__(self, gembrain_api=None):
        """Initialize code executor.

        Args:
            gembrain_api: Optional GemBrainAPI instance for code to use
        """
        self.execution_namespace = {
            '__builtins__': __builtins__,
            'sys': sys,
        }

        # Inject GemBrain API if provided
        if gembrain_api:
            self.execution_namespace['gb'] = gembrain_api
            logger.info("✓ GemBrain API injected into code execution namespace as 'gb'")

        self.execution_count = 0
        self.execution_history = []

    def execute(self, code: str, timeout: int = 30) -> Dict[str, Any]:
        """Execute Python code with unrestricted access.

        Args:
            code: Python code to execute
            timeout: Execution timeout in seconds (not enforced - use responsibly)

        Returns:
            Dictionary with stdout, stderr, result, and success status
        """
        self.execution_count += 1
        execution_id = self.execution_count

        logger.warning("=" * 80)
        logger.warning(f"CODE EXECUTION #{execution_id} - STARTING")
        logger.warning(f"Timestamp: {datetime.now().isoformat()}")
        logger.warning("Code to execute:")
        logger.warning("-" * 40)
        for i, line in enumerate(code.split('\n'), 1):
            logger.warning(f"  {i:3d} | {line}")
        logger.warning("-" * 40)

        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        result = None
        error = None
        start_time = time.time()

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
            logger.error(f"Code execution #{execution_id} FAILED")
            logger.error(f"Error:\n{error}")

        execution_time = time.time() - start_time
        stdout_text = stdout_capture.getvalue()
        stderr_text = stderr_capture.getvalue()

        # Log results
        logger.warning(f"CODE EXECUTION #{execution_id} - FINISHED")
        logger.warning(f"Success: {success}")
        logger.warning(f"Execution time: {execution_time:.3f}s")
        if stdout_text:
            logger.info(f"STDOUT:\n{stdout_text}")
        if stderr_text:
            logger.warning(f"STDERR:\n{stderr_text}")
        if result is not None:
            logger.info(f"Result: {result}")
        if error:
            logger.error(f"Error:\n{error}")
        logger.warning("=" * 80)

        # Store in history
        execution_record = {
            "id": execution_id,
            "timestamp": datetime.now().isoformat(),
            "code": code,
            "success": success,
            "stdout": stdout_text,
            "stderr": stderr_text,
            "result": result,
            "error": error,
            "execution_time": execution_time,
        }
        self.execution_history.append(execution_record)

        return {
            "execution_id": execution_id,
            "success": success,
            "stdout": stdout_text,
            "stderr": stderr_text,
            "result": result,
            "error": error,
            "execution_time": execution_time,
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
        logger.warning("Code execution namespace RESET")

    def get_execution_history(self):
        """Get execution history.

        Returns:
            List of execution records
        """
        return self.execution_history.copy()

    def get_last_execution(self):
        """Get last execution record.

        Returns:
            Last execution record or None
        """
        return self.execution_history[-1] if self.execution_history else None
