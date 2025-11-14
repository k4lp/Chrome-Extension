# GemBrain Codebase - Comprehensive Overview

**Project**: GemBrain - A Gemini-powered agentic second brain desktop application
**Total Lines of Code**: ~10,000 lines
**Framework**: PyQt6, SQLAlchemy, Google Gemini API
**Database**: SQLite with custom ORM layer
**Current Status**: Production-ready with new data structures

---

## 1. OVERALL STRUCTURE & ORGANIZATION

### Directory Structure
```
gembrain/
├── core/               # Database layer (models, repository, services)
├── agents/             # AI orchestration and reasoning
├── automation/         # Scheduled tasks and automation rules
├── ui/                 # PyQt6 GUI components
│   ├── widgets/        # Individual UI panels and dialogs
│   └── styles/         # QSS stylesheets
├── config/             # Settings management with Pydantic
└── utils/              # Logging, path utilities, JSON helpers
```

### Key Statistics
- **Core Module**: 888 lines (models, repository, services, database)
- **Agents Module**: 3,600+ lines (orchestration, reasoning, tools)
- **UI Module**: 2,400+ lines (windows, panels, dialogs)
- **Config Module**: 150+ lines (Pydantic-based settings)

---

## 2. DATA STRUCTURES & FEATURES

### Core Data Models (4 Primary + Automation Rules)

#### **Task Model**
- `content`: Text description of work to be done
- `notes`: LLM annotations
- `status`: PENDING → ONGOING → PAUSED → COMPLETED
- `created_at`, `updated_at`: Timestamps with auto-update
- **Key Methods**: create, get_by_id, get_all, search, update, delete

#### **Memory Model**
- `content`: Small hints, clues, insights
- `notes`: LLM annotations
- **Purpose**: Accessible knowledge base for future reference
- **Storage**: ID-based retrieval (not passed to LLM by default)
- **Key Methods**: create, get_all, search, update, delete

#### **Goal Model**
- `content`: Expected outcome description
- `notes`: LLM annotations
- `status`: PENDING → COMPLETED
- **Purpose**: Quality verification and output checking
- **Verification**: Separate LLM evaluates if outputs meet goals
- **Key Methods**: create, get_by_id, get_all, search, update, delete

#### **Datavault Model**
- `content`: Large data blob (code, text, outputs)
- `filetype`: Classification (text, py, js, json, md, csv, html, xml)
- `notes`: LLM annotations
- **Purpose**: Avoid token limits for large content
- **Accessible via**: Python API in code execution
- **Key Methods**: store_item, get_item, get_all_items, search_items, update_item, delete_item

#### **AutomationRule Model**
- `name`: Unique identifier
- `enabled`: Boolean flag
- `trigger`: ON_APP_START, DAILY, WEEKLY, MANUAL
- `schedule_cron`: Optional custom cron expression
- `agent_task`: Instruction text for agent
- `last_run_at`: Timestamp of last execution

---

## 3. CURRENT UI PATTERNS & COMPONENTS

### Main Window Architecture
**File**: `gembrain/ui/main_window.py` (17KB)

**Layout**: 3-column design
```
┌─────────────────────────────────────────────────────────────┐
│ Navigation          Main Panel          Context Panel        │
│ Sidebar          (Stacked Widget)      (optional)           │
│                                                              │
│ • Chat       → Chat Panel              • Today's Tasks      │
│ • Tasks      → Tasks Panel             • Recent Memories    │
│ • Goals      → Goals Panel                                  │
│ • Vault      → Datavault Panel                              │
│ ⚙️ Settings                                                 │
└─────────────────────────────────────────────────────────────┘
```

### UI Panels (Widgets)

#### **ChatPanel** (477 lines)
- Main interaction point with AI agent
- Worker thread (`OrchestratorWorker`) runs agent in background
- Split-screen layout:
  - Left: Conversation view
  - Right: Technical details (reasoning, logs)
- Real-time progress updates from iterative reasoning
- Auto-apply actions or manual review mode

#### **TasksPanel** (147 lines)
- Tabbed interface: Pending → Ongoing → Completed
- Double-click to toggle status
- Create new tasks via input dialog
- Display: Content preview + notes

#### **GoalsPanel** (202 lines)
- 3 tabs: Pending, Completed, All
- Double-click to toggle completion
- Statistics footer
- Goal details dialog

#### **DatavaultPanel** (309 lines)
- Filter by filetype (dropdown)
- Display: Icon, type, size, content preview
- Double-click to view full details
- Delete functionality with confirmation
- Stats: item count and total size
- Dialog for storing new data

#### **ContextPanel** (101 lines)
- Right-side panel (optional)
- Shows: Today's tasks + recent memories
- Auto-refreshes when navigation changes
- Contextual information for focus

#### **TechnicalDetailsView** (649 lines)
- Shows reasoning steps, iterations, tool usage
- Real-time log streaming
- Expandable sections for each iteration

#### **SettingsDialog** (562 lines)
- Comprehensive settings UI
- Tabs: General, Gemini, Agent, Storage, Automations
- Real-time validation
- Pydantic model integration

---

## 4. DATA STORAGE & MANAGEMENT

### Database Layer Architecture

**3-Layer Design**:

#### **Layer 1: Models** (`core/models.py` - 125 lines)
- SQLAlchemy declarative models
- Enums for status tracking
- Relationship definitions
- Auto-timestamping with `onupdate`

#### **Layer 2: Repository** (`core/repository.py` - 372 lines)
- Generic `BaseRepository<T>` for common CRUD
- Static methods on concrete repositories
- Search functionality with ILIKE (case-insensitive)
- Update with auto-timestamp
- Delete with existence check

#### **Layer 3: Services** (`core/services.py` - 292 lines)
- Business logic layer
- `TaskService`, `MemoryService`, `GoalService`, `DatavaultService`, `AutomationService`
- Logging and error handling
- Composition pattern (uses repositories)

### Database Connection (`core/db.py` - 130 lines)
- SQLite with foreign key support
- Global engine and session management
- Functions:
  - `init_db()`: Create tables
  - `get_db()`: Session generator
  - `close_db()`: Connection cleanup
  - `recreate_db()`: Complete schema reset

---

## 5. DELETE & EXPORT FUNCTIONALITY

### Delete Functionality (Current Implementation)

#### **Individual Delete Operations**
- **Tasks**: `task_service.delete_task(task_id)`
- **Goals**: `goal_service.delete_goal(goal_id)`
- **Memories**: `memory_service.delete_memory(memory_id)`
- **Datavault**: `datavault_service.delete_item(item_id)`

#### **Bulk Delete: "Delete All Data" Feature**
**Location**: `gembrain/ui/main_window.py` (lines 341-449)

**Process**:
1. Double confirmation dialog
2. Textual confirmation ("DELETE ALL")
3. Count items before deletion
4. Iterate and delete from all 4 repositories
5. Refresh all panels
6. Log warning with deletion summary

**Current Limitations**:
- No selective deletion (all or nothing)
- No export before deletion
- No undo capability

### Export Functionality (MISSING)
- No built-in data export feature
- No CSV/JSON export capability
- Can access data via database directly

---

## 6. SERVICE LAYER ARCHITECTURE

### Service Organization

```
Services (core/services.py)
├── TaskService
│   ├── create_task(content, notes, status)
│   ├── get_task(task_id)
│   ├── get_all_tasks(status=None)
│   ├── get_tasks_by_status(status)
│   ├── get_today_tasks()
│   ├── search_tasks(query)
│   ├── update_task(task_id, **kwargs)
│   └── delete_task(task_id)
│
├── MemoryService
│   ├── create_memory(content, notes)
│   ├── get_memory(memory_id)
│   ├── get_all_memories(limit=None)
│   ├── search_memories(query)
│   ├── update_memory(memory_id, **kwargs)
│   └── delete_memory(memory_id)
│
├── GoalService
│   ├── create_goal(content, notes, status)
│   ├── get_goal(goal_id)
│   ├── get_all_goals(status=None)
│   ├── search_goals(query)
│   ├── update_goal(goal_id, **kwargs)
│   └── delete_goal(goal_id)
│
├── DatavaultService
│   ├── store_item(content, filetype, notes)
│   ├── get_item(item_id)
│   ├── get_all_items(filetype=None)
│   ├── search_items(query)
│   ├── update_item(item_id, **kwargs)
│   └── delete_item(item_id)
│
└── AutomationService
    ├── create_rule(name, trigger, agent_task, ...)
    ├── get_rule(name)
    ├── get_all_rules(enabled_only=False)
    ├── update_last_run(rule_id)
    ├── enable_rule(rule_id, enabled)
    └── delete_rule(rule_id)
```

### Key Design Patterns
- **Repository Pattern**: Abstraction for data access
- **Service Pattern**: Business logic encapsulation
- **Composition**: Services use repositories
- **Static Methods**: Repositories use static methods for flexibility
- **Generic Base**: `BaseRepository<T>` eliminates duplication

---

## 7. AGENTS & ORCHESTRATION

### Orchestrator (`agents/orchestrator.py` - 381 lines)

**Responsibilities**:
- Receives user messages
- Builds context from services (tasks, memories, goals)
- Calls GeminiClient for LLM response
- Executes actions via ActionExecutor
- Optional iterative reasoning mode
- Returns OrchestratorResponse

**Flow**:
```
User Message
    ↓
Build Context (Tasks, Memories, Goals)
    ↓
Call Gemini API
    ↓
Parse Actions (structured JSON)
    ↓
[Iterative Reasoning] OR [Direct Execution]
    ↓
Return Response (text + action results)
```

### Tools & Actions (`agents/tools.py` - 871 lines)

**ActionExecutor**: Executes agent decisions
- 20+ action types (create_task, update_memory, execute_code, etc.)
- Retry logic for transient failures
- Error handling with detailed logging
- Supports code execution with GemBrain API

**Action Categories**:
1. **Task Operations**: create, update, list, search, delete
2. **Memory Operations**: create, update, list, search, delete
3. **Goal Operations**: create, update, list, search, delete
4. **Datavault Operations**: store, get, list, search, update, delete
5. **Code Execution**: execute_code with API access
6. **Query Operations**: list, search across all types

### Code Execution API (`agents/code_api.py` - 662 lines)

**GemBrainAPI**: Exposes database access to executed code
```python
# Available in executed code as 'gb' object
gb.create_task(content, notes, status)
gb.update_task(task_id, ...)
gb.list_tasks(status, limit)
gb.search_tasks(query, limit)
gb.delete_task(task_id)

gb.create_memory(content, notes)
gb.list_memories(limit)
gb.search_memories(query)
gb.delete_memory(memory_id)

gb.create_goal(content, notes, status)
gb.list_goals(status, limit)
gb.search_goals(query)
gb.delete_goal(goal_id)

gb.datavault_store(content, filetype, notes)
gb.datavault_get(item_id)
gb.datavault_list(filetype, limit)
gb.datavault_search(query, limit)
gb.datavault_update(item_id, ...)
gb.datavault_delete(item_id)
```

### Iterative Reasoning (`agents/iterative_reasoner.py` - 1145 lines)

**Purpose**: Complex reasoning via multiple iterations
- Breaks down complex queries into subtasks
- Tracks current subtask and reasoning
- Executes actions in loop
- Verification LLM checks if goals met
- Stops when max iterations or convergence reached

**Key Components**:
- `IterativeReasoner`: Main orchestration
- `ReasoningSession`: Tracks state across iterations
- `_parse_iteration_response()`: Extracts JSON from response
- Goal verification: Checks if outputs meet specified goals
- Error handling: Graceful degradation on failures

### Gemini Client (`agents/gemini_client.py` - 309 lines)
- Wrapper around Google Gemini API
- Configurable model selection
- Temperature and token control
- Error handling and logging

---

## 8. CONFIGURATION & SETTINGS

### Settings Structure (`config/models.py`)

**Root: Settings** (Pydantic BaseModel)
- `api`: APIConfig
- `storage`: StorageConfig
- `agent_behavior`: AgentBehaviorConfig
- `automations`: AutomationConfig
- `ui`: UIConfig

#### **APIConfig**
- `gemini_api_key`: API key for authentication
- `default_model`: Default to "gemini-1.5-pro"
- `max_output_tokens`: 8192 default
- `temperature`: 0.7 default
- `system_prompt_variant`: "second_brain"

#### **StorageConfig**
- `db_path`: `~/.gembrain/gembrain.db`
- `backup_dir`: `~/.gembrain/backups`
- `auto_backup_enabled`: True
- `auto_backup_interval_hours`: 24

#### **AgentBehaviorConfig**
- `auto_structured_actions`: Auto-apply suggestions
- `ask_before_destructive`: Confirmation for deletions
- `max_actions_per_message`: 10
- `enable_code_execution`: True
- `enable_iterative_reasoning`: False
- `max_reasoning_iterations`: 50
- `verification_model`: "gemini-1.5-flash"
- `auto_verify`: True

#### **AutomationConfig**
- `daily_review_enabled`, `daily_review_time`
- `weekly_review_enabled`, `weekly_review_day`, `weekly_review_time`
- `resurface_notes_enabled`, `resurface_notes_age_days`, `resurface_notes_count`

#### **UIConfig**
- `theme`: "light" or "dark"
- `font_family`, `font_size`
- `compact_mode`
- `window_width`, `window_height`
- `show_context_panel`
- `markdown_preview`

### Configuration Manager (`config/manager.py`)
- Loads/saves config from JSON
- Default paths in `~/.gembrain/`
- Pydantic validation
- Hot-reload capabilities

---

## 9. AUTOMATION SYSTEM

### AutomationEngine (`automation/engine.py` - 160+ lines)

**Purpose**: Schedule and run automated tasks

**Features**:
- APScheduler integration
- Background execution
- Cron-based scheduling
- Multiple automation types:
  - Daily Review (reviews completed tasks)
  - Weekly Review (broader summary)
  - Note Resurfacing (resurface old notes)

**API**:
- `start()`: Initialize and schedule
- `stop()`: Cleanup
- `run_automation_now()`: Manual trigger

### Automation Rules (`automation/rules.py`)
- Database-backed custom rules
- Enable/disable individual rules
- Cron expression support
- Last run timestamp tracking

---

## 10. KEY ARCHITECTURAL INSIGHTS

### Strengths
1. **Clean Layering**: Models → Repository → Services → UI
2. **Type Safety**: Full type hints throughout
3. **Extensibility**: Generic BaseRepository pattern
4. **Threading**: Background worker for UI responsiveness
5. **Logging**: Comprehensive logging via loguru
6. **Configuration**: Pydantic with validation
7. **Error Handling**: Try-catch with detailed error messages

### Design Patterns Used
- **Repository Pattern**: Data access abstraction
- **Service Pattern**: Business logic separation
- **Factory Pattern**: Settings creation
- **Observer Pattern**: Signals in PyQt6
- **Worker Thread Pattern**: Async operations
- **Generic/Template Pattern**: BaseRepository<T>

### Current Limitations
1. No data export functionality
2. Memory not easily accessible to LLM
3. No undo capability
4. Automation rules not exposed in UI
5. Limited data filtering/querying options
6. No data compression for large vaults

---

## 11. RECENT CHANGES & CURRENT BRANCH

**Current Branch**: `claude/add-delete-export-features-01XAtWMYYBq2kPyZezUeT89d`

**Recent Commits** (Last 7):
1. `7e8fede`: Fix code execution error and add Delete All Data feature
2. `617288f`: Add comprehensive tool documentation to EVERY iteration
3. `9464da2`: Major improvements: JSON parsing, autonomous prompts, Goals & Datavault UI
4. `a506edd`: Fix JSON parsing to allow control characters in strings
5. `c2dea27`: Add missing TaskService and MemoryService methods
6. `9a4b380`: Fix TaskService missing get_tasks_by_status method
7. `0a6d915`: Remove dead UI panel files

**Latest Features**:
- Delete All Data with double confirmation
- Goals panel UI
- Datavault panel UI
- Fixed iterative reasoning JSON parsing issues

---

## 12. FILE SIZE DISTRIBUTION

```
Largest Files (UI/Logic):
- iterative_reasoner.py: 1145 lines (reasoning logic)
- technical_details_view.py: 649 lines (UI logging)
- code_api.py: 662 lines (API exposure)
- tools.py: 871 lines (action execution)
- prompts.py: 556 lines (system prompts)
- settings_dialog.py: 562 lines (settings UI)
- chat_panel.py: 477 lines (main chat UI)
- orchestrator.py: 381 lines (agent orchestration)
- repository.py: 372 lines (data access)
- services.py: 292 lines (business logic)
```

---

## SUMMARY

GemBrain is a sophisticated desktop application implementing:

1. **AI-Powered Second Brain**: Uses Gemini for intelligent task decomposition
2. **4-Tier Data Structure**: Tasks, Memory, Goals, Datavault
3. **Clean Architecture**: Layered design with clear separation of concerns
4. **Agentic Intelligence**: Iterative reasoning with goal-based verification
5. **Automation**: Scheduled reviews and custom rules
6. **User-Friendly UI**: PyQt6 with multi-panel workspace
7. **Data Ownership**: Local SQLite database

The codebase is well-structured, thoroughly documented, and ready for enhancement with export/delete features.

