# Component Logging Reference

Complete reference of all logging throughout the GemBrain application, organized by component.

## Table of Contents
1. [Core Services](#core-services)
2. [Repository Layer](#repository-layer)
3. [Code Execution](#code-execution)
4. [Orchestrator & Agent](#orchestrator--agent)
5. [UI Panels](#ui-panels)
6. [Automation](#automation)
7. [Main Application](#main-application)

---

## Core Services

### TaskService (`gembrain/core/services.py`)

| Log Level | Message Pattern | Trigger | Line |
|-----------|----------------|---------|------|
| `INFO` | `Created task: {task_id}` | Task created successfully | 50 |
| `INFO` | `Deleted all {count} tasks` | All tasks deleted | 108 |

**Example:**
```python
logger.info(f"Created task: {task.id}")
logger.info(f"Deleted all {count} tasks")
```

### MemoryService (`gembrain/core/services.py`)

| Log Level | Message Pattern | Trigger | Line |
|-----------|----------------|---------|------|
| `INFO` | `Created memory: {memory_id}` | Memory created successfully | 119 |
| `INFO` | `Deleted all {count} memories` | All memories deleted | 159 |

**Example:**
```python
logger.info(f"Created memory: {memory.id}")
logger.info(f"Deleted all {count} memories")
```

### GoalService (`gembrain/core/services.py`)

| Log Level | Message Pattern | Trigger | Line |
|-----------|----------------|---------|------|
| `INFO` | `Created goal: {goal_id}` | Goal created successfully | 176 |
| `INFO` | `Deleted all {count} goals` | All goals deleted | 206 |

**Example:**
```python
logger.info(f"Created goal: {goal.id}")
logger.info(f"Deleted all {count} goals")
```

### DatavaultService (`gembrain/core/services.py`)

| Log Level | Message Pattern | Trigger | Line |
|-----------|----------------|---------|------|
| `INFO` | `Stored datavault item: {id} (type: {filetype})` | Item stored | 223 |
| `INFO` | `Updated datavault item: {id}` | Item updated | 242 |
| `INFO` | `Deleted datavault item: {id}` | Item deleted | 249 |
| `INFO` | `Deleted all {count} datavault items` | All items deleted | 259 |

**Example:**
```python
logger.info(f"Stored datavault item: {item.id} (type: {filetype})")
logger.info(f"Deleted all {count} datavault items")
```

### ExportService (`gembrain/core/services.py`)

| Log Level | Message Pattern | Trigger | Line |
|-----------|----------------|---------|------|
| `INFO` | `Exported datavault item {id} to {path}` | Export successful | 320 |
| `ERROR` | `Failed to export datavault item {id}: {error}` | Export failed | 324 |

**Example:**
```python
logger.info(f"Exported datavault item {item.id} to {path}")
logger.error(f"Failed to export datavault item {item.id}: {e}")
```

---

## Repository Layer

All repository operations are handled by services, which log the operations. The repository layer itself does not log directly to keep it clean and focused.

---

## Code Execution

### CodeExecutor (`gembrain/agents/code_executor.py`)

| Log Level | Message Pattern | Trigger | Context |
|-----------|----------------|---------|---------|
| `WARNING` | `===============...` (80 =) | Code execution start | Banner |
| `WARNING` | `CODE EXECUTION #{n} - STARTING` | Execution begins | Header |
| `WARNING` | `Timestamp: {iso_timestamp}` | Execution begins | Timestamp |
| `WARNING` | `Code to execute:` | Before code display | Section |
| `WARNING` | `{line_num} \| {code_line}` | For each code line | Code listing |
| `WARNING` | `CODE EXECUTION #{n} - FINISHED` | Execution ends | Footer |
| `WARNING` | `Success: {bool}` | Execution result | Status |
| `WARNING` | `Execution time: {seconds}s` | Execution ends | Performance |

**Example Output:**
```
2025-11-14 21:37:38 | WARNING  | ================================================================================
2025-11-14 21:37:38 | WARNING  | CODE EXECUTION #1 - STARTING
2025-11-14 21:37:38 | WARNING  | Timestamp: 2025-11-14T21:37:38.990765
2025-11-14 21:37:38 | WARNING  | Code to execute:
2025-11-14 21:37:38 | WARNING  | ----------------------------------------
2025-11-14 21:37:38 | WARNING  |     1 | import json
2025-11-14 21:37:38 | WARNING  |     2 |
2025-11-14 21:37:38 | WARNING  |     3 | gb.log("Starting test")
...
2025-11-14 21:37:39 | WARNING  | CODE EXECUTION #1 - FINISHED
2025-11-14 21:37:39 | WARNING  | Success: True
2025-11-14 21:37:39 | WARNING  | Execution time: 0.068s
2025-11-14 21:37:39 | WARNING  | ================================================================================
```

### Code API (`gembrain/agents/code_api.py`)

#### Task Operations

| Log Level | Message Pattern | Trigger | Line |
|-----------|----------------|---------|------|
| `INFO` | `✅ Code created task: {task_id}` | Task created from code | 100 |
| `INFO` | `✅ Code updated task: {task_id}` | Task updated from code | 201 |
| `INFO` | `🗑️ Code deleted task: {task_id}` | Task deleted from code | 222 |
| `ERROR` | `Failed to create task: {error}` | Task creation failed | 109 |

#### Memory Operations

| Log Level | Message Pattern | Trigger | Line |
|-----------|----------------|---------|------|
| `INFO` | `🧠 Code created memory: {memory_id}` | Memory created from code | 240 |
| `INFO` | `🧠 Code updated memory: {memory_id}` | Memory updated from code | 330 |
| `INFO` | `🗑️ Code deleted memory: {memory_id}` | Memory deleted from code | 350 |
| `ERROR` | `Failed to create memory: {error}` | Memory creation failed | 248 |

#### Goal Operations

| Log Level | Message Pattern | Trigger | Line |
|-----------|----------------|---------|------|
| `INFO` | `🎯 Code created goal: {goal_id}` | Goal created from code | 371 |
| `INFO` | `🎯 Code updated goal: {goal_id}` | Goal updated from code | 472 |
| `INFO` | `🗑️ Code deleted goal: {goal_id}` | Goal deleted from code | 493 |
| `ERROR` | `Failed to create goal: {error}` | Goal creation failed | 380 |

#### Datavault Operations

| Log Level | Message Pattern | Trigger | Line |
|-----------|----------------|---------|------|
| `INFO` | `💾 Code stored datavault item: {id} (type: {filetype})` | Item stored from code | 513 |
| `INFO` | `💾 Code updated datavault item: {id}` | Item updated from code | 610 |
| `INFO` | `🗑️ Code deleted datavault item: {id}` | Item deleted from code | 632 |
| `ERROR` | `Failed to store datavault item: {error}` | Store failed | 523 |

#### Utility Operations

| Log Level | Message Pattern | Trigger | Line |
|-----------|----------------|---------|------|
| `INFO` | `[CODE] {message}` | Code calls gb.log() | 649 |
| `WARNING` | `[CODE] {message}` | Code calls gb.log(level="warning") | 645 |
| `ERROR` | `[CODE] {message}` | Code calls gb.log(level="error") | 647 |
| `INFO` | `✅ Code explicitly committed database changes` | Code calls gb.commit() | 658 |
| `ERROR` | `Failed to commit: {error}` | Commit failed | 661 |

**Example:**
```python
# When code executes: gb.create_task("Test task")
logger.info(f"✅ Code created task: {task.id}")

# When code executes: gb.log("Custom message")
logger.info(f"[CODE] Custom message")
```

---

## Orchestrator & Agent

### Orchestrator (`gembrain/agents/orchestrator.py`)

| Log Level | Message Pattern | Trigger | Context |
|-----------|----------------|---------|---------|
| `INFO` | `🧠 Iterative reasoning is ENABLED - using iterative mode` | Iterative mode active | Startup |
| `INFO` | `🧠 Starting iterative reasoning: {user_message}` | Reasoning begins | Entry |
| `INFO` | `✅ Reasoning completed: {iterations} iterations, Final output: {length} chars` | Reasoning done | Exit |
| `INFO` | `🔍 Running verification...` | Verification starts | Verification |
| `INFO` | `✅ Verification PASSED - Output approved` | Verification succeeds | Verification |
| `INFO` | `📊 Iterative reasoning: {iterations} iterations, {actions} total actions` | Summary | Stats |
| `INFO` | `✅ Verification: APPROVED` | Verification result | Result |

### Iterative Reasoner (`gembrain/agents/iterative_reasoner.py`)

| Log Level | Message Pattern | Trigger | Context |
|-----------|----------------|---------|---------|
| `INFO` | `🧠 Starting iterative reasoning for: {task}` | Reasoning starts | Entry |
| `INFO` | `🔄 Iteration {current}/{max}` | Each iteration | Loop |
| `INFO` | `🎬 {count} actions to execute` | Actions found | Action prep |
| `INFO` | `✅ Executed {count} actions` | Actions done | Post-action |
| `INFO` | `🏁 is_final: {bool}` | Check if done | State |
| `INFO` | `✅ Reasoning complete after {iterations} iterations` | Success | Exit |
| `INFO` | `📤 Final output length: {length} chars` | Output ready | Result |
| `INFO` | `🔍 Starting verification...` | Verification starts | Verification |
| `INFO` | `✅ Verification PASSED` | Verification succeeds | Verification |

### Tools (`gembrain/agents/tools.py`)

| Log Level | Message Pattern | Trigger | Context |
|-----------|----------------|---------|---------|
| `WARNING` | `============...` (60 =) | Batch start/end | Banner |
| `WARNING` | `EXECUTING ACTION BATCH: {count} actions` | Batch begins | Header |
| `WARNING` | `BATCH COMPLETE: {success} succeeded, {failed} failed` | Batch ends | Footer |
| `INFO` | `Action {current}/{total}` | Each action | Counter |
| `INFO` | `────────────...` (60 ─) | Action separator | Divider |
| `INFO` | `EXECUTING ACTION: {action_type}` | Action starts | Action header |
| `INFO` | `Parameters: {params}` | Action details | Parameters |

**Example Output:**
```
2025-11-14 21:37:38 | WARNING  | ============================================================
2025-11-14 21:37:38 | WARNING  | EXECUTING ACTION BATCH: 1 actions
2025-11-14 21:37:38 | WARNING  | ============================================================
2025-11-14 21:37:38 | INFO     | Action 1/1
2025-11-14 21:37:38 | INFO     | ────────────────────────────────────────────────────────────
2025-11-14 21:37:38 | INFO     | EXECUTING ACTION: execute_code
2025-11-14 21:37:38 | INFO     | Parameters: {'type': 'execute_code', 'code': '...'}
```

### Gemini Client (`gembrain/agents/gemini_client.py`)

| Log Level | Message Pattern | Trigger | Line |
|-----------|----------------|---------|------|
| `INFO` | `Configured Gemini model: {model} with API key #{key_num}/25` | Model configured | Various |
| `INFO` | `Successfully generated response` | Response received | Generate |

---

## UI Panels

### TasksPanel (`gembrain/ui/widgets/tasks_panel.py`)

| Log Level | Message Pattern | Trigger | Line |
|-----------|----------------|---------|------|
| `INFO` | `Created task: {content[:50]}...` | Task created via UI | 123 |
| `INFO` | `Updated task {id} status to {status}` | Task status changed | 147 |
| `INFO` | `Deleted all {count} tasks via UI` | Delete all executed | 182 |
| `ERROR` | `Failed to delete all tasks: {error}` | Delete all failed | 184 |

### GoalsPanel (`gembrain/ui/widgets/goals_panel.py`)

| Log Level | Message Pattern | Trigger | Line |
|-----------|----------------|---------|------|
| `INFO` | `Refreshing goals panel` | Panel refresh starts | 98 |
| `INFO` | `Loaded {count} goals` | Panel refresh done | 128 |
| `INFO` | `Created goal: {id}` | Goal created via UI | 156 |
| `ERROR` | `Failed to create goal: {error}` | Goal creation failed | 160 |
| `INFO` | `Updated goal {id} status to {status}` | Goal status changed | 178 |
| `ERROR` | `Failed to update goal: {error}` | Goal update failed | 181 |
| `INFO` | `Deleted all {count} goals via UI` | Delete all executed | 237 |
| `ERROR` | `Failed to delete all goals: {error}` | Delete all failed | 239 |

### MemoryPanel (`gembrain/ui/widgets/memory_panel.py`)

| Log Level | Message Pattern | Trigger | Line |
|-----------|----------------|---------|------|
| `INFO` | `Refreshing memory panel` | Panel refresh starts | 94 |
| `INFO` | `Loaded {count} memories` | Panel refresh done | 105 |
| `INFO` | `Created memory: {id}` | Memory created via UI | 149 |
| `ERROR` | `Failed to create memory: {error}` | Memory creation failed | 151 |
| `INFO` | `Deleted memory: {id}` | Memory deleted | 204 |
| `ERROR` | `Failed to delete memory: {error}` | Memory deletion failed | 208 |
| `INFO` | `Deleted all {count} memories via UI` | Delete all executed | 237 |
| `ERROR` | `Failed to delete all memories: {error}` | Delete all failed | 239 |

### DatavaultPanel (`gembrain/ui/widgets/datavault_panel.py`)

| Log Level | Message Pattern | Trigger | Line |
|-----------|----------------|---------|------|
| `INFO` | `Refreshing datavault panel` | Panel refresh starts | 103 |
| `INFO` | `Loaded {count} datavault items` | Panel refresh done | 145 |
| `INFO` | `Stored datavault item: {id}` | Item stored via UI | 174 |
| `ERROR` | `Failed to store data: {error}` | Store failed | 179 |
| `INFO` | `Deleted datavault item: {id}` | Item deleted | 246 |
| `ERROR` | `Failed to delete item: {error}` | Delete failed | 252 |
| `INFO` | `Deleted all {count} datavault items via UI` | Delete all executed | 288 |
| `ERROR` | `Failed to delete all items: {error}` | Delete all failed | 290 |
| `INFO` | `Exported datavault item {id} to {filepath}` | Export successful | 326 |
| `ERROR` | `Failed to export item {id}: {error}` | Export failed | 335 |

### ChatPanel (`gembrain/ui/widgets/chat_panel.py`)

| Log Level | Message Pattern | Trigger | Line |
|-----------|----------------|---------|------|
| `INFO` | `🚀 Starting background worker thread` | Message sent | 228 |
| `INFO` | `🧵 Worker thread started` | Thread begins | 51 |
| `INFO` | `🧵 Worker thread completed successfully` | Thread done | 71 |
| `ERROR` | `🧵 Worker thread error: {error}` | Thread error | 75 |
| `INFO` | `✅ Response ready from worker thread` | Response received | 237 |
| `ERROR` | `❌ Worker error: {error}` | Worker error | 263 |
| `WARNING` | `Already processing a message` | Duplicate send | 198 |

---

## Automation

### Automation Engine (`gembrain/automation/engine.py`)

| Log Level | Message Pattern | Trigger | Line |
|-----------|----------------|---------|------|
| `INFO` | `Starting automation engine` | Engine starts | Various |
| `INFO` | `Automation engine started` | Engine ready | Various |

---

## Main Application

### App (`gembrain/ui/app.py`)

| Log Level | Message Pattern | Trigger | Line |
|-----------|----------------|---------|------|
| `INFO` | `Starting GemBrain` | Application starts | 28 |
| `INFO` | `Database initialized` | Database ready | 35 |
| `INFO` | `Automation engine started` | Automation ready | 85 |
| `INFO` | `Cleaning up` | Shutdown begins | 112 |
| `INFO` | `GemBrain stopped` | Shutdown complete | 121 |
| `ERROR` | `Error running application: {error}` | Fatal error | 105 |

### Main Window (`gembrain/ui/main_window.py`)

| Log Level | Message Pattern | Trigger | Line |
|-----------|----------------|---------|------|
| `INFO` | `Main window closing` | Window closing | 497 |
| `INFO` | `Database backed up to {path}` | Backup successful | 262 |
| `ERROR` | `Backup failed: {error}` | Backup failed | 265 |
| `INFO` | `Created pre-migration backup at {path}` | Migration backup | 307 |
| `INFO` | `Database migrated to new schema` | Migration done | 318 |
| `ERROR` | `Migration failed: {error}` | Migration failed | 333 |
| `WARNING` | `=" * 80` | Delete all start/end | Banner |
| `WARNING` | `DELETE ALL DATA - EXECUTED` | Delete all done | 418 |
| `WARNING` | `Deleted {count} tasks` | Delete stats | 419 |
| `WARNING` | `Deleted {count} goals` | Delete stats | 420 |
| `WARNING` | `Deleted {count} memories` | Delete stats | 421 |
| `WARNING` | `Deleted {count} datavault items` | Delete stats | 422 |
| `ERROR` | `Delete all failed: {error}` | Delete all failed | 444 |
| `ERROR` | `Automation {name} failed: {error}` | Automation failed | 476 |

---

## Log File Locations

### Linux/Mac
- Console: `stderr` with colored output
- File: `~/.config/gembrain/logs/gembrain_YYYYMMDD.log`

### Windows
- Console: `stderr` with colored output
- File: `%APPDATA%\gembrain\logs\gembrain_YYYYMMDD.log`

---

## Log Levels

| Level | Usage | Examples |
|-------|-------|----------|
| `DEBUG` | Development/troubleshooting | Variable values, flow control |
| `INFO` | Normal operations | Created task, Loaded data, Started process |
| `WARNING` | Important events | Code execution blocks, Batch operations, Delete all |
| `ERROR` | Failures/exceptions | Failed to create, Failed to delete, API error |

---

## Enabling Verbose Logging

### Method 1: Modify Setup Function

Edit `gembrain/utils/logging.py`:
```python
def setup_logging(log_dir: Path, debug: bool = True):  # Change to True
    logger.add(
        sys.stderr,
        level="DEBUG",  # Change from INFO to DEBUG
        ...
    )
```

### Method 2: Runtime Override

Add at top of any file:
```python
from loguru import logger
logger.level("DEBUG")
```

### Method 3: Component-Specific

```python
from loguru import logger

# Enable debug for specific operations
logger.opt(depth=1).debug("Detailed debug info: {data}", data=my_data)
```

---

## Common Log Patterns

### Success Pattern
```
✅ {Action} {resource}: {id}
Example: ✅ Code created task: 123
```

### Deletion Pattern
```
🗑️ Code deleted {resource}: {id}
Example: 🗑️ Code deleted memory: 456
```

### Storage Pattern
```
💾 Code stored datavault item: {id} (type: {filetype})
Example: 💾 Code stored datavault item: 789 (type: json)
```

### Error Pattern
```
Failed to {action}: {error}
Example: Failed to create task: Database connection lost
```

### Banner Pattern (Important Events)
```
============================================================
{TITLE IN CAPS}
============================================================
```

---

## Monitoring Tips

### Watch Real-Time Logs
```bash
# Linux/Mac
tail -f ~/.config/gembrain/logs/gembrain_$(date +%Y%m%d).log

# Windows PowerShell
Get-Content "$env:APPDATA\gembrain\logs\gembrain_$(Get-Date -Format 'yyyyMMdd').log" -Wait
```

### Filter by Component
```bash
# Show only code execution
grep "CODE EXECUTION" ~/.config/gembrain/logs/*.log

# Show only errors
grep "ERROR" ~/.config/gembrain/logs/*.log

# Show only API calls from code
grep "\[CODE\]" ~/.config/gembrain/logs/*.log
```

### Count Events
```bash
# Count tasks created today
grep "Created task:" ~/.config/gembrain/logs/gembrain_$(date +%Y%m%d).log | wc -l

# Count code executions today
grep "CODE EXECUTION #" ~/.config/gembrain/logs/gembrain_$(date +%Y%m%d).log | wc -l
```

---

**Last Updated**: 2025-11-14
**Version**: 1.0
