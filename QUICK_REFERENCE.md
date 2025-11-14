# GemBrain Quick Reference Guide

## Key Files to Know

### Core Data Layer
- `gembrain/core/models.py` - Data models (Task, Memory, Goal, Datavault)
- `gembrain/core/services.py` - Business logic services
- `gembrain/core/repository.py` - Data access layer
- `gembrain/core/db.py` - Database initialization

### AI & Orchestration
- `gembrain/agents/orchestrator.py` - Main agent coordinator
- `gembrain/agents/iterative_reasoner.py` - Multi-step reasoning (1145 lines)
- `gembrain/agents/tools.py` - Action execution
- `gembrain/agents/code_api.py` - GemBrain API exposed to code

### UI Components
- `gembrain/ui/main_window.py` - Main window & menu
- `gembrain/ui/widgets/chat_panel.py` - AI conversation
- `gembrain/ui/widgets/tasks_panel.py` - Task management
- `gembrain/ui/widgets/goals_panel.py` - Goal management
- `gembrain/ui/widgets/datavault_panel.py` - Data storage
- `gembrain/ui/widgets/settings_dialog.py` - Configuration UI

### Configuration
- `gembrain/config/models.py` - Pydantic settings models
- `gembrain/config/manager.py` - Settings I/O
- `~/.gembrain/config.json` - Runtime configuration

### Automation
- `gembrain/automation/engine.py` - APScheduler-based automation
- `gembrain/automation/rules.py` - Automation rule models

---

## Data Model Cheat Sheet

### Task
```python
Task(
    content: str,           # What needs doing
    notes: str,            # LLM annotations
    status: TaskStatus,    # PENDING|ONGOING|PAUSED|COMPLETED
    created_at, updated_at # Auto-timestamped
)
```

### Memory
```python
Memory(
    content: str,          # Hint/clue/insight
    notes: str,           # LLM annotations
    created_at, updated_at
)
```

### Goal
```python
Goal(
    content: str,         # Expected outcome
    notes: str,          # LLM annotations
    status: GoalStatus,  # PENDING|COMPLETED
    created_at, updated_at
)
```

### Datavault
```python
Datavault(
    content: str,         # Large data blob
    filetype: str,       # text|py|js|json|md|csv|html|xml
    notes: str,         # LLM annotations
    created_at, updated_at
)
```

---

## Service API Patterns

### All Services Follow This Pattern:

```python
# Database session is always first parameter
service = TaskService(db_session)

# CRUD operations
service.create_task(content, notes, status)
service.get_task(task_id)
service.get_all_tasks(status=None)
service.search_tasks(query)
service.update_task(task_id, **kwargs)
service.delete_task(task_id)
```

### Service Classes
- `TaskService` - Task CRUD + status filtering
- `MemoryService` - Memory CRUD + limits
- `GoalService` - Goal CRUD + status filtering
- `DatavaultService` - Data CRUD + filetype filtering
- `AutomationService` - Automation rule management

---

## How User Interactions Flow

```
User Types Message
    ↓
ChatPanel.send_message()
    ↓
OrchestratorWorker (background thread)
    ↓
Orchestrator.run_user_message()
    ↓
Build Context (fetch tasks, memories, goals)
    ↓
GeminiClient.call_gemini()
    ↓
ActionExecutor.execute_action() [multiple actions]
    ↓
Return OrchestratorResponse
    ↓
ChatPanel displays response
    ↓
UI panels refresh automatically
```

---

## Important Locations & Paths

### Database
- Location: `~/.gembrain/gembrain.db`
- Backups: `~/.gembrain/backups/`
- Config: `~/.gembrain/config.json`

### Menu Items (File Menu in MainWindow)
```
File Menu:
├── Backup Database
├── Migrate to New Schema
├── Delete All Data...
└── Exit
```

### Menu Items (Automation Menu)
```
Automation Menu:
├── Run Daily Review
├── Run Weekly Review
└── Resurface Notes
```

---

## Current Limitations & Gaps

### What's Missing:
1. ❌ Data export (CSV, JSON)
2. ❌ Selective deletion (only bulk "delete all")
3. ❌ Data undo capability
4. ❌ Memory search in UI (only programmatic access)
5. ❌ Automation rules UI (only database-backed)
6. ❌ Data compression for large datavaults

### What Exists But Could Be Better:
1. Memory accessibility (only via code execution)
2. Iterative reasoning (complex state tracking)
3. Goal verification (requires manual LLM check)
4. No data filtering/querying UI

---

## Key Settings (config/models.py)

### Must Configure:
```python
Settings.api.gemini_api_key = "sk-..."  # Required
```

### Important Behaviors:
```python
Settings.agent_behavior.enable_iterative_reasoning = False  # Default
Settings.agent_behavior.enable_code_execution = True
Settings.agent_behavior.auto_structured_actions = False  # Requires review
Settings.agent_behavior.ask_before_destructive = True
```

### Storage:
```python
Settings.storage.auto_backup_enabled = True
Settings.storage.auto_backup_interval_hours = 24
```

---

## Testing Common Operations

### Add a Task (UI)
1. Click "Tasks" in sidebar
2. Click "+ New Task"
3. Enter content

### Add via Code Execution
```python
gb.create_task("Buy groceries", status="pending")
```

### List Tasks
```python
tasks = gb.list_tasks()  # All
tasks = gb.list_tasks(status="pending")  # Filtered
```

### Delete a Task
```python
gb.delete_task(task_id)
```

### Store Large Data
```python
gb.datavault_store(
    content="<large code>",
    filetype="py",
    notes="Helper functions"
)
```

---

## Performance Notes

- **Iterative Reasoning**: Can run 5-50 iterations (configurable)
- **Database**: SQLite, suitable for ~10k+ items
- **UI Threading**: Chat runs in background worker to prevent freezing
- **Memory**: Context building fetches top N items from each type

---

## Code Quality

- Type hints: ✅ Throughout
- Docstrings: ✅ On all major classes
- Error handling: ✅ Try-catch with logging
- Logging: ✅ Comprehensive via loguru
- Tests: ⏳ Minimal coverage

---

## Recent Work (Current Branch)

**Branch**: `claude/add-delete-export-features-01XAtWMYYBq2kPyZezUeT89d`

**Latest Features**:
- Delete All Data feature with double confirmation
- Goals panel UI (read/create/toggle)
- Datavault panel UI (store/view/delete)
- Fixed JSON parsing in iterative reasoner
- Added missing service methods

**Still TODO**:
- Export to CSV/JSON
- Selective deletion UI
- Memory panel UI
- Automation rules management UI

