# GemBrain Codebase Exploration - Summary

**Date**: November 14, 2025
**Status**: Complete
**Documentation Generated**: 3 comprehensive guides

---

## What Was Explored

I've thoroughly analyzed the GemBrain codebase (approximately 10,000 lines of Python) across 6 major modules to understand:

1. Overall structure and organization ✓
2. Where tasks, memory, goals, and datavault features are implemented ✓
3. Current UI patterns and component structure ✓
4. How data is stored and managed ✓
5. Existing delete and export functionality ✓
6. Service layer architecture ✓

---

## Key Findings

### Architecture Overview
GemBrain is a **6-layer architecture**:
- **UI Layer**: PyQt6 with 3-column design (sidebar, main panel, optional context)
- **Agent Layer**: Gemini orchestration with iterative reasoning capability
- **Service Layer**: Business logic with 5 main services
- **Repository Layer**: Generic CRUD pattern with 5 repositories
- **Model Layer**: 5 SQLAlchemy models (Task, Memory, Goal, Datavault, AutomationRule)
- **Database Layer**: SQLite with auto-timestamping and foreign key support

### Data Models (4 Core + 1 Automation)

**Task Model**
- Content, notes, status (PENDING → ONGOING → PAUSED → COMPLETED)
- Auto-timestamped, indexed by status
- Accessible via UI (TasksPanel) and Python API

**Memory Model**
- Content, notes (small hints and insights)
- ID-based retrieval (not passed to LLM by default)
- Accessible only via Python API and ContextPanel

**Goal Model**
- Content, notes, status (PENDING → COMPLETED)
- For verification and quality checking
- Accessible via UI (GoalsPanel) and Python API

**Datavault Model**
- Content (large blobs), filetype, notes
- Supports: text, py, js, json, md, csv, html, xml
- Accessible via UI (DatavaultPanel) and Python API

**AutomationRule Model**
- Name, trigger type, cron schedule, agent task
- Database-backed but NO UI for management
- Triggers: ON_APP_START, DAILY, WEEKLY, MANUAL

### UI Components (7 Panels)

1. **ChatPanel** (477 lines) - Main interaction point with threaded background worker
2. **TasksPanel** (147 lines) - 3-tab tabbed interface for task status filtering
3. **GoalsPanel** (202 lines) - 3-tab interface with goal completion tracking
4. **DatavaultPanel** (309 lines) - Filetype-filtered data viewing and storage
5. **ContextPanel** (101 lines) - Sidebar showing today's tasks + recent memories
6. **TechnicalDetailsView** (649 lines) - Real-time reasoning logs and iterations
7. **SettingsDialog** (562 lines) - Comprehensive configuration with Pydantic integration

### Current Delete Functionality

**Individual Delete Operations**:
- Each service supports `delete_*` methods
- Delete buttons in UI panels with confirmation dialogs
- Soft confirmation (single click) for individual items

**Bulk Delete - "Delete All Data"** (File Menu):
- Double confirmation + textual confirmation ("DELETE ALL")
- Deletes all tasks, goals, memories, and datavault items
- Logs deletion summary
- **Limitation**: All-or-nothing (no selective deletion)

### Export Functionality (MISSING)

**Current Status**: ❌ Not implemented
- No CSV export
- No JSON export
- No selective export
- Can only access raw SQLite database

---

## Service Layer Details

**5 Service Classes** (core/services.py - 292 lines):
1. **TaskService** - 8 methods (CRUD + filtering by status)
2. **MemoryService** - 6 methods (CRUD + optional limit)
3. **GoalService** - 7 methods (CRUD + filtering by status)
4. **DatavaultService** - 7 methods (CRUD + filtering by filetype)
5. **AutomationService** - 6 methods (CRUD + rule management)

**Repository Pattern**:
- Generic `BaseRepository<T>` eliminates 150+ lines of duplication
- Static methods for flexibility
- Search via ILIKE (case-insensitive)
- Auto-timestamp updates
- Existence checks before deletion

---

## Agent Architecture

### Orchestrator Flow
```
User Message
  → Build Context (fetch tasks, memories, goals)
  → Call Gemini API
  → Parse Actions (structured JSON)
  → [If enabled] Iterative Reasoning Loop
  → Execute Actions (via ActionExecutor)
  → Return Response
```

### Action Types (20+)
- Task: create, update, list, search, delete
- Memory: create, update, list, search, delete
- Goal: create, update, list, search, delete
- Datavault: store, get, list, search, update, delete
- Code Execution: execute_code with GemBrain API access
- Automations: Various automation triggers

### Iterative Reasoning (1145 lines)
- **Enabled by default**: NO (settings.agent_behavior.enable_iterative_reasoning)
- **Max iterations**: Configurable (5-200 range)
- **Verification model**: Separate from main model (default: gemini-1.5-flash)
- **Features**: Goal verification, action history, multi-step subtask decomposition

### Code Execution API (GemBrainAPI)
- Exposed as `gb` object in executed code
- Full access to all 4 core services
- Create, read, update, delete operations
- List and search functionality

---

## Configuration System

**Pydantic-based** (config/models.py):
- **APIConfig**: Gemini API key, model, tokens, temperature
- **StorageConfig**: DB path, backup directory, auto-backup settings
- **AgentBehaviorConfig**: Code execution, iterative reasoning, action confirmation
- **AutomationConfig**: Daily/weekly reviews, note resurfacing schedules
- **UIConfig**: Theme, fonts, window dimensions, context panel visibility

**Stored at**: `~/.gembrain/config.json`
**Managed by**: ConfigManager with hot-reload capabilities

---

## Automation System

**Engine** (automation/engine.py):
- APScheduler-based background execution
- 3 built-in automations: daily_review, weekly_review, resurface_notes
- Manual trigger capability
- Custom cron-based rules support

**Rules** (database-backed):
- Enable/disable individual rules
- Last run timestamp tracking
- Custom schedule expressions

**Limitation**: No UI for creating/managing automation rules

---

## Recent Work (Current Branch)

**Branch**: `claude/add-delete-export-features-01XAtWMYYBq2kPyZezUeT89d`

**Latest Commits**:
1. Fix code execution error and add Delete All Data feature
2. Add comprehensive tool documentation to EVERY iteration
3. Major improvements: JSON parsing, autonomous prompts, Goals & Datavault UI
4. Fix JSON parsing to allow control characters in strings
5. Add missing TaskService and MemoryService methods

**Latest Features**:
- Delete All Data with double confirmation
- Goals panel UI (create, read, toggle status)
- Datavault panel UI (store, view, delete, filter by type)
- Fixed iterative reasoning JSON parsing (handles nested code blocks)
- Missing service methods added

**TODO for Export/Delete Features**:
- CSV/JSON export functionality
- Selective deletion UI (delete specific items)
- Undo capability (optional)
- Memory UI panel (currently only programmatic access)
- Automation rules management UI

---

## Documentation Generated

I've created 3 comprehensive documentation files in the repository:

1. **CODEBASE_OVERVIEW.md** (534 lines)
   - Detailed breakdown of all 6 architecture layers
   - Complete service API documentation
   - Data model explanations
   - UI component descriptions
   - Configuration details

2. **QUICK_REFERENCE.md** (200+ lines)
   - Key files to know
   - Data model cheat sheet
   - Service API patterns
   - Common operations
   - Performance notes
   - Testing examples

3. **ARCHITECTURE_DIAGRAMS.md** (220+ lines)
   - Layered architecture diagram
   - Data flow: user message to response
   - Service-repository pattern
   - UI panel hierarchy
   - Iterative reasoning state machine
   - Code execution sandboxing
   - Configuration hierarchy
   - Database schema (ER diagram)

---

## Architectural Strengths

1. Clean layering with clear separation of concerns
2. Type hints throughout (type-safe)
3. Comprehensive error handling with detailed logging
4. Extensible generic repository pattern
5. Threading for responsive UI
6. Pydantic-based configuration with validation
7. Well-structured service composition

---

## Current Limitations

1. ❌ No data export (CSV, JSON)
2. ❌ No selective deletion UI (only bulk delete)
3. ❌ Memory not easily accessible to users (only programmatic)
4. ❌ Automation rules not exposed in UI
5. ❌ No undo capability
6. ❌ Limited data querying/filtering in UI

---

## File Statistics

**Total Lines of Code**: ~10,000 lines
**Key Modules**:
- Iterative Reasoner: 1145 lines (most complex)
- Technical Details View: 649 lines (UI)
- Code API: 662 lines (agent access)
- Tools/Actions: 871 lines (execution)
- Settings Dialog: 562 lines (UI)
- Prompts: 556 lines (LLM guidance)
- Chat Panel: 477 lines (main UI)
- Orchestrator: 381 lines (coordination)
- Repository: 372 lines (data access)
- Services: 292 lines (business logic)

---

## How to Use This Documentation

1. **Start with QUICK_REFERENCE.md** for a quick overview of key files and APIs
2. **Refer to CODEBASE_OVERVIEW.md** for detailed explanations of each component
3. **Check ARCHITECTURE_DIAGRAMS.md** for visual understanding of data flows
4. **Use CODEBASE_OVERVIEW.md Table of Contents** to navigate to specific topics

---

## Next Steps for Development

If implementing export/delete features, consider:

1. **For Export**:
   - Create ExportService with CSV/JSON/SQLite export methods
   - Add bulk export menu items
   - Support selective/filtered export
   - Add export dialogs to each panel

2. **For Better Deletion**:
   - Create DeleteService with selective delete UI
   - Add checkboxes to panel items
   - Implement delete toolbar
   - Add batch operations

3. **For Missing Features**:
   - Add Memory panel UI
   - Add Automation rules management UI
   - Add undo/trash capability
   - Improve data searching and filtering

---

## Repository Information

**Current Branch**: `claude/add-delete-export-features-01XAtWMYYBq2kPyZezUeT89d`
**Status**: Clean (no uncommitted changes)
**Recent Activity**: Active development on delete/export features

All documentation has been saved to the repository root for future reference.

---

**Exploration Date**: November 14, 2025
**Explored By**: Claude Code (Anthropic)
**Total Analysis Time**: Comprehensive codebase audit
