# Action Parsing System - Improvement Plan

## Executive Summary

This document outlines a comprehensive plan to fix bugs and improve the architecture of GemBrain's action parsing system. The plan addresses **8 critical architectural issues** and **13 edge cases** discovered during testing.

**Priority Levels:**
- 🔴 **CRITICAL** - Security or data integrity issues
- 🟠 **HIGH** - Functionality-breaking bugs
- 🟡 **MEDIUM** - Quality of life improvements
- 🟢 **LOW** - Nice-to-have enhancements

---

## Phase 1: Critical Bug Fixes (Week 1)

### 1.1 Apply Control Character Fixing to Standard Mode 🔴 CRITICAL

**Issue**: LLMs generate literal newlines/tabs in JSON strings which cause `json.loads()` to fail with `JSONDecodeError`. This breaks action parsing in standard mode.

**Current State**:
- Iterative reasoning has `_fix_json_control_chars()` method that escapes control characters
- Standard mode (`parse_actions_from_response`) does NOT have this fix
- Results in failed action execution when LLM outputs multi-line content

**Impact**: **HIGH** - Users lose actions when LLM generates natural multi-line content

**Solution**:

```python
# File: gembrain/utils/json_utils.py

def _fix_json_control_chars(json_str: str) -> str:
    """Fix unescaped control characters in JSON string values.

    LLMs sometimes generate JSON with literal newlines/tabs in string values.
    This function escapes them properly so json.loads() can parse it.
    """
    result = []
    in_string = False
    escape_next = False

    for char in json_str:
        if escape_next:
            result.append(char)
            escape_next = False
            continue

        if char == '\\':
            result.append(char)
            escape_next = True
            continue

        if char == '"':
            in_string = not in_string
            result.append(char)
            continue

        if in_string:
            if char == '\n':
                result.append('\\n')
            elif char == '\r':
                result.append('\\r')
            elif char == '\t':
                result.append('\\t')
            elif ord(char) < 32:
                result.append(f'\\u{ord(char):04x}')
            else:
                result.append(char)
        else:
            result.append(char)

    return ''.join(result)


def extract_json_block(text: str, block_name: str = "actions") -> Optional[Dict[str, Any]]:
    """Extract JSON from a fenced code block in text."""
    pattern = rf"```{block_name}\s*\n(.*?)\n```"
    match = re.search(pattern, text, re.DOTALL)

    if not match:
        return None

    try:
        json_str = match.group(1).strip()
        # FIX: Apply control character escaping before parsing
        json_str_fixed = _fix_json_control_chars(json_str)
        return json.loads(json_str_fixed, strict=False)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON block '{block_name}': {e}")
        logger.debug(f"JSON content: {json_str[:500]}")
        return None
```

**Testing**:
```python
def test_control_characters_in_standard_mode():
    response = '''
```actions
{
  "actions": [
    {"type": "create_task", "content": "Line 1
Line 2
Line 3"}
  ]
}
```
'''
    result = parse_actions_from_response(response)
    assert len(result["actions"]) == 1
    assert "Line 1\nLine 2" in result["actions"][0]["content"]
```

**Effort**: 2 hours
**Dependencies**: None
**Risk**: Low (same logic already works in iterative mode)

---

### 1.2 Fix Nested Backticks in Action Parsing 🟠 HIGH

**Issue**: Current regex-based parser `r"```actions\s*\n(.*?)\n```"` breaks when JSON strings contain backticks.

**Example**:
```json
{
  "actions": [
    {
      "type": "execute_code",
      "code": "print('Code with backticks: ``` inside')"
    }
  ]
}
```

**Current Behavior**: Regex stops at first ``` inside the string, truncating the JSON

**Solution**: Use state machine parser (already exists in `IterativeReasoner._parse_iteration_response`!)

```python
# File: gembrain/utils/json_utils.py

def extract_json_block(text: str, block_name: str = "actions") -> Optional[Dict[str, Any]]:
    """Extract JSON from a fenced code block in text.

    Properly handles nested backticks in JSON strings using brace counting.
    """
    start_marker = f"```{block_name}"
    start_idx = text.find(start_marker)

    if start_idx == -1:
        return None

    # Find newline after opening marker
    json_start = text.find("\n", start_idx) + 1

    # Count braces to find end (handles nested backticks in strings)
    brace_count = 0
    in_string = False
    escape_next = False
    json_end = json_start

    for i in range(json_start, len(text)):
        char = text[i]

        if escape_next:
            escape_next = False
            continue

        if char == '\\':
            escape_next = True
            continue

        if char == '"':
            in_string = not in_string
            continue

        if not in_string:
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    json_end = i + 1
                    break

    if brace_count != 0:
        logger.error(f"Unbalanced braces in {block_name} block")
        return None

    json_str = text[json_start:json_end]

    try:
        json_str_fixed = _fix_json_control_chars(json_str)
        return json.loads(json_str_fixed, strict=False)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON block '{block_name}': {e}")
        return None
```

**Testing**: Test case already exists in `test_action_parsing.py::test_nested_code_blocks_in_json`

**Effort**: 3 hours
**Dependencies**: Requires control character fix (1.1)
**Risk**: Medium (more complex parsing logic)

---

### 1.3 Add JSON Schema Validation 🟡 MEDIUM

**Issue**: Current validation only checks for presence of required fields, not their types or values. Error messages are not actionable for LLMs.

**Solution**: Use Pydantic models for action validation with clear error messages.

```python
# File: gembrain/agents/action_schemas.py (NEW FILE)

from pydantic import BaseModel, Field, validator
from typing import Optional, Literal
from enum import Enum


class TaskStatusEnum(str, Enum):
    """Valid task statuses."""
    PENDING = "pending"
    ONGOING = "ongoing"
    PAUSED = "paused"
    COMPLETED = "completed"


class CreateTaskAction(BaseModel):
    """Schema for create_task action."""
    type: Literal["create_task"]
    content: str = Field(..., min_length=1, description="Task content (required)")
    notes: Optional[str] = Field("", description="Optional notes")
    status: TaskStatusEnum = Field(TaskStatusEnum.PENDING, description="Task status")


class UpdateTaskAction(BaseModel):
    """Schema for update_task action."""
    type: Literal["update_task"]
    task_id: int = Field(..., gt=0, description="Task ID to update")
    content: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[TaskStatusEnum] = None


class DeleteTaskAction(BaseModel):
    """Schema for delete_task action."""
    type: Literal["delete_task"]
    task_id: int = Field(..., gt=0, description="Task ID to delete")


class ExecuteCodeAction(BaseModel):
    """Schema for execute_code action."""
    type: Literal["execute_code"]
    code: str = Field(..., min_length=1, description="Python code to execute")

    @validator('code')
    def code_must_not_be_dangerous(cls, v):
        """Validate code doesn't contain obviously dangerous patterns."""
        dangerous_patterns = ['__import__', 'eval(', 'exec(', 'compile(']
        for pattern in dangerous_patterns:
            if pattern in v:
                raise ValueError(f"Code contains dangerous pattern: {pattern}")
        return v


# ... Add schemas for all action types


ACTION_SCHEMAS = {
    "create_task": CreateTaskAction,
    "update_task": UpdateTaskAction,
    "delete_task": DeleteTaskAction,
    "execute_code": ExecuteCodeAction,
    # ... etc
}


def validate_action(action: dict) -> tuple[bool, Optional[str]]:
    """Validate action against schema.

    Returns:
        (is_valid, error_message)
    """
    action_type = action.get("type")

    if not action_type:
        return False, "Missing 'type' field in action"

    schema = ACTION_SCHEMAS.get(action_type)
    if not schema:
        return False, f"Unknown action type: {action_type}"

    try:
        schema(**action)  # Validate
        return True, None
    except Exception as e:
        # Pydantic provides detailed, LLM-friendly error messages
        return False, str(e)
```

**Usage**:
```python
# File: gembrain/agents/tools.py

from .action_schemas import validate_action

def execute_action(self, action: Dict[str, Any]) -> ActionResult:
    """Execute a single action with validation."""
    action_type = action.get("type", "unknown")

    # Validate with Pydantic schema
    is_valid, error_msg = validate_action(action)
    if not is_valid:
        logger.error(f"✗ VALIDATION ERROR: {error_msg}")
        return ActionResult(False, action_type, error_msg)

    # ... rest of execution
```

**Benefits**:
- Type checking (e.g., task_id must be int > 0)
- Clear error messages for LLM to fix issues
- Self-documenting schemas
- Easy to extend with new validation rules

**Effort**: 8 hours (create schemas for all 30+ action types)
**Dependencies**: `pip install pydantic`
**Risk**: Low (validates before execution, doesn't change execution logic)

---

## Phase 2: Architecture Improvements (Week 2)

### 2.1 Support Multiple ```actions Blocks 🟡 MEDIUM

**Issue**: Only first ````actions` block is parsed. LLM cannot organize actions into logical groups.

**Current**:
```markdown
```actions
{"actions": [{"type": "create_task", "content": "Task 1"}]}
```

```actions
{"actions": [{"type": "create_task", "content": "Task 2"}]}  // IGNORED!
```
```

**Solution**:

```python
# File: gembrain/utils/json_utils.py

def parse_actions_from_response(response: str) -> Dict[str, Any]:
    """Parse all actions blocks from agent response."""
    all_actions = []

    # Find all ```actions blocks using finditer
    pattern = r"```actions\s*\n(.*?)\n```"
    matches = re.finditer(pattern, response, re.DOTALL)

    for match in matches:
        json_str = match.group(1).strip()
        actions_data = extract_json_block_content(json_str)  # Helper function

        if actions_data and "actions" in actions_data:
            all_actions.extend(actions_data["actions"])

    # Remove all actions blocks from reply
    reply = re.sub(r"```actions\s*\n.*?\n```", "", response, flags=re.DOTALL).strip()

    return {
        "reply": reply,
        "actions": all_actions,
    }
```

**Testing**:
```python
def test_multiple_actions_blocks():
    response = '''
```actions
{"actions": [{"type": "create_task", "content": "Task 1"}]}
```

Some text in between.

```actions
{"actions": [{"type": "create_memory", "content": "Memory 1"}]}
```
'''
    result = parse_actions_from_response(response)
    assert len(result["actions"]) == 2
    assert result["actions"][0]["type"] == "create_task"
    assert result["actions"][1]["type"] == "create_memory"
```

**Effort**: 2 hours
**Dependencies**: Nested backticks fix (1.2)
**Risk**: Low

---

### 2.2 Add Action Dependencies System 🟢 LOW

**Issue**: Actions execute in array order but can't express dependencies (e.g., "create project first, then create tasks in it").

**Current Workaround**: Use `execute_code` action to control order programmatically

**Proposed Solution**: Add optional `depends_on` field

```json
{
  "actions": [
    {
      "id": "action_1",
      "type": "create_project",
      "name": "Marketing"
    },
    {
      "id": "action_2",
      "type": "create_task",
      "content": "Plan Q1 campaign",
      "project_id_from": "action_1.project_id",
      "depends_on": ["action_1"]
    }
  ]
}
```

**Implementation**:

```python
# File: gembrain/agents/tools.py

def execute_actions(self, actions: List[Dict[str, Any]]) -> List[ActionResult]:
    """Execute actions with dependency resolution."""

    # Build dependency graph
    action_graph = {}
    for action in actions:
        action_id = action.get("id", f"action_{actions.index(action)}")
        depends_on = action.get("depends_on", [])
        action_graph[action_id] = (action, depends_on)

    # Topological sort
    executed = {}
    results = []

    def execute_with_deps(action_id: str):
        if action_id in executed:
            return executed[action_id]

        action, deps = action_graph[action_id]

        # Execute dependencies first
        for dep_id in deps:
            execute_with_deps(dep_id)

        # Resolve dynamic references (e.g., "action_1.project_id")
        action = resolve_action_references(action, executed)

        # Execute action
        result = self.execute_action(action)
        executed[action_id] = result
        results.append(result)
        return result

    for action_id in action_graph:
        execute_with_deps(action_id)

    return results
```

**Effort**: 16 hours (complex dependency resolution logic)
**Dependencies**: None
**Risk**: High (requires careful testing of circular dependencies, missing deps)
**Recommendation**: **DEFER** - Code-based actions already solve this problem better

---

### 2.3 Unify Action Formats (Standard vs Iterative) 🟢 LOW

**Issue**: Standard mode uses ````actions` blocks, iterative mode uses ````iteration` blocks with `next_actions` field. This is confusing for LLMs.

**Options**:

**Option A: Keep Separate** (Recommended)
- Standard mode: ````actions` for simple requests
- Iterative mode: ````iteration` for complex multi-step reasoning
- Clear separation of concerns
- No breaking changes

**Option B: Unify Under ````actions`**
- Both modes use ````actions` blocks
- Iterative mode adds metadata in separate ````iteration_meta` block
- Simpler for LLM, but requires migration

**Recommendation**: **Option A** - Keep formats separate but document clearly in system prompts

**Effort**: 1 hour (documentation only)
**Risk**: None

---

## Phase 3: Security & Performance (Week 3)

### 3.1 Sandbox Code Execution 🔴 CRITICAL

**Issue**: Current code execution uses restricted globals list which can be bypassed.

**Security Risks**:
```python
# Potential bypasses:
[c for c in (1).__class__.__base__.__subclasses__() if c.__name__ == 'Popen'][0](['ls'])

# Access to file system via imports:
import os
os.system('rm -rf /')

# Memory exhaustion:
huge_list = [0] * 10**9
```

**Solution**: Use Docker-based sandboxing

```python
# File: gembrain/agents/code_executor.py

import docker
import tempfile
import json

class DockerCodeExecutor:
    """Execute code in isolated Docker container."""

    def __init__(self, gembrain_api, timeout=30):
        self.gembrain_api = gembrain_api
        self.timeout = timeout
        self.client = docker.from_env()

    def execute(self, code: str) -> dict:
        """Execute code in Docker container."""

        # Create temporary directory for code
        with tempfile.TemporaryDirectory() as tmpdir:
            # Write code to file
            code_file = f"{tmpdir}/user_code.py"
            with open(code_file, 'w') as f:
                f.write(code)

            # Serialize GemBrain API state
            api_state = self._serialize_api_state()
            state_file = f"{tmpdir}/api_state.json"
            with open(state_file, 'w') as f:
                json.dump(api_state, f)

            # Run container
            try:
                output = self.client.containers.run(
                    image="gembrain-sandbox:latest",  # Custom Docker image
                    command=["python", "/code/user_code.py"],
                    volumes={
                        tmpdir: {"bind": "/code", "mode": "ro"}
                    },
                    network_mode="none",  # No network access
                    mem_limit="512m",  # Memory limit
                    cpu_period=100000,
                    cpu_quota=50000,  # 50% CPU
                    timeout=self.timeout,
                    remove=True,
                    stdout=True,
                    stderr=True,
                )

                return {
                    "success": True,
                    "stdout": output.decode('utf-8'),
                    "stderr": "",
                    "error": "",
                }

            except docker.errors.ContainerError as e:
                return {
                    "success": False,
                    "stdout": "",
                    "stderr": e.stderr.decode('utf-8'),
                    "error": str(e),
                }
            except Exception as e:
                return {
                    "success": False,
                    "stdout": "",
                    "stderr": "",
                    "error": f"Container error: {str(e)}",
                }
```

**Docker Image** (`Dockerfile`):
```dockerfile
FROM python:3.11-slim

# Install only necessary packages
RUN pip install --no-cache-dir \
    sqlalchemy \
    loguru

# Copy GemBrain API client
COPY gembrain_api_client.py /usr/local/lib/python3.11/site-packages/

# Create non-root user
RUN useradd -m -u 1000 sandbox
USER sandbox

WORKDIR /code
CMD ["python"]
```

**Effort**: 24 hours (Docker setup, testing, CI/CD integration)
**Dependencies**: Docker installed on host
**Risk**: High (major architectural change)
**Recommendation**: **HIGH PRIORITY** for production deployments

**Alternative**: Use `RestrictedPython` library (easier but less secure)

---

### 3.2 Add Action Rate Limiting 🟡 MEDIUM

**Issue**: No rate limiting on actions. LLM could create thousands of tasks/memories in a loop.

**Solution**:

```python
# File: gembrain/agents/tools.py

from time import time
from collections import defaultdict

class ActionExecutor:
    """Execute actions with rate limiting."""

    def __init__(self, db, enable_code_execution=True, max_retries=3, retry_delay=0.5):
        # ... existing init

        # Rate limiting: max 100 actions per minute per type
        self.rate_limits = {
            "create_task": (100, 60),  # (max_count, time_window_seconds)
            "create_memory": (50, 60),
            "create_goal": (20, 60),
            "datavault_store": (50, 60),
            "execute_code": (10, 60),
        }

        self.action_counts = defaultdict(list)  # action_type -> [timestamp, ...]

    def _check_rate_limit(self, action_type: str) -> tuple[bool, Optional[str]]:
        """Check if action is within rate limit."""
        if action_type not in self.rate_limits:
            return True, None

        max_count, window = self.rate_limits[action_type]
        now = time()

        # Remove old timestamps outside window
        self.action_counts[action_type] = [
            ts for ts in self.action_counts[action_type]
            if now - ts < window
        ]

        # Check count
        if len(self.action_counts[action_type]) >= max_count:
            return False, f"Rate limit exceeded for {action_type}: {max_count} per {window}s"

        # Record this action
        self.action_counts[action_type].append(now)
        return True, None

    def execute_action(self, action: Dict[str, Any]) -> ActionResult:
        """Execute action with rate limiting."""
        action_type = action.get("type", "unknown")

        # Check rate limit
        allowed, error_msg = self._check_rate_limit(action_type)
        if not allowed:
            logger.warning(f"🚫 RATE LIMIT: {error_msg}")
            return ActionResult(False, action_type, error_msg)

        # ... rest of execution
```

**Effort**: 4 hours
**Dependencies**: None
**Risk**: Low

---

## Phase 4: Error Handling & Observability (Week 4)

### 4.1 Improve Error Messages for LLMs 🟡 MEDIUM

**Issue**: Current error messages are for humans, not LLMs. LLM needs actionable guidance.

**Example**:

**Current**:
```
Missing required field: content
```

**Improved**:
```
Validation Error: Action 'create_task' is missing required field 'content'.

Expected format:
{
  "type": "create_task",
  "content": "<task description>",  // REQUIRED
  "notes": "<optional notes>",       // OPTIONAL
  "status": "pending|ongoing|paused|completed"  // OPTIONAL, default: "pending"
}

Example:
{
  "type": "create_task",
  "content": "Review pull request #123",
  "notes": "High priority",
  "status": "pending"
}
```

**Implementation**:

```python
# File: gembrain/agents/action_schemas.py

class ActionValidationError(Exception):
    """Action validation error with LLM-friendly message."""

    def __init__(self, action_type: str, field: str, issue: str, example: dict):
        self.action_type = action_type
        self.field = field
        self.issue = issue
        self.example = example

    def __str__(self):
        return f"""
Validation Error: Action '{self.action_type}' has issue with field '{self.field}'.

Issue: {self.issue}

Expected format:
{json.dumps(self.example, indent=2)}

Please fix the action and try again.
"""


def validate_create_task(action: dict):
    if "content" not in action or not action["content"]:
        raise ActionValidationError(
            action_type="create_task",
            field="content",
            issue="Missing required field 'content'",
            example={
                "type": "create_task",
                "content": "Review pull request #123",
                "notes": "High priority",
                "status": "pending"
            }
        )
```

**Effort**: 8 hours (create templates for all action types)
**Dependencies**: JSON schema validation (1.3)
**Risk**: Low

---

### 4.2 Add Action Tracing & Debugging 🟢 LOW

**Issue**: Hard to debug action execution flow, especially with retries and dependencies.

**Solution**: Add structured logging and tracing

```python
# File: gembrain/agents/tools.py

import uuid
from contextlib import contextmanager

class ActionExecutor:
    """Execute actions with tracing."""

    @contextmanager
    def trace_action(self, action: dict):
        """Context manager for action tracing."""
        trace_id = str(uuid.uuid4())[:8]
        action_type = action.get("type", "unknown")

        logger.info(f"[{trace_id}] ▶ START {action_type}")
        logger.debug(f"[{trace_id}] Parameters: {json.dumps(action, indent=2)}")

        start_time = time.time()
        try:
            yield trace_id
            elapsed = time.time() - start_time
            logger.info(f"[{trace_id}] ✓ SUCCESS {action_type} ({elapsed:.3f}s)")
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"[{trace_id}] ✗ FAILED {action_type} ({elapsed:.3f}s): {e}")
            raise

    def execute_action(self, action: Dict[str, Any]) -> ActionResult:
        """Execute action with tracing."""
        with self.trace_action(action) as trace_id:
            # ... execution logic
            pass
```

**Benefits**:
- Easy to filter logs by trace_id
- Track retries and execution time
- Debug action flow visually

**Effort**: 6 hours
**Dependencies**: None
**Risk**: Low

---

## Implementation Timeline

### Week 1: Critical Fixes
- **Day 1-2**: Control character fix (1.1) + Tests
- **Day 3-4**: Nested backticks fix (1.2) + Tests
- **Day 5**: Integration testing & documentation

### Week 2: Architecture
- **Day 1-3**: JSON schema validation (1.3)
- **Day 4-5**: Multiple actions blocks (2.1) + Tests

### Week 3: Security
- **Day 1-3**: Docker sandboxing (3.1) - HIGH PRIORITY
- **Day 4-5**: Rate limiting (3.2) + Tests

### Week 4: Polish
- **Day 1-2**: Error message improvements (4.1)
- **Day 3-4**: Action tracing (4.2)
- **Day 5**: Final integration testing & documentation

---

## Testing Strategy

### Unit Tests
- All new functions have unit tests
- Edge cases documented in `ACTION_PARSING_DOCUMENTATION.md`
- Target: 90%+ code coverage

### Integration Tests
```python
# tests/integration/test_action_flow.py

def test_end_to_end_text_actions():
    """Test full flow: LLM response → parsing → validation → execution."""

def test_end_to_end_code_actions():
    """Test code execution with GemBrain API."""

def test_iterative_reasoning_with_actions():
    """Test action execution in iterative reasoning mode."""

def test_action_retry_and_recovery():
    """Test retry logic with transient failures."""
```

### Performance Tests
```python
def test_rate_limiting_enforcement():
    """Ensure rate limits prevent abuse."""

def test_large_action_batch():
    """Test execution of 100+ actions."""
```

### Security Tests
```python
def test_code_sandbox_escape_attempts():
    """Verify sandbox prevents malicious code."""

def test_resource_exhaustion_prevention():
    """Ensure memory/CPU limits work."""
```

---

## Rollout Plan

### Phase 1: Testing Environment
1. Deploy fixes to dev environment
2. Run comprehensive test suite
3. Manual testing with real LLM interactions
4. Fix any regressions

### Phase 2: Canary Deployment
1. Enable for 10% of users
2. Monitor error rates and action success metrics
3. Collect feedback
4. Iterate on issues

### Phase 3: Full Rollout
1. Enable for all users
2. Monitor for 1 week
3. Document learnings
4. Plan next iteration

---

## Success Metrics

- **Action Parse Success Rate**: >99% (currently ~85% due to control char issues)
- **Action Execution Success Rate**: >95%
- **Average Action Latency**: <100ms (excluding code execution)
- **Code Execution Timeout Rate**: <1%
- **Security Incidents**: 0

---

## Risk Mitigation

### High-Risk Changes
1. **Docker sandboxing (3.1)**:
   - Risk: Breaking existing code execution
   - Mitigation: Feature flag, gradual rollout, fallback to restricted execution

2. **Action dependencies (2.2)**:
   - Risk: Complex bugs in dependency resolution
   - Mitigation: DEFER this feature, use code-based actions instead

### Medium-Risk Changes
1. **Multiple actions blocks (2.1)**:
   - Risk: Performance impact with many blocks
   - Mitigation: Limit to max 5 blocks per response

2. **JSON schema validation (1.3)**:
   - Risk: Too strict validation breaks existing prompts
   - Mitigation: Gradual migration, clear error messages

---

## Conclusion

This plan addresses all **8 architectural issues** and **13 edge cases** identified during analysis.

**Priorities**:
1. **Week 1**: Fix critical parsing bugs (MUST DO)
2. **Week 3**: Security hardening (HIGHLY RECOMMENDED for production)
3. **Week 2 & 4**: Quality improvements (NICE TO HAVE)

**Total Effort**: ~80 hours (2 developers, 4 weeks)

**Expected Outcome**: Robust, secure, well-tested action parsing system with >99% reliability.

---

**Last Updated**: 2025-11-14
**Author**: Claude (GemBrain Agent)
**Status**: Ready for Review
