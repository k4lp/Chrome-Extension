================================================================================
                    GEMBRAIN ARCHITECTURE DIAGRAMS
================================================================================

1. LAYERED ARCHITECTURE
================================================================================

    UI LAYER (PyQt6)
    ├── MainWindow (3-column layout)
    ├── ChatPanel (conversation + technical details)
    ├── TasksPanel (tabbed view)
    ├── GoalsPanel (tabbed view)
    ├── DatavaultPanel (filtered view)
    ├── ContextPanel (sidebar info)
    └── SettingsDialog (configuration)
            ↓
    AGENT LAYER (AI Orchestration)
    ├── Orchestrator (main coordinator)
    ├── IterativeReasoner (multi-step logic)
    ├── ActionExecutor (executes decisions)
    ├── GeminiClient (API wrapper)
    ├── CodeExecutor (runs Python)
    └── GemBrainAPI (exposes DB to code)
            ↓
    SERVICE LAYER (Business Logic)
    ├── TaskService
    ├── MemoryService
    ├── GoalService
    ├── DatavaultService
    └── AutomationService
            ↓
    REPOSITORY LAYER (Data Access)
    ├── TaskRepository (CRUD)
    ├── MemoryRepository (CRUD)
    ├── GoalRepository (CRUD)
    ├── DatavaultRepository (CRUD)
    └── AutomationRuleRepository (CRUD)
            ↓
    MODEL LAYER (Data Structures)
    ├── Task (content, notes, status)
    ├── Memory (content, notes)
    ├── Goal (content, notes, status)
    ├── Datavault (content, filetype, notes)
    └── AutomationRule (name, trigger, task)
            ↓
    DATABASE LAYER (SQLite)
    └── ~/.gembrain/gembrain.db


2. DATA FLOW: USER MESSAGE TO RESPONSE
================================================================================

User Input
    ↓
[Chat Panel]
    ↓
OrchestratorWorker (background thread)
    ↓
[Orchestrator.run_user_message()]
    ├─→ Build Context:
    │    ├─ TaskService.get_all_tasks()
    │    ├─ MemoryService.get_all_memories(limit)
    │    └─ GoalService.get_all_goals()
    │
    ├─→ Call LLM:
    │    └─ GeminiClient.call_gemini(system_prompt + context + message)
    │
    ├─→ Parse Response:
    │    └─ Extract actions (JSON structured format)
    │
    ├─→ Check Iterative Reasoning:
    │    If enabled:
    │    └─ IterativeReasoner.reason(query, max_iterations, verification_model)
    │        └─ Loop:
    │            ├─ Call Gemini for next iteration
    │            ├─ Execute actions
    │            ├─ Verify with verification_model
    │            └─ Continue or stop
    │
    └─→ Execute Actions:
         └─ ActionExecutor.execute_action(action_type, **params)
             ├─ create_task → TaskService.create_task()
             ├─ update_memory → MemoryService.update_memory()
             ├─ datavault_store → DatavaultService.store_item()
             ├─ execute_code → CodeExecutor.execute(code)
             │   └─ Has access to GemBrainAPI (gb.*)
             └─ [20+ other actions]
    ↓
Return OrchestratorResponse (text + results)
    ↓
[Chat Panel] Display response
    ↓
[Context Panel] Refresh
[Tasks Panel] Refresh
[Goals Panel] Refresh
[Datavault Panel] Refresh


3. SERVICE-REPOSITORY PATTERN
================================================================================

Service Layer                Repository Layer           Database
┌──────────────────┐        ┌─────────────────┐       ┌─────────────┐
│ TaskService      │        │ TaskRepository  │       │ SQLite DB   │
├──────────────────┤        ├─────────────────┤       ├─────────────┤
│ create_task()    │───────→│ create()        │──────→│ Tasks table │
│ get_task()       │───────→│ get_by_id()     │──────→│             │
│ get_all_tasks()  │───────→│ get_all()       │──────→│             │
│ search_tasks()   │───────→│ search()        │──────→│             │
│ update_task()    │───────→│ update()        │──────→│             │
│ delete_task()    │───────→│ delete()        │──────→│             │
└──────────────────┘        └─────────────────┘       └─────────────┘

Same pattern for:
- MemoryService ←→ MemoryRepository
- GoalService ←→ GoalRepository
- DatavaultService ←→ DatavaultRepository


4. UI PANEL HIERARCHY
================================================================================

MainWindow (QMainWindow)
├── Menu Bar
│   ├── File (Backup, Migrate, Delete All, Exit)
│   └── Automation (Daily, Weekly, Resurface)
│
├── Central Widget (QHBoxLayout)
│   ├── Navigation Sidebar (QWidget)
│   │   ├── Title
│   │   ├── Nav List (Chat, Tasks, Goals, Vault)
│   │   └── Settings Button
│   │
│   ├── Stacked Widget (Main Panel - stretch=3)
│   │   ├── ChatPanel
│   │   │   ├── ConversationView (left side)
│   │   │   └── TechnicalDetailsView (right side)
│   │   │
│   │   ├── TasksPanel
│   │   │   └── QTabWidget
│   │   │       ├── Pending List
│   │   │       ├── Ongoing List
│   │   │       └── Completed List
│   │   │
│   │   ├── GoalsPanel
│   │   │   └── QTabWidget
│   │   │       ├── Pending List
│   │   │       ├── Completed List
│   │   │       └── All List
│   │   │
│   │   └── DatavaultPanel
│   │       ├── Filetype Filter
│   │       └── Items List
│   │
│   └── Context Panel (optional - stretch=1)
│       ├── Today's Tasks
│       └── Recent Memories
│
└── Status Bar (CustomStatusBar)


5. ITERATIVE REASONING STATE MACHINE
================================================================================

Start
  ↓
Initialize ReasoningSession
  ├─ iteration: 0
  ├─ current_subtask: 0
  ├─ reasoning: ""
  ├─ action_history: []
  └─ completed_goals: []
  ↓
Loop (while iteration < max_iterations):
  ↓
  Call Gemini with:
  ├─ Current state
  ├─ Completed actions so far
  └─ Goals to verify
  ↓
  Parse iteration block (JSON):
  ├─ iteration number
  ├─ current_subtask
  ├─ reasoning
  ├─ action_list
  └─ next_status
  ↓
  Execute Actions
  ├─ For each action
  └─ Capture results
  ↓
  Check Completion:
  ├─ If status = "COMPLETE" → Exit loop
  ├─ If verification_model approves goals → Exit loop
  └─ Else → Continue loop
  ↓
Return final result


6. CODE EXECUTION SANDBOXING
================================================================================

ChatPanel [User code]
    ↓
CodeExecutor.execute(code_string)
    ↓
Create safe namespace with:
├─ __builtins__ (filtered)
├─ gb = GemBrainAPI(db, services)
├─ import functions
└─ other allowed modules
    ↓
Execute code in namespace:
exec(code, {"gb": gb, ...})
    ↓
Capture output + any exceptions
    ↓
Return ExecutionResult
├─ stdout
├─ stderr
├─ error_message
└─ execution_time


7. CONFIGURATION HIERARCHY
================================================================================

Settings (Pydantic BaseModel)
├── api: APIConfig
│   ├─ gemini_api_key
│   ├─ default_model
│   ├─ max_output_tokens
│   ├─ temperature
│   └─ system_prompt_variant
│
├── storage: StorageConfig
│   ├─ db_path (default: ~/.gembrain/gembrain.db)
│   ├─ backup_dir (default: ~/.gembrain/backups)
│   ├─ auto_backup_enabled
│   └─ auto_backup_interval_hours
│
├── agent_behavior: AgentBehaviorConfig
│   ├─ auto_structured_actions
│   ├─ ask_before_destructive
│   ├─ enable_code_execution
│   ├─ enable_iterative_reasoning
│   ├─ max_reasoning_iterations
│   ├─ verification_model
│   └─ auto_verify
│
├── automations: AutomationConfig
│   ├─ daily_review_enabled + time
│   ├─ weekly_review_enabled + day + time
│   └─ resurface_notes settings
│
└── ui: UIConfig
    ├─ theme
    ├─ font_family + font_size
    ├─ window dimensions
    ├─ show_context_panel
    └─ markdown_preview

Loaded from: ~/.gembrain/config.json
Managed by: ConfigManager


8. DATABASE SCHEMA (Entity Relationship)
================================================================================

┌─────────────────────┐
│ Tasks               │
├─────────────────────┤
│ id (PK)             │
│ content (Text)      │
│ notes (Text)        │
│ status (Enum)       │├─ PENDING
│                     │├─ ONGOING
│ created_at (Date)   │├─ PAUSED
│ updated_at (Date)   │└─ COMPLETED
└─────────────────────┘

┌─────────────────────┐
│ Memories            │
├─────────────────────┤
│ id (PK)             │
│ content (Text)      │
│ notes (Text)        │
│ created_at (Date)   │
│ updated_at (Date)   │
└─────────────────────┘

┌─────────────────────┐
│ Goals               │
├─────────────────────┤
│ id (PK)             │
│ content (Text)      │
│ notes (Text)        │
│ status (Enum)       │├─ PENDING
│                     │└─ COMPLETED
│ created_at (Date)   │
│ updated_at (Date)   │
└─────────────────────┘

┌──────────────────────┐
│ Datavault            │
├──────────────────────┤
│ id (PK)              │
│ content (LargeText)  │
│ filetype (String)    │├─ text|py|js|json|md|csv|html|xml
│ notes (Text)         │
│ created_at (Date)    │
│ updated_at (Date)    │
└──────────────────────┘

┌──────────────────────┐
│ AutomationRules      │
├──────────────────────┤
│ id (PK)              │
│ name (String, unique)│
│ enabled (Boolean)    │
│ trigger (Enum)       │├─ ON_APP_START
│ schedule_cron (Str)  │├─ DAILY
│ agent_task (Text)    │├─ WEEKLY
│ last_run_at (Date)   │└─ MANUAL
└──────────────────────┘

No foreign key relationships - independent tables


================================================================================
