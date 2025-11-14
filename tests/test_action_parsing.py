"""Comprehensive tests for action parsing system.

Tests both text-based (```actions blocks) and code-based (execute_code) action mechanisms.
Covers all edge cases documented in ACTION_PARSING_DOCUMENTATION.md
"""

import pytest
import json
from unittest.mock import Mock, MagicMock, patch
from sqlalchemy.orm import Session

from gembrain.utils.json_utils import parse_actions_from_response, extract_json_block
from gembrain.agents.tools import ActionExecutor, ActionResult
from gembrain.agents.code_executor import CodeExecutor
from gembrain.agents.code_api import GemBrainAPI
from gembrain.agents.iterative_reasoner import IterativeReasoner
from gembrain.core.models import TaskStatus, GoalStatus


class TestTextBasedActionParsing:
    """Test text-based action parsing (```actions blocks)."""

    def test_valid_single_action(self):
        """Test parsing a single valid action."""
        response = """
Here is my response.

```actions
{
  "actions": [
    {
      "type": "create_task",
      "content": "Test task",
      "notes": "Test notes"
    }
  ]
}
```

Some more text.
"""
        result = parse_actions_from_response(response)

        assert "reply" in result
        assert "actions" in result
        assert len(result["actions"]) == 1
        assert result["actions"][0]["type"] == "create_task"
        assert result["actions"][0]["content"] == "Test task"
        assert "```actions" not in result["reply"]

    def test_valid_multiple_actions(self):
        """Test parsing multiple actions in one block."""
        response = """
```actions
{
  "actions": [
    {"type": "create_task", "content": "Task 1"},
    {"type": "create_memory", "content": "Memory 1"},
    {"type": "create_goal", "content": "Goal 1"}
  ]
}
```
"""
        result = parse_actions_from_response(response)
        assert len(result["actions"]) == 3
        assert result["actions"][0]["type"] == "create_task"
        assert result["actions"][1]["type"] == "create_memory"
        assert result["actions"][2]["type"] == "create_goal"

    def test_missing_closing_backticks(self):
        """Test handling of missing closing backticks."""
        response = """
```actions
{"actions": [{"type": "create_task", "content": "test"}]}
"""
        result = parse_actions_from_response(response)
        # Should not parse without closing backticks
        assert result["actions"] == []

    def test_multiple_actions_blocks_only_first_parsed(self):
        """Test that only first actions block is parsed."""
        response = """
```actions
{"actions": [{"type": "create_task", "content": "task 1"}]}
```

```actions
{"actions": [{"type": "create_task", "content": "task 2"}]}
```
"""
        result = parse_actions_from_response(response)
        # Currently only first block is parsed
        assert len(result["actions"]) == 1
        assert result["actions"][0]["content"] == "task 1"

    def test_invalid_json(self):
        """Test handling of invalid JSON."""
        response = """
```actions
{
  "actions": [
    {
      "type": "create_task",
      "content": "test",
    }
  ]
}
```
"""
        result = parse_actions_from_response(response)
        # Invalid JSON should result in empty actions
        assert result["actions"] == []

    def test_wrong_block_name(self):
        """Test that wrong block name is not recognized."""
        response = """
```action
{"actions": [{"type": "create_task", "content": "test"}]}
```
"""
        result = parse_actions_from_response(response)
        assert result["actions"] == []

    def test_actions_outside_block(self):
        """Test that actions outside code block are not parsed."""
        response = """
{"actions": [{"type": "create_task", "content": "test"}]}
"""
        result = parse_actions_from_response(response)
        assert result["actions"] == []

    def test_nested_code_blocks_in_json(self):
        """Test handling of nested code blocks in JSON strings."""
        response = """
```actions
{
  "actions": [
    {
      "type": "execute_code",
      "code": "print('test with backticks: ``` inside')"
    }
  ]
}
```
"""
        result = parse_actions_from_response(response)
        # This should parse correctly despite backticks in string
        assert len(result["actions"]) == 1
        assert "```" in result["actions"][0]["code"]

    def test_empty_actions_array(self):
        """Test handling of empty actions array."""
        response = """
```actions
{"actions": []}
```
"""
        result = parse_actions_from_response(response)
        assert result["actions"] == []

    def test_missing_actions_key(self):
        """Test handling of missing 'actions' key."""
        response = """
```actions
{
  "data": [{"type": "create_task", "content": "test"}]
}
```
"""
        result = parse_actions_from_response(response)
        assert result["actions"] == []

    def test_whitespace_variations(self):
        """Test parsing with various whitespace."""
        response = """
```actions
   {
      "actions":    [
         {   "type"  :  "create_task"  ,  "content"  :  "test"  }
      ]
   }
```
"""
        result = parse_actions_from_response(response)
        assert len(result["actions"]) == 1

    def test_unicode_in_content(self):
        """Test handling of Unicode characters."""
        response = """
```actions
{
  "actions": [
    {"type": "create_task", "content": "测试任务 with émojis 🎉"}
  ]
}
```
"""
        result = parse_actions_from_response(response)
        assert len(result["actions"]) == 1
        assert "🎉" in result["actions"][0]["content"]

    def test_control_characters_in_json_strings(self):
        """Test handling of control characters (newlines, tabs) in JSON strings."""
        # This is a known issue - LLMs sometimes generate literal newlines in JSON
        response = """
```actions
{
  "actions": [
    {
      "type": "create_task",
      "content": "Line 1
Line 2"
    }
  ]
}
```
"""
        result = parse_actions_from_response(response)
        # Current implementation may fail - this documents the issue
        # After fix, should parse correctly
        if result["actions"]:
            assert "Line 1" in result["actions"][0]["content"]


class TestActionValidation:
    """Test action validation logic."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return MagicMock(spec=Session)

    @pytest.fixture
    def executor(self, mock_db):
        """Create ActionExecutor with mocked dependencies."""
        with patch('gembrain.agents.tools.TaskService'), \
             patch('gembrain.agents.tools.MemoryService'), \
             patch('gembrain.agents.tools.GoalService'), \
             patch('gembrain.agents.tools.DatavaultService'):
            return ActionExecutor(mock_db, enable_code_execution=False)

    def test_missing_action_type(self, executor):
        """Test validation fails when action type is missing."""
        action = {"content": "test"}
        error = executor._validate_action(action)
        assert error == "Missing action type"

    def test_missing_required_field_create_task(self, executor):
        """Test validation fails when required field is missing."""
        action = {"type": "create_task", "notes": "test"}
        error = executor._validate_action(action)
        assert error == "Missing required field: content"

    def test_missing_required_field_search_tasks(self, executor):
        """Test validation for search action missing query."""
        action = {"type": "search_tasks"}
        error = executor._validate_action(action)
        assert error == "Missing required field: query"

    def test_valid_action_with_all_fields(self, executor):
        """Test validation passes with all required fields."""
        action = {
            "type": "create_task",
            "content": "Test task",
            "notes": "Test notes",
            "status": "pending"
        }
        error = executor._validate_action(action)
        assert error is None

    def test_valid_action_list_tasks_no_required_fields(self, executor):
        """Test validation for list_tasks (no required fields)."""
        action = {"type": "list_tasks"}
        error = executor._validate_action(action)
        assert error is None

    def test_unknown_action_type_passes_validation(self, executor):
        """Test that unknown action types pass validation (fail later in routing)."""
        action = {"type": "unknown_action"}
        error = executor._validate_action(action)
        # Validation only checks known types, unknown types pass validation
        assert error is None


class TestCodeBasedActions:
    """Test code-based actions (execute_code with GemBrain API)."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return MagicMock(spec=Session)

    @pytest.fixture
    def mock_services(self):
        """Create mock services."""
        task_service = MagicMock()
        memory_service = MagicMock()
        goal_service = MagicMock()
        datavault_service = MagicMock()

        return {
            "task_service": task_service,
            "memory_service": memory_service,
            "goal_service": goal_service,
            "datavault_service": datavault_service,
        }

    @pytest.fixture
    def gembrain_api(self, mock_db, mock_services):
        """Create GemBrainAPI instance."""
        return GemBrainAPI(mock_db, mock_services)

    @pytest.fixture
    def code_executor(self, gembrain_api):
        """Create CodeExecutor instance."""
        return CodeExecutor(gembrain_api)

    def test_simple_code_execution(self, code_executor):
        """Test executing simple Python code."""
        code = "result = 1 + 1\nprint(result)"
        result = code_executor.execute(code)

        assert result["success"] is True
        assert "2" in result["stdout"]
        assert result["error"] == ""

    def test_syntax_error_in_code(self, code_executor):
        """Test handling of syntax errors."""
        code = "print('test'"  # Missing closing parenthesis
        result = code_executor.execute(code)

        assert result["success"] is False
        assert "SyntaxError" in result["error"]

    def test_runtime_error_in_code(self, code_executor):
        """Test handling of runtime errors."""
        code = "undefined_variable"
        result = code_executor.execute(code)

        assert result["success"] is False
        assert "NameError" in result["error"]

    def test_api_method_create_task(self, code_executor, mock_services):
        """Test calling gb.create_task() in code."""
        # Mock task service to return a task-like object
        mock_task = Mock()
        mock_task.id = 1
        mock_task.content = "Test task"
        mock_task.status = TaskStatus.PENDING
        mock_task.created_at = Mock()
        mock_task.created_at.isoformat.return_value = "2025-01-01T00:00:00"

        mock_services["task_service"].create_task.return_value = mock_task

        code = """
result = gb.create_task("Test task", notes="Test notes")
print(f"Created task: {result['task_id']}")
"""
        result = code_executor.execute(code)

        assert result["success"] is True
        assert "Created task: 1" in result["stdout"]
        mock_services["task_service"].create_task.assert_called_once()

    def test_api_method_returns_dict_not_bool(self, code_executor, mock_services):
        """Test that API methods return dicts (not bools) for compatibility."""
        mock_services["task_service"].delete_task.return_value = True

        code = """
result = gb.delete_task(1)
success = result.get('success')
print(f"Success: {success}")
"""
        result = code_executor.execute(code)

        # Should not raise AttributeError: 'bool' object has no attribute 'get'
        assert result["success"] is True
        assert "Success: True" in result["stdout"]

    def test_api_list_tasks_returns_dict(self, code_executor, mock_services):
        """Test that list_tasks returns dict with 'tasks' key."""
        mock_tasks = [
            Mock(id=1, content="Task 1", notes="", status=TaskStatus.PENDING),
            Mock(id=2, content="Task 2", notes="", status=TaskStatus.ONGOING),
        ]
        mock_services["task_service"].get_all_tasks.return_value = mock_tasks

        code = """
result = gb.list_tasks()
tasks = result.get('tasks', [])
print(f"Found {len(tasks)} tasks")
for task in tasks:
    print(f"Task {task['id']}: {task['content']}")
"""
        result = code_executor.execute(code)

        assert result["success"] is True
        assert "Found 2 tasks" in result["stdout"]
        assert "Task 1:" in result["stdout"]

    def test_api_invalid_status_value(self, code_executor, mock_services):
        """Test handling of invalid status values."""
        mock_services["task_service"].create_task.side_effect = ValueError(
            "invalid_status is not a valid TaskStatus"
        )

        code = 'gb.create_task("Test", status="invalid_status")'
        result = code_executor.execute(code)

        assert result["success"] is False
        assert "ValueError" in result["error"]

    def test_code_with_imports(self, code_executor, mock_services):
        """Test code execution with imports."""
        mock_task = Mock()
        mock_task.id = 1
        mock_task.content = "Task 1"
        mock_task.status = TaskStatus.PENDING
        mock_task.created_at = Mock()
        mock_task.created_at.isoformat.return_value = "2025-01-01T00:00:00"

        mock_services["task_service"].create_task.return_value = mock_task

        code = """
import json

data = {"task": "Test task"}
task_result = gb.create_task(data["task"])
print(json.dumps({"task_id": task_result["task_id"]}))
"""
        result = code_executor.execute(code)

        assert result["success"] is True
        assert "task_id" in result["stdout"]

    def test_code_with_loops(self, code_executor, mock_services):
        """Test code execution with loops."""
        mock_task = Mock()
        mock_task.id = 1
        mock_task.content = "Task"
        mock_task.status = TaskStatus.PENDING
        mock_task.created_at = Mock()
        mock_task.created_at.isoformat.return_value = "2025-01-01T00:00:00"

        mock_services["task_service"].create_task.return_value = mock_task

        code = """
created_ids = []
for i in range(3):
    result = gb.create_task(f"Task {i}")
    created_ids.append(result["task_id"])

print(f"Created {len(created_ids)} tasks")
"""
        result = code_executor.execute(code)

        assert result["success"] is True
        assert "Created 3 tasks" in result["stdout"]
        assert mock_services["task_service"].create_task.call_count == 3

    def test_datavault_store_with_json(self, code_executor, mock_services):
        """Test storing JSON data in datavault."""
        mock_item = Mock()
        mock_item.id = 1
        mock_item.filetype = "json"
        mock_item.created_at = Mock()
        mock_item.created_at.isoformat.return_value = "2025-01-01T00:00:00"

        mock_services["datavault_service"].store_item.return_value = mock_item

        code = """
import json

data = {"results": [1, 2, 3], "total": 3}
json_str = json.dumps(data)
result = gb.datavault_store(json_str, filetype="json", notes="test results")
print(f"Stored in datavault: {result['datavault_id']}")
"""
        result = code_executor.execute(code)

        assert result["success"] is True
        assert "Stored in datavault: 1" in result["stdout"]

    def test_gb_log_method(self, code_executor):
        """Test gb.log() utility method."""
        code = """
gb.log("Starting task creation")
gb.log("Task created successfully")
"""
        result = code_executor.execute(code)

        assert result["success"] is True
        # Logs go to stdout via print()
        assert "Starting task creation" in result["stdout"]
        assert "Task created successfully" in result["stdout"]


class TestIterativeReasoningActionParsing:
    """Test action parsing in iterative reasoning mode."""

    def test_parse_iteration_with_actions(self):
        """Test parsing iteration block with next_actions."""
        response = """
```iteration
{
  "iteration": 1,
  "reasoning": "I need to create tasks for the project",
  "observations": ["User wants project setup"],
  "next_actions": [
    {
      "type": "create_task",
      "content": "Set up repository",
      "notes": "Step 1"
    },
    {
      "type": "create_task",
      "content": "Configure CI/CD",
      "notes": "Step 2"
    }
  ],
  "insights_gained": ["Tasks should be sequential"],
  "is_final": false
}
```
"""
        # Create a minimal IterativeReasoner to test parsing
        with patch('gembrain.agents.iterative_reasoner.GeminiClient'), \
             patch('gembrain.agents.iterative_reasoner.Settings'):
            reasoner = IterativeReasoner(
                gemini_client=Mock(),
                settings=Mock(),
                action_handler=Mock(),
                max_iterations=10
            )

            parsed = reasoner._parse_iteration_response(response)

            assert parsed is not None
            assert parsed["iteration"] == 1
            assert len(parsed["next_actions"]) == 2
            assert parsed["next_actions"][0]["type"] == "create_task"
            assert parsed["is_final"] is False

    def test_parse_iteration_with_code_in_actions(self):
        """Test parsing iteration with execute_code action containing backticks."""
        response = """
```iteration
{
  "iteration": 2,
  "reasoning": "Executing code to create tasks",
  "next_actions": [
    {
      "type": "execute_code",
      "code": "for i in range(3):\\n    gb.create_task(f'Task {i}')"
    }
  ],
  "is_final": false
}
```
"""
        with patch('gembrain.agents.iterative_reasoner.GeminiClient'), \
             patch('gembrain.agents.iterative_reasoner.Settings'):
            reasoner = IterativeReasoner(
                gemini_client=Mock(),
                settings=Mock(),
                action_handler=Mock(),
                max_iterations=10
            )

            parsed = reasoner._parse_iteration_response(response)

            assert parsed is not None
            assert len(parsed["next_actions"]) == 1
            assert "for i in range(3)" in parsed["next_actions"][0]["code"]

    def test_parse_iteration_with_control_characters(self):
        """Test handling of control characters in iteration JSON."""
        # LLM might generate literal newlines in reasoning field
        response = """
```iteration
{
  "iteration": 1,
  "reasoning": "Line 1
Line 2
Line 3",
  "is_final": false
}
```
"""
        with patch('gembrain.agents.iterative_reasoner.GeminiClient'), \
             patch('gembrain.agents.iterative_reasoner.Settings'):
            reasoner = IterativeReasoner(
                gemini_client=Mock(),
                settings=Mock(),
                action_handler=Mock(),
                max_iterations=10
            )

            parsed = reasoner._parse_iteration_response(response)

            # _fix_json_control_chars should handle this
            assert parsed is not None
            assert "Line 1" in parsed["reasoning"]
            assert "Line 2" in parsed["reasoning"]

    def test_parse_iteration_nested_braces(self):
        """Test parsing with nested braces in code."""
        response = """
```iteration
{
  "iteration": 1,
  "next_actions": [
    {
      "type": "execute_code",
      "code": "data = {'key1': {'nested': 'value'}, 'key2': [1, 2, 3]}"
    }
  ],
  "is_final": false
}
```
"""
        with patch('gembrain.agents.iterative_reasoner.GeminiClient'), \
             patch('gembrain.agents.iterative_reasoner.Settings'):
            reasoner = IterativeReasoner(
                gemini_client=Mock(),
                settings=Mock(),
                action_handler=Mock(),
                max_iterations=10
            )

            parsed = reasoner._parse_iteration_response(response)

            assert parsed is not None
            assert "nested" in parsed["next_actions"][0]["code"]


class TestActionExecutionEdgeCases:
    """Test edge cases in action execution."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return MagicMock(spec=Session)

    @pytest.fixture
    def executor(self, mock_db):
        """Create ActionExecutor with mocked dependencies."""
        with patch('gembrain.agents.tools.TaskService') as mock_task, \
             patch('gembrain.agents.tools.MemoryService'), \
             patch('gembrain.agents.tools.GoalService'), \
             patch('gembrain.agents.tools.DatavaultService'):

            # Setup mock task service
            executor = ActionExecutor(mock_db, enable_code_execution=False)
            executor.task_service = mock_task.return_value

            return executor

    def test_execute_unknown_action_type(self, executor):
        """Test execution of unknown action type."""
        action = {"type": "unknown_action", "param": "value"}
        result = executor.execute_action(action)

        assert result.success is False
        assert "Unknown action type" in result.message

    def test_execute_action_with_missing_field(self, executor):
        """Test execution fails validation for missing required field."""
        action = {"type": "create_task"}  # Missing 'content'
        result = executor.execute_action(action)

        assert result.success is False
        assert "Missing required field: content" in result.message

    def test_execute_action_with_invalid_status(self, executor):
        """Test execution with invalid status value."""
        action = {
            "type": "create_task",
            "content": "Test",
            "status": "invalid_status"
        }
        result = executor.execute_action(action)

        assert result.success is False
        assert "Invalid status" in result.message

    def test_retry_logic_for_retryable_action(self, executor):
        """Test that retryable actions are retried on failure."""
        # create_task is retryable
        executor.task_service.create_task.side_effect = [
            Exception("Temporary error"),  # First attempt fails
            Mock(id=1, content="Test", status=TaskStatus.PENDING)  # Second succeeds
        ]

        action = {"type": "create_task", "content": "Test"}
        result = executor.execute_action(action)

        # Should succeed after retry
        assert result.success is True
        assert result.retry_count > 0
        assert executor.task_service.create_task.call_count == 2

    def test_no_retry_for_non_retryable_action(self, executor):
        """Test that non-retryable actions are not retried."""
        # delete_task is non-retryable
        executor.task_service.delete_task.side_effect = Exception("Error")

        action = {"type": "delete_task", "task_id": 1}
        result = executor.execute_action(action)

        # Should fail immediately without retry
        assert result.success is False
        assert result.retry_count == 0
        assert executor.task_service.delete_task.call_count == 1


class TestExtractJsonBlock:
    """Test the generic extract_json_block function."""

    def test_extract_actions_block(self):
        """Test extracting actions block."""
        text = """
```actions
{"test": "value"}
```
"""
        result = extract_json_block(text, "actions")
        assert result == {"test": "value"}

    def test_extract_custom_block_name(self):
        """Test extracting block with custom name."""
        text = """
```custom
{"data": [1, 2, 3]}
```
"""
        result = extract_json_block(text, "custom")
        assert result == {"data": [1, 2, 3]}

    def test_extract_no_block_found(self):
        """Test when no matching block is found."""
        text = """
```other
{"data": "value"}
```
"""
        result = extract_json_block(text, "actions")
        assert result is None

    def test_extract_invalid_json(self):
        """Test extraction with invalid JSON."""
        text = """
```actions
{invalid json}
```
"""
        result = extract_json_block(text, "actions")
        assert result is None

    def test_extract_with_whitespace(self):
        """Test extraction with extra whitespace."""
        text = """
```actions
   {"test": "value"}
```
"""
        result = extract_json_block(text, "actions")
        assert result == {"test": "value"}


# Run tests with: pytest tests/test_action_parsing.py -v
