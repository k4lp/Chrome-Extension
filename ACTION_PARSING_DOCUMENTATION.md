# GemBrain Action Parsing System Documentation

## Overview

GemBrain supports **two distinct mechanisms** for LLMs to execute actions:

1. **Text-based Actions** - LLM outputs structured JSON in markdown code blocks
2. **Code-based Actions** - LLM writes Python code using the GemBrain API

Both mechanisms are parsed and executed by the action execution system.

---

## 1. Text-Based Actions (Standard Mode)

### Location
- Parsed by: `gembrain/utils/json_utils.py::parse_actions_from_response()`
- Used by: `orchestrator.py` in standard mode (iterative reasoning disabled)

### Expected Format

LLM should output a markdown code block with the `actions` tag:

```markdown
Here is my response to the user.

```actions
{
  "actions": [
    {
      "type": "create_task",
      "content": "Review the new feature",
      "notes": "Priority: high",
      "status": "pending"
    },
    {
      "type": "create_memory",
      "content": "User prefers dark mode",
      "notes": "preference"
    }
  ]
}
```

More text after the actions block.
```

### Parsing Rules

1. **Block Detection**: Uses regex `r"```actions\s*\n(.*?)\n```"` (DOTALL mode)
2. **JSON Parsing**: Uses `json.loads(json_str, strict=False)`
3. **Reply Text**: Actions block is removed from response, remaining text is the reply
4. **Multiple Blocks**: Only the **first** ````actions` block is parsed

### Supported Action Types

All actions require a `type` field. Additional required fields vary:

#### Task Actions
- `create_task`: Requires `content`, optional `notes`, `status` (default: "pending")
- `update_task`: Requires `task_id`, optional `content`, `notes`, `status`
- `delete_task`: Requires `task_id`
- `get_task`: Requires `task_id`
- `list_tasks`: Optional `status`, `limit` (default: 50)
- `search_tasks`: Requires `query`, optional `limit` (default: 20)

#### Memory Actions
- `create_memory`: Requires `content`, optional `notes`
- `update_memory`: Requires `memory_id`, optional `content`, `notes`
- `delete_memory`: Requires `memory_id`
- `get_memory`: Requires `memory_id`
- `list_memories`: Optional `limit` (default: 50)
- `search_memories`: Requires `query`, optional `limit` (default: 20)

#### Goal Actions
- `create_goal`: Requires `content`, optional `notes`, `status` (default: "pending")
- `update_goal`: Requires `goal_id`, optional `content`, `notes`, `status`
- `delete_goal`: Requires `goal_id`
- `get_goal`: Requires `goal_id`
- `list_goals`: Optional `status`, `limit` (default: 50)
- `search_goals`: Requires `query`, optional `limit` (default: 20)

#### Datavault Actions
- `datavault_store`: Requires `content`, optional `filetype` (default: "text"), `notes`
- `datavault_get`: Requires `item_id`
- `datavault_update`: Requires `item_id`, optional `content`, `filetype`, `notes`
- `datavault_delete`: Requires `item_id`
- `datavault_list`: Optional `filetype`, `limit` (default: 50)
- `datavault_search`: Requires `query`, optional `limit` (default: 20)

#### Code Execution
- `execute_code`: Requires `code` (Python code string)

### Validation

Actions are validated by `ActionExecutor._validate_action()`:

1. Check for `type` field
2. Check for required fields based on action type
3. Return error message if validation fails

### Example Text-Based Action

```json
{
  "actions": [
    {
      "type": "create_task",
      "content": "Implement user authentication",
      "notes": "Use OAuth 2.0",
      "status": "pending"
    }
  ]
}
```

---

## 2. Code-Based Actions (via execute_code)

### Location
- Executed by: `gembrain/agents/code_executor.py::CodeExecutor`
- API: `gembrain/agents/code_api.py::GemBrainAPI`
- Used in: Both standard mode and iterative reasoning

### Expected Format

LLM outputs an `execute_code` action containing Python code:

```json
{
  "actions": [
    {
      "type": "execute_code",
      "code": "task_result = gb.create_task('Review code', notes='High priority')\nprint(f\"Created task: {task_result['task_id']}\")"
    }
  ]
}
```

### Available API (`gb` object)

The `gb` object provides the following methods:

#### Task Management
```python
gb.create_task(content, notes="", status="pending")
  → Returns: {"id": int, "task_id": int, "content": str, "status": str, "created_at": str}

gb.update_task(task_id, content=None, notes=None, status=None)
  → Returns: {"id": int, "task_id": int, "content": str, "status": str, "updated_at": str}

gb.delete_task(task_id)
  → Returns: {"success": bool, "task_id": int}

gb.list_tasks(status=None, limit=50)
  → Returns: {"tasks": [{"id": int, "content": str, "notes": str, "status": str}]}

gb.search_tasks(query, limit=20)
  → Returns: {"tasks": [...]}
```

#### Memory Management
```python
gb.create_memory(content, notes="")
  → Returns: {"id": int, "memory_id": int, "content": str, "created_at": str}

gb.update_memory(memory_id, content=None, notes=None)
  → Returns: {"id": int, "memory_id": int, "content": str, "updated_at": str}

gb.delete_memory(memory_id)
  → Returns: {"success": bool, "memory_id": int}

gb.list_memories(limit=50)
  → Returns: {"memories": [{"id": int, "content": str, "notes": str}]}

gb.search_memories(query, limit=20)
  → Returns: {"memories": [...]}
```

#### Goal Management
```python
gb.create_goal(content, notes="", status="pending")
  → Returns: {"id": int, "goal_id": int, "content": str, "status": str, "created_at": str}

gb.update_goal(goal_id, content=None, notes=None, status=None)
  → Returns: {"id": int, "goal_id": int, "content": str, "status": str, "updated_at": str}

gb.delete_goal(goal_id)
  → Returns: {"success": bool, "goal_id": int}

gb.list_goals(status=None, limit=50)
  → Returns: {"goals": [{"id": int, "content": str, "status": str}]}

gb.search_goals(query, limit=20)
  → Returns: {"goals": [...]}
```

#### Datavault Management
```python
gb.datavault_store(content, filetype="text", notes="")
  → Returns: {"id": int, "datavault_id": int, "filetype": str, "content_length": int, "created_at": str}

gb.datavault_get(item_id)
  → Returns: {"id": int, "content": str, "filetype": str, "notes": str}

gb.datavault_update(item_id, content=None, filetype=None, notes=None)
  → Returns: {"id": int, "datavault_id": int, "filetype": str, "updated_at": str}

gb.datavault_delete(item_id)
  → Returns: {"success": bool, "datavault_id": int}

gb.datavault_list(filetype=None, limit=50)
  → Returns: {"items": [{"id": int, "filetype": str, "notes": str, "content_length": int}]}

gb.datavault_search(query, limit=20)
  → Returns: {"items": [...]}
```

#### Utility
```python
gb.log(message)
  → Logs a message for debugging
```

### Code Execution Environment

- **Restricted globals**: Only `gb` object and safe built-ins (no `open`, `eval`, `exec`, etc.)
- **Stdout/Stderr captured**: All print statements and errors are captured
- **Return value captured**: Final expression/return value is saved
- **Timeout**: 30 seconds (configurable)
- **Result format**:
  ```python
  {
      "success": bool,
      "stdout": str,
      "stderr": str,
      "result": Any,
      "error": str,
      "execution_time": float
  }
  ```

### Example Code-Based Action

```python
# In LLM response:
{
  "actions": [
    {
      "type": "execute_code",
      "code": """
import json

# Create tasks from a list
tasks = [
    'Review PR #123',
    'Update documentation',
    'Fix bug in authentication'
]

created_ids = []
for task_content in tasks:
    result = gb.create_task(task_content, notes='Auto-generated')
    created_ids.append(result['task_id'])
    gb.log(f"Created task: {result['task_id']}")

# Store summary in datavault
summary = json.dumps({'created_tasks': created_ids, 'total': len(created_ids)})
gb.datavault_store(summary, filetype='json', notes='Task creation summary')

print(f"Created {len(created_ids)} tasks")
"""
    }
  ]
}
```

---

## 3. Iterative Reasoning Actions

### Location
- System: `gembrain/agents/iterative_reasoner.py::IterativeReasoner`
- Uses special ````iteration` JSON blocks

### Expected Format

In iterative reasoning mode, actions are embedded in iteration JSON:

```json
{
  "iteration": 2,
  "reasoning": "I need to create tasks for the project...",
  "observations": ["User wants a project management setup"],
  "next_actions": [
    {
      "type": "create_task",
      "content": "Set up project structure",
      "notes": "Step 1"
    },
    {
      "type": "execute_code",
      "code": "gb.create_memory('Project initialized', notes='milestone')"
    }
  ],
  "insights_gained": ["Tasks should be sequential"],
  "is_final": false
}
```

### Parsing

- Uses custom brace-counting parser in `_parse_iteration_response()`
- Handles nested code blocks and escaped quotes
- Fixes control characters in JSON strings

---

## Edge Cases & Known Issues

### Text-Based Actions

#### 1. **Missing Closing Backticks**
```markdown
```actions
{"actions": [{"type": "create_task", "content": "test"}]}
// Missing closing ```
```
**Result**: Not parsed, no actions extracted

#### 2. **Multiple Actions Blocks**
```markdown
```actions
{"actions": [{"type": "create_task", "content": "task 1"}]}
```

```actions
{"actions": [{"type": "create_task", "content": "task 2"}]}
```
```
**Result**: Only first block parsed, second block ignored

#### 3. **Invalid JSON**
```json
{
  "actions": [
    {
      "type": "create_task",
      "content": "test",  // Trailing comma
    }
  ]
}
```
**Result**: `json.JSONDecodeError`, returns empty actions list

#### 4. **Wrong Block Name**
```markdown
```action
{"actions": [...]}
```
```
**Result**: Not recognized (expects `actions` not `action`)

#### 5. **Missing Required Fields**
```json
{
  "actions": [
    {"type": "create_task"}  // Missing 'content'
  ]
}
```
**Result**: Validation fails, returns `ActionResult(success=False, message="Missing required field: content")`

#### 6. **Actions Outside Block**
```json
{"type": "create_task", "content": "test"}
```
**Result**: Not parsed (must be inside ````actions` block)

#### 7. **Nested Code Blocks in JSON**
```json
{
  "actions": [
    {
      "type": "execute_code",
      "code": "```python\nprint('test')\n```"
    }
  ]
}
```
**Result**: May confuse regex parser if ``` appears in JSON strings

### Code-Based Actions

#### 1. **Syntax Errors**
```python
gb.create_task('test'  // Missing closing parenthesis
```
**Result**: Returns `success: False, error: "SyntaxError: ..."`

#### 2. **Runtime Errors**
```python
result = gb.create_task("test")
print(result['nonexistent_field'])  # KeyError
```
**Result**: Returns `success: False, error: "KeyError: ..."`

#### 3. **Undefined Variables**
```python
print(undefined_var)
```
**Result**: Returns `success: False, error: "NameError: ..."`

#### 4. **Infinite Loops**
```python
while True:
    pass
```
**Result**: Timeout after 30 seconds, raises `TimeoutError`

#### 5. **API Method Returns Wrong Type**
```python
result = gb.delete_task(1)
# Before fix: returned bool (caused AttributeError)
# After fix: returns {"success": bool, "task_id": int}
success = result.get('success')  # Works now
```

#### 6. **Invalid Status Values**
```python
gb.create_task("test", status="invalid_status")
```
**Result**: Service layer raises `ValueError: invalid_status is not a valid TaskStatus`

---

## Architecture Issues

### 1. **Single Actions Block Limitation**
- **Issue**: Only first ````actions` block is parsed
- **Impact**: LLM cannot output multiple action groups
- **Severity**: Medium
- **Proposed Fix**: Parse all ````actions` blocks and merge actions arrays

### 2. **No Action Validation Before Parsing**
- **Issue**: JSON is parsed before validation
- **Impact**: Complex error messages, harder to debug
- **Severity**: Low
- **Proposed Fix**: Add schema validation using JSON Schema or Pydantic

### 3. **Regex-Based Parsing Fragility**
- **Issue**: Regex `r"```actions\s*\n(.*?)\n```"` fails with nested backticks
- **Impact**: Code blocks inside JSON strings break parsing
- **Severity**: High
- **Proposed Fix**: Use proper parser (state machine or AST-based)

### 4. **No Action Ordering Guarantee**
- **Issue**: Actions execute in array order, but no dependency handling
- **Impact**: Actions may fail if they depend on previous action results
- **Severity**: Medium
- **Proposed Fix**: Add dependency specification or use code-based actions exclusively

### 5. **Iterative Reasoning Uses Different Format**
- **Issue**: ````iteration` blocks vs ````actions` blocks
- **Impact**: Confusing for LLM, two different schemas to learn
- **Severity**: Low
- **Proposed Fix**: Unify formats or clearly separate modes

### 6. **Error Messages Don't Propagate to LLM**
- **Issue**: Action failures return error messages but LLM doesn't see them in next iteration
- **Impact**: LLM repeats failing actions
- **Severity**: High
- **Proposed Fix**: Include action results in next iteration context (already done in iterative mode!)

### 7. **Code Execution Security**
- **Issue**: Restricted globals list may have bypasses
- **Impact**: Potential for unsafe code execution
- **Severity**: Critical
- **Proposed Fix**: Use sandboxed execution environment (Docker, RestrictedPython)

### 8. **JSON Control Character Handling**
- **Issue**: LLMs generate literal newlines in JSON strings
- **Impact**: `json.loads()` fails with JSONDecodeError
- **Severity**: Medium
- **Current Fix**: `_fix_json_control_chars()` escapes control chars in iterative mode
- **Gap**: Not applied to standard mode text-based actions
- **Proposed Fix**: Apply same fix in `extract_json_block()`

---

## Recommendations

### Immediate (High Priority)

1. **Apply `_fix_json_control_chars()` to standard mode** - Prevents JSON parse failures
2. **Add comprehensive test suite** - Test all edge cases documented above
3. **Improve error messages** - Make validation errors more actionable for LLM
4. **Document action formats in system prompt** - LLM needs clear examples

### Short-Term (Medium Priority)

1. **Parse multiple ````actions` blocks** - Allow LLM flexibility
2. **Add JSON Schema validation** - Better error messages, schema evolution
3. **Improve regex parser** - Handle nested backticks correctly
4. **Add action dependency system** - Or recommend code-based approach for complex workflows

### Long-Term (Low Priority)

1. **Unify action formats** - Single consistent schema
2. **Add action result context** - Already done in iterative mode, extend to standard
3. **Sandbox code execution** - Security hardening
4. **Add action tracing/debugging UI** - Visual representation of action flow

---

## Testing Strategy

See `tests/test_action_parsing.py` for comprehensive test coverage including:

1. Valid action parsing (both text and code)
2. Invalid JSON handling
3. Missing required fields
4. Wrong action types
5. Nested code blocks
6. Multiple actions blocks
7. Control characters in JSON
8. Code execution errors
9. API return type validation
10. Edge cases for all action types

---

**Last Updated**: 2025-11-14
