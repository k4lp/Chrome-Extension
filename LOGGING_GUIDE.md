# GemBrain Logging & Debugging Guide

## Overview

GemBrain has a comprehensive logging system that displays agent reasoning, code execution, and actions in the **Technical Details** view at the bottom of the Chat panel.

## UI Components

### 1. **Technical Details View** (Bottom Panel)
Located at the bottom 45% of the Chat panel, contains 3 tabs:

- **🧠 Reasoning Tab**: Shows agent's thought process, iterations, observations, and insights
- **💻 Code Execution Tab**: Shows all code executed and their results (stdout, stderr, return values, errors)
- **⚡ Actions Tab**: Shows history of actions executed (create_task, create_goal, etc.)

### 2. **Conversation View** (Top Panel)
Shows the final user messages and agent responses.

## How Logging Works

### Progress Events Flow
```
Orchestrator → progress_callback() → ChatPanel._on_progress_update() → TechnicalDetailsView
```

The orchestrator emits structured progress events:

```python
{
    "type": "code_execution_start",
    "code": "print('Hello')"
}
{
    "type": "code_execution_result",
    "data": {
        "stdout": "Hello\n",
        "stderr": "",
        "result": None,
        "error": "",
        "execution_time": 0.001,
        "success": True
    }
}
```

### Event Types

| Event Type | Description | Displayed In |
|------------|-------------|--------------|
| `iteration_start` | New reasoning iteration | Reasoning Tab |
| `thought` | Agent's thinking (markdown) | Reasoning Tab |
| `observation` | What agent observed | Reasoning Tab |
| `insights` | Insights gained | Reasoning Tab |
| `actions_planned` | Actions to be executed | Reasoning Tab |
| `code_execution_start` | Code about to run | Code Execution Tab |
| `code_execution_result` | Code execution results | Code Execution Tab |
| `action_start` | Action starting | Actions Tab |
| `action_result` | Action completed | Actions Tab + Reasoning Tab |
| `reasoning_complete` | Iteration finished | Reasoning Tab |

## Debugging: Why Logs Are Empty

If the Technical Details tabs are empty, check:

### 1. **Verify Orchestrator is Emitting Events**

Add logging to `gembrain/agents/orchestrator.py`:

```python
def run_user_message(self, user_message, ui_context, auto_apply_actions, progress_callback=None):
    # Add this debug line
    logger.debug(f"Orchestrator: progress_callback is {'SET' if progress_callback else 'NOT SET'}")

    # When emitting events, add logging
    if progress_callback:
        logger.debug(f"Emitting progress event: {event_type}")
        progress_callback(progress_data)
    else:
        logger.warning("No progress_callback - events not being sent to UI!")
```

### 2. **Check Progress Callback Chain**

In `gembrain/ui/widgets/chat_panel.py`, verify `_on_progress_update` is being called:

```python
def _on_progress_update(self, progress_data):
    logger.debug(f"ChatPanel: Received progress event: {progress_data.get('type') if isinstance(progress_data, dict) else 'string'}")
    # ... rest of method
```

### 3. **Verify TechnicalDetailsView Methods**

In `gembrain/ui/widgets/technical_details_view.py`:

```python
def append_code_execution_start(self, code: str):
    logger.debug(f"TechnicalDetailsView: Adding code execution (length={len(code)})")
    # ... rest of method
```

### 4. **Check Worker Thread Connection**

In `gembrain/ui/widgets/chat_panel.py` `_send_message`:

```python
# Verify signal is connected
self.worker.progress.connect(self._on_progress_update)
logger.debug("Worker signals connected")
```

## Manual Testing

### Test Code Execution Logging

1. Open Chat panel
2. Send message: "Execute this Python code: print('Test logging')"
3. Check **💻 Code Execution Tab** for:
   - Code section showing `print('Test logging')`
   - Output section showing `Test logging`
   - Status showing ✅ Success

### Test Action Logging

1. Send message: "Create a task to test logging"
2. Check **⚡ Actions Tab** for:
   - Action card showing `create_task`
   - Parameters showing task content
   - Status showing ✅ or ❌

### Test Reasoning Logging

1. Enable iterative reasoning in Settings
2. Send a complex message
3. Check **🧠 Reasoning Tab** for:
   - Collapsible iteration sections
   - Thought processes (markdown formatted)
   - Observations and insights

## Enabling Verbose Logging

### 1. **Application-Level Logging**

Edit `gembrain/utils/logging.py`:

```python
def setup_logging(log_dir: Path, debug: bool = True):  # Change to True
    # ...
    logger.add(
        sys.stderr,
        level="DEBUG",  # Change from INFO to DEBUG
        # ...
    )
```

### 2. **Component-Specific Logging**

Add at top of files you want to debug:

```python
from loguru import logger
logger.level("DEBUG")
```

### 3. **Qt Event Logging**

```python
# In chat_panel.py
import os
os.environ['QT_LOGGING_RULES'] = '*.debug=true'
```

## Common Issues

### Issue: "Code Execution Tab is always empty"

**Cause**: Orchestrator not emitting `code_execution_start` events

**Solution**:
1. Check if code executor has `progress_callback` parameter
2. Verify callback is called before/after execution:
   ```python
   if progress_callback:
       progress_callback({
           "type": "code_execution_start",
           "code": code_to_execute
       })
   ```

### Issue: "Actions Tab shows nothing"

**Cause**: Actions not emitting start/result events

**Solution**:
1. Ensure action executor emits events:
   ```python
   progress_callback({
       "type": "action_start",
       "action_type": action_dict["type"],
       "details": str(action_dict)
   })
   ```

### Issue: "Reasoning Tab shows nothing"

**Cause**: Iterative reasoning disabled or not emitting events

**Solution**:
1. Enable iterative reasoning in Settings → Agent Behavior
2. Set max_iterations > 0
3. Verify reasoning loop emits iteration_start events

## Log File Locations

Logs are written to:
- **Console**: stderr with colored output
- **File**: `~/.config/gembrain/logs/gembrain_{date}.log` (Linux/Mac)
- **File**: `%APPDATA%\gembrain\logs\gembrain_{date}.log` (Windows)

## Example: Adding New Log Event

To add a new event type:

1. **Emit from Orchestrator**:
```python
if progress_callback:
    progress_callback({
        "type": "custom_event",
        "data": "Custom data"
    })
```

2. **Handle in ChatPanel**:
```python
def _on_progress_update(self, progress_data):
    if event_type == "custom_event":
        data = progress_data.get("data", "")
        self.technical_view.append_custom_event(data)
```

3. **Display in TechnicalDetailsView**:
```python
def append_custom_event(self, data: str):
    label = QLabel(f"<b>Custom:</b> {data}")
    self.reasoning_layout.addWidget(label)
```

## Performance Tips

- **Collapse iterations**: Click iteration headers to collapse old reasoning
- **Clear logs**: Click "Clear All" button to reset all tabs
- **Limit code output**: Very long outputs are auto-truncated to 200 chars in some views
- **Use filters**: Future enhancement - filter by event type

## Color Coding Reference

### Tasks (by status):
- 🟠 **Pending**: Orange background (#fff4e6)
- 🔵 **Ongoing**: Blue background (#e3f2fd)
- 🟡 **Paused**: Yellow/Orange background (#fff3e0)
- 🟢 **Completed**: Green background (#e8f5e9)

### Goals (by status):
- 🎯 **Pending**: Amber background (#fff8e1)
- ✅ **Completed**: Green background (#e8f5e9)

## Need More Help?

1. Check orchestrator implementation for progress_callback usage
2. Verify worker thread is connecting signals properly
3. Add debug logging at each step of the callback chain
4. Check Python console for any Qt warnings or errors
5. Verify PyQt6 version compatibility (needs >= 6.4)

---

**Last Updated**: 2025-11-14
