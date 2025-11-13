# Comprehensive Codebase Refactoring Plan

**Generated:** 2025-11-13  
**Purpose:** Make code modular, remove redundant code, and ensure Tasks are automatically passed with each iteration in the reasoning chain

---

## Executive Summary

This plan addresses three critical objectives:

1. **CRITICAL CHANGE**: Tasks must be automatically passed with each iteration in the reasoning chain
2. **Modularity**: Identify and fix code duplication, tight coupling, and SRP violations
3. **Dead Code Removal**: Remove unused panels, services, and imports from old Notes/Projects architecture

**Impact:** Medium-High complexity, ~8-10 files to modify, no database schema changes required

---

## Part 1: CRITICAL - Task Context in Iterative Reasoning

### Problem Analysis

**Current Behavior:**
1. `Orchestrator._build_context()` fetches Tasks/Memory/Goals ONCE at start
2. This initial context is passed to `IterativeReasoner.reason(initial_context=...)`
3. `IterativeReasoner._build_iteration_context()` reuses `initial_context` but NEVER refreshes data
4. If iteration 2 creates 3 tasks, iteration 3 won't see them!

**Data Flow Trace:**
```
User Query
  ↓
Orchestrator.run_user_message()
  ↓
Orchestrator._build_context() → [memories, tasks, goals] ← Fetched ONCE
  ↓
IterativeReasoner.reason(initial_context) 
  ↓
Loop: Each iteration calls _build_iteration_context()
  ↓
_build_iteration_context():
  - Uses initial_context (stale!)
  - Adds previous iterations
  - Adds action_results ("Created task X")
  - ❌ NEVER fetches current Tasks from database
```

**Why This Matters:**
- LLM cannot see tasks it just created in previous iterations
- Breaks the feedback loop for task management
- LLM might duplicate tasks or lose track of work
- User requirement: "task data, everything, is passed on with each iteration automatically"

### Solution Design

**Approach:** Dynamically fetch current state from database in each iteration

**Files to Modify:**

#### 1. `/home/user/Chrome-Extension/gembrain/agents/iterative_reasoner.py`

**Location:** `_build_iteration_context()` method (lines 648-691)

**Current Implementation:**
```python
def _build_iteration_context(
    self, session: ReasoningSession, initial_context: Optional[List[str]] = None
) -> List[str]:
    """Build context for current iteration."""
    context_blocks = []
    
    if initial_context:
        context_blocks.extend(initial_context)  # ← Static, never refreshed!
    
    # Add previous iterations...
    return context_blocks
```

**Proposed Changes:**

```python
def _build_iteration_context(
    self, session: ReasoningSession, initial_context: Optional[List[str]] = None
) -> List[str]:
    """Build context for current iteration.
    
    CRITICAL: Fetches CURRENT state from database to ensure LLM sees
    all tasks/memories/goals that exist NOW, including those created
    in previous iterations.
    """
    context_blocks = []
    
    # Add static initial context (if any)
    if initial_context:
        context_blocks.extend(initial_context)
    
    # ============================================================
    # CRITICAL: Fetch CURRENT state from database
    # ============================================================
    try:
        from ..core.models import TaskStatus, GoalStatus
        
        # Access services through action_handler
        task_service = self.action_handler.task_service
        memory_service = self.action_handler.memory_service
        goal_service = self.action_handler.goal_service
        
        # Fetch ALL tasks (not just pending/ongoing)
        all_tasks = []
        for status in [TaskStatus.PENDING, TaskStatus.ONGOING, TaskStatus.PAUSED, TaskStatus.COMPLETED]:
            all_tasks.extend(task_service.get_all_tasks(status))
        
        # Limit to most recent for context size management
        all_tasks = all_tasks[:50]
        
        if all_tasks:
            task_context = "=== CURRENT TASKS (as of this iteration) ===\n\n"
            task_context += "All tasks that exist in the system:\n"
            for task in all_tasks:
                status_emoji = {
                    "pending": "⏳",
                    "ongoing": "🔄", 
                    "paused": "⏸️",
                    "completed": "✅"
                }.get(task.status.value, "")
                
                task_context += f"{status_emoji} [{task.id}] {task.content[:100]}"
                if len(task.content) > 100:
                    task_context += "..."
                task_context += f" ({task.status.value})\n"
                
                if task.notes:
                    task_context += f"  Notes: {task.notes[:100]}\n"
            
            context_blocks.append(task_context)
        
        # Fetch current memories
        memories = memory_service.get_all_memories()[:30]
        if memories:
            memory_context = "=== CURRENT MEMORIES ===\n"
            for m in memories:
                memory_context += f"- [{m.id}] {m.content[:100]}\n"
            context_blocks.append(memory_context)
        
        # Fetch current goals
        pending_goals = goal_service.get_all_goals(GoalStatus.PENDING)[:20]
        if pending_goals:
            goal_context = "=== CURRENT GOALS ===\n"
            for g in pending_goals:
                goal_context += f"- [{g.id}] {g.content}\n"
            context_blocks.append(goal_context)
    
    except Exception as e:
        logger.error(f"Failed to fetch current context: {e}")
        # Continue with stale context rather than failing
    
    # Add previous iterations (reasoning, observations, action_results)
    if session.iterations:
        iterations_summary = "=== PREVIOUS ITERATIONS ===\n\n"
        # ... (existing code for iterations) ...
        context_blocks.append(iterations_summary)
    
    return context_blocks
```

**Key Changes:**
1. Access services through `self.action_handler` (which has task_service, memory_service, goal_service)
2. Fetch ALL task statuses (pending, ongoing, paused, completed) for complete visibility
3. Include task IDs, content, status, and notes so LLM can reference and modify them
4. Fetch memories and goals for complete context
5. Add clear section headers so LLM knows this is CURRENT state
6. Graceful error handling - continue with stale context if database fetch fails

**Why Access Through action_handler:**
- `action_handler` is already an instance of `ActionExecutor`
- `ActionExecutor.__init__()` creates `task_service`, `memory_service`, `goal_service` (line 84-87 in tools.py)
- No need to create new service instances or pass additional dependencies

#### 2. `/home/user/Chrome-Extension/gembrain/agents/orchestrator.py`

**Optional Improvement:** Document that initial_context is now supplemented

**Location:** `_build_context()` method (lines 302-353)

**Current:**
```python
def _build_context(self, ui_context: Optional[UIContext] = None) -> List[str]:
    """Build context blocks for agent."""
    blocks = []
    
    # Add memories
    # Add open tasks
    # Add pending goals
    # Add UI context
    
    return blocks
```

**Proposed Change:** Add documentation only

```python
def _build_context(self, ui_context: Optional[UIContext] = None) -> List[str]:
    """Build INITIAL context blocks for agent.
    
    NOTE: When using iterative reasoning, this initial context is passed
    once at the start. IterativeReasoner._build_iteration_context() will
    dynamically refresh Tasks/Memory/Goals state for each iteration to
    ensure the LLM sees current data.
    """
    blocks = []
    # ... (existing code unchanged) ...
    return blocks
```

### Testing Strategy

**Test Case 1: Task Creation Visibility**
```
Iteration 1: Create 3 tasks via execute_code
Iteration 2: List all tasks
Expected: All 3 tasks appear in iteration 2 context
```

**Test Case 2: Task Updates Visibility**
```
Iteration 1: Create task "Write report" (status: pending)
Iteration 2: Update task to "ongoing"
Iteration 3: Check task status
Expected: Iteration 3 sees task with "ongoing" status
```

**Test Case 3: Multi-Status Visibility**
```
Iteration 1: Create tasks with different statuses
Iteration 2: Complete some tasks
Iteration 3: Query "what tasks are completed?"
Expected: LLM can see completed tasks in context
```

---

## Part 2: Modularity Issues

### 2.1 Code Duplication in Repository Layer

**Problem:** All repository classes have nearly identical CRUD patterns

**Location:** `/home/user/Chrome-Extension/gembrain/core/repository.py`

**Evidence:**
- `TaskRepository`, `MemoryRepository`, `GoalRepository`, `DatavaultRepository`
- All have: `create()`, `get_by_id()`, `get_all()`, `search()`, `update()`, `delete()`
- Search pattern is identical across all: `or_(Model.content.ilike(...), Model.notes.ilike(...))`
- Update pattern is identical: loop through kwargs, setattr(), commit, refresh
- Delete pattern is identical: get_by_id(), db.delete(), db.commit()

**Lines of Duplication:**
- `get_by_id`: Lines 38-40, 104-106, 172-174, 243-245 (4x)
- `search`: Lines 51-64, 114-127, 185-198, 256-269 (4x)
- `update`: Lines 67-78, 130-141, 201-212, 272-283 (4x)
- `delete`: Lines 81-88, 144-151, 215-222, 286-293 (4x)

**Solution: Create Generic Repository Base Class**

```python
# gembrain/core/repository.py (new base class)

from typing import TypeVar, Generic, List, Optional, Type
from sqlalchemy.orm import Session
from datetime import datetime

T = TypeVar('T')

class BaseRepository(Generic[T]):
    """Generic repository with common CRUD operations."""
    
    def __init__(self, model_class: Type[T]):
        self.model_class = model_class
    
    @staticmethod
    def get_by_id(db: Session, model_class: Type[T], item_id: int) -> Optional[T]:
        """Get item by ID."""
        return db.query(model_class).filter(model_class.id == item_id).first()
    
    @staticmethod
    def search(
        db: Session, 
        model_class: Type[T], 
        query_text: str,
        search_fields: List[str] = None
    ) -> List[T]:
        """Search items by specified fields."""
        if not search_fields:
            search_fields = ['content', 'notes']
        
        search_pattern = f"%{query_text}%"
        filters = []
        
        for field in search_fields:
            if hasattr(model_class, field):
                filters.append(getattr(model_class, field).ilike(search_pattern))
        
        return (
            db.query(model_class)
            .filter(or_(*filters))
            .order_by(model_class.created_at.desc())
            .all()
        )
    
    @staticmethod
    def update(
        db: Session, 
        model_class: Type[T], 
        item_id: int, 
        **kwargs
    ) -> Optional[T]:
        """Update item fields."""
        item = BaseRepository.get_by_id(db, model_class, item_id)
        if not item:
            return None
        
        for key, value in kwargs.items():
            if hasattr(item, key):
                setattr(item, key, value)
        
        if hasattr(item, 'updated_at'):
            item.updated_at = datetime.now()
        
        db.commit()
        db.refresh(item)
        return item
    
    @staticmethod
    def delete(
        db: Session, 
        model_class: Type[T], 
        item_id: int
    ) -> bool:
        """Delete an item."""
        item = BaseRepository.get_by_id(db, model_class, item_id)
        if not item:
            return False
        
        db.delete(item)
        db.commit()
        return True


# Then simplify specific repositories:
class TaskRepository(BaseRepository[Task]):
    """Repository for Task operations."""
    
    @staticmethod
    def create(
        db: Session,
        content: str,
        notes: str = "",
        status: TaskStatus = TaskStatus.PENDING,
    ) -> Task:
        """Create a new task."""
        task = Task(content=content, notes=notes, status=status)
        db.add(task)
        db.commit()
        db.refresh(task)
        return task
    
    @staticmethod
    def get_by_id(db: Session, task_id: int) -> Optional[Task]:
        return BaseRepository.get_by_id(db, Task, task_id)
    
    @staticmethod
    def get_all(db: Session, status: Optional[TaskStatus] = None) -> List[Task]:
        """Get all tasks, optionally filtered by status."""
        query = db.query(Task)
        if status:
            query = query.filter(Task.status == status)
        return query.order_by(Task.created_at.desc()).all()
    
    @staticmethod
    def search(db: Session, query_text: str) -> List[Task]:
        return BaseRepository.search(db, Task, query_text)
    
    @staticmethod
    def update(db: Session, task_id: int, **kwargs) -> Optional[Task]:
        return BaseRepository.update(db, Task, task_id, **kwargs)
    
    @staticmethod
    def delete(db: Session, task_id: int) -> bool:
        return BaseRepository.delete(db, Task, task_id)
```

**Impact:**
- Reduces ~150 lines of duplicated code
- Easier to maintain - fix bugs in one place
- Consistent behavior across all repositories

### 2.2 Service Layer Duplication

**Problem:** Services have nearly identical wrapper methods

**Location:** `/home/user/Chrome-Extension/gembrain/core/services.py`

**Similar Pattern:**
- All services wrap repository calls
- All have identical logging patterns
- Very thin wrappers with no added value

**Solution Options:**

**Option A (Conservative):** Keep services as-is for explicit interface
- PRO: Clear, explicit interfaces
- CON: Still duplicated code

**Option B (Aggressive):** Merge into repositories and remove service layer
- PRO: Less code, simpler architecture
- CON: Breaks separation of concerns, couples business logic to data layer

**Recommendation:** Keep services but simplify. The service layer provides:
1. Transaction management
2. Business logic (even if minimal now)
3. Logging/monitoring
4. Future extensibility

### 2.3 Code API Duplication

**Problem:** `GemBrainAPI` has similar CRUD wrappers

**Location:** `/home/user/Chrome-Extension/gembrain/agents/code_api.py` (610 lines)

**Duplication:**
- Task operations: Lines 32-169
- Memory operations: Lines 175-297
- Goal operations: Lines 303-440
- Datavault operations: Lines 446-578

Each section has: create, get, list, search, update, delete with similar patterns

**Solution:** Use dynamic method generation

```python
class GemBrainAPI:
    """API for code execution."""
    
    def __init__(self, db_session, services: Dict[str, Any]):
        self.db = db_session
        self.task_service = services.get("task_service")
        self.memory_service = services.get("memory_service")
        self.goal_service = services.get("goal_service")
        self.datavault_service = services.get("datavault_service")
    
    def _generic_create(
        self, 
        service, 
        entity_name: str,
        content: str, 
        notes: str = "", 
        **kwargs
    ):
        """Generic create method."""
        try:
            entity = service.create(content, notes, **kwargs)
            logger.info(f"✅ Code created {entity_name}: {entity.id}")
            return {
                "id": entity.id,
                "content": entity.content,
                "notes": entity.notes,
                "created_at": entity.created_at.isoformat(),
                **{k: getattr(entity, k).value if hasattr(getattr(entity, k), 'value') else getattr(entity, k) 
                   for k in kwargs.keys()}
            }
        except Exception as e:
            logger.error(f"Failed to create {entity_name}: {e}")
            raise
    
    def create_task(self, content: str, notes: str = "", status: str = "pending"):
        """Create a new task."""
        from ..core.models import TaskStatus
        return self._generic_create(
            self.task_service, 
            "task", 
            content, 
            notes, 
            status=TaskStatus(status)
        )
    
    def create_memory(self, content: str, notes: str = ""):
        """Create a new memory."""
        return self._generic_create(self.memory_service, "memory", content, notes)
    
    # Similar for list, search, update, delete...
```

**Impact:**
- Reduces ~400 lines to ~150 lines
- Easier to add new entity types

---

## Part 3: Dead Code Removal

### 3.1 Unused Panel Files

**Files to DELETE:**

1. `/home/user/Chrome-Extension/gembrain/ui/widgets/notes_panel.py` (192 lines)
   - References `NoteService` which no longer exists
   - Notes were removed in Phase 2 refactor
   - No longer used in `main_window.py`

2. `/home/user/Chrome-Extension/gembrain/ui/widgets/projects_panel.py` (~150 lines)
   - References `ProjectService` which no longer exists
   - Projects were removed in Phase 2 refactor
   - No longer used in `main_window.py`

3. `/home/user/Chrome-Extension/gembrain/ui/widgets/vault_panel.py` (~100 lines)
   - References `VaultService` which no longer exists
   - Replaced by Datavault in Phase 2 refactor
   - No longer used in `main_window.py`

**Impact:** Remove ~450 lines of dead UI code

### 3.2 Unused Imports

**Search Pattern:** Files importing non-existent services

```bash
grep -r "NoteService\|ProjectService\|VaultService" gembrain/
```

**Expected to find and remove:**
- Any lingering imports in other files
- Type hints referencing these services
- Documentation mentioning these services

### 3.3 Commented-Out Code

**Manual Review Required:** Check all files with comments for:
- Large commented-out code blocks (>5 lines)
- Old implementations that should be removed
- TODOs that are outdated

**Files with many comments (need review):**
- `gembrain/agents/prompts.py` (556 lines, extensive documentation - keep)
- `gembrain/agents/iterative_reasoner.py` (837 lines, check for dead code)
- `gembrain/agents/tools.py` (863 lines, check for dead code)

---

## Part 4: Coupling Issues

### 4.1 Orchestrator Tight Coupling

**Problem:** Orchestrator directly creates and manages multiple services

**Location:** `/home/user/Chrome-Extension/gembrain/agents/orchestrator.py` (lines 38-55)

```python
def __init__(self, db: Session, settings: Settings):
    self.db = db
    self.settings = settings
    self.gemini_client = GeminiClient(settings)
    self.action_executor = ActionExecutor(db, ...)
    self.task_service = TaskService(db)  # ← Tight coupling
    self.memory_service = MemoryService(db)  # ← Tight coupling
    self.goal_service = GoalService(db)  # ← Tight coupling
```

**Issue:**
- Orchestrator knows about 6+ different classes
- Hard to test (need to mock everything)
- Changes to services require changes to Orchestrator

**Solution: Dependency Injection**

```python
@dataclass
class OrchestratorDependencies:
    """Dependencies for Orchestrator."""
    db: Session
    settings: Settings
    gemini_client: GeminiClient
    action_executor: ActionExecutor
    task_service: TaskService
    memory_service: MemoryService
    goal_service: GoalService


class Orchestrator:
    """Orchestrates agent interactions."""
    
    def __init__(self, deps: OrchestratorDependencies):
        """Initialize with dependencies."""
        self.deps = deps
    
    # Use self.deps.task_service instead of self.task_service
```

**OR use Factory Pattern:**

```python
class OrchestratorFactory:
    """Factory for creating Orchestrator with all dependencies."""
    
    @staticmethod
    def create(db: Session, settings: Settings) -> Orchestrator:
        """Create fully configured Orchestrator."""
        gemini_client = GeminiClient(settings)
        action_executor = ActionExecutor(db, ...)
        task_service = TaskService(db)
        memory_service = MemoryService(db)
        goal_service = GoalService(db)
        
        return Orchestrator(
            db=db,
            settings=settings,
            gemini_client=gemini_client,
            action_executor=action_executor,
            task_service=task_service,
            memory_service=memory_service,
            goal_service=goal_service,
        )
```

**Recommendation:** Factory pattern is simpler and doesn't require changing all call sites

### 4.2 ActionExecutor Service Management

**Problem:** ActionExecutor creates services internally

**Location:** `/home/user/Chrome-Extension/gembrain/agents/tools.py` (lines 83-87)

```python
def __init__(self, db: Session, ...):
    self.db = db
    self.task_service = TaskService(db)  # ← Creates its own
    self.memory_service = MemoryService(db)
    self.goal_service = GoalService(db)
    self.datavault_service = DatavaultService(db)
```

**Issue:**
- Same services created multiple times (in Orchestrator AND ActionExecutor)
- No sharing of service instances
- Harder to mock for testing

**Solution:** Pass services via constructor

```python
def __init__(
    self,
    db: Session,
    task_service: TaskService,
    memory_service: MemoryService,
    goal_service: GoalService,
    datavault_service: DatavaultService,
    enable_code_execution: bool = True,
    max_retries: int = 3,
):
    """Initialize with injected services."""
    self.db = db
    self.task_service = task_service
    self.memory_service = memory_service
    self.goal_service = goal_service
    self.datavault_service = datavault_service
    # ...
```

---

## Part 5: Single Responsibility Violations

### 5.1 Orchestrator Does Too Much

**Problem:** `Orchestrator` handles:
1. User message routing
2. Context building
3. Iterative reasoning orchestration
4. Action execution management
5. Response formatting

**Recommendation:** Split into:
- `MessageRouter` - Route messages to appropriate handler
- `ContextBuilder` - Build context for LLM
- `ReasoningCoordinator` - Coordinate iterative reasoning
- `Orchestrator` - High-level coordination only

**Impact:** Large refactor, defer to Phase 3

### 5.2 IterativeReasoner Responsibilities

**Problem:** Handles both reasoning AND verification

**Current:**
- `reason()` - Run iterative reasoning loop
- `verify()` - Verify reasoning quality
- `_build_iteration_context()` - Context management
- `_build_verification_context()` - Verification context
- `_parse_iteration_response()` - Response parsing
- `_parse_verification_response()` - Verification parsing

**Recommendation:** Split into:
- `IterativeReasoner` - Just reasoning loop
- `ReasoningVerifier` - Just verification
- `ResponseParser` - Just parsing

**Impact:** Medium refactor, provides better separation

---

## Implementation Order

### Phase 1: Critical Fix (DO FIRST)
**Priority:** 🔴 CRITICAL  
**Files:** 1-2  
**Estimated Time:** 2-3 hours  
**Risk:** Low

1. Modify `IterativeReasoner._build_iteration_context()` to fetch current Tasks/Memory/Goals
2. Test thoroughly with multi-iteration scenarios
3. Document the change

**Why First:** User-critical requirement, fixes broken feedback loop

### Phase 2: Dead Code Removal
**Priority:** 🟡 MEDIUM  
**Files:** 3-5  
**Estimated Time:** 1-2 hours  
**Risk:** Very Low

1. Delete `notes_panel.py`, `projects_panel.py`, `vault_panel.py`
2. Search and remove unused imports
3. Remove commented-out code blocks

**Why Second:** Easy wins, reduces confusion, no dependencies

### Phase 3: Repository Refactoring
**Priority:** 🟡 MEDIUM  
**Files:** 1  
**Estimated Time:** 3-4 hours  
**Risk:** Medium (database operations)

1. Create `BaseRepository` class
2. Refactor `TaskRepository` to use base
3. Test thoroughly
4. Refactor remaining repositories

**Why Third:** Improves maintainability, but doesn't break functionality

### Phase 4: Code API Simplification
**Priority:** 🟢 LOW  
**Files:** 1  
**Estimated Time:** 2-3 hours  
**Risk:** Low

1. Add generic helper methods to `GemBrainAPI`
2. Refactor CRUD methods to use helpers
3. Test code execution

**Why Fourth:** Nice-to-have, reduces duplication

### Phase 5: Dependency Injection (Optional)
**Priority:** 🔵 OPTIONAL  
**Files:** 2-3  
**Estimated Time:** 4-6 hours  
**Risk:** Medium (affects initialization flow)

1. Create `OrchestratorFactory`
2. Update call sites
3. Comprehensive testing

**Why Last:** Architectural improvement, not urgent

---

## Risks and Mitigations

### Risk 1: Breaking Iteration Context
**Probability:** Medium  
**Impact:** High  
**Mitigation:**
- Comprehensive testing before deployment
- Keep fallback to initial_context if database fetch fails
- Monitor logs for errors

### Risk 2: Performance Degradation
**Probability:** Low  
**Impact:** Medium  
**Cause:** Fetching tasks on every iteration
**Mitigation:**
- Limit task count (50 max)
- Use database indexes (already exist)
- Monitor iteration times

### Risk 3: Repository Refactor Breaking Tests
**Probability:** Medium  
**Impact:** Medium  
**Mitigation:**
- Refactor one repository at a time
- Run tests after each change
- Keep old code in comments until verified

---

## Testing Checklist

### Part 1 - Task Context
- [ ] Create task in iteration 1, see it in iteration 2
- [ ] Update task status, see updated status in next iteration
- [ ] Create 10 tasks via code, all visible in next iteration
- [ ] Complete tasks, see completed status
- [ ] Verify no performance degradation

### Part 2 - Modularity
- [ ] All repository tests pass
- [ ] All service tests pass
- [ ] Code API tests pass
- [ ] Integration tests pass

### Part 3 - Dead Code
- [ ] Application starts without errors
- [ ] No import errors
- [ ] UI loads correctly
- [ ] No references to deleted panels

---

## Metrics

### Before Refactoring
- Total Python LOC: 9,397
- Repository duplication: ~150 lines (4 repos × ~35 lines each)
- Code API duplication: ~400 lines
- Dead UI code: ~450 lines
- Files with unused imports: TBD (search required)

### After Refactoring (Estimated)
- Lines removed: ~1,000
- Lines added: ~200 (BaseRepository, improved context building)
- Net reduction: ~800 lines (-8.5%)
- Improved maintainability: High
- Improved testability: Medium
- Reduced coupling: Medium

---

## Appendix A: File Inventory

### Critical Files (Part 1)
- `gembrain/agents/iterative_reasoner.py` (837 lines) - MODIFY
- `gembrain/agents/orchestrator.py` (381 lines) - DOCUMENT

### Duplication Files (Part 2)
- `gembrain/core/repository.py` (366 lines) - REFACTOR
- `gembrain/core/services.py` (254 lines) - REVIEW
- `gembrain/agents/code_api.py` (609 lines) - REFACTOR
- `gembrain/agents/tools.py` (863 lines) - MODIFY

### Dead Code Files (Part 3)
- `gembrain/ui/widgets/notes_panel.py` (192 lines) - DELETE
- `gembrain/ui/widgets/projects_panel.py` (~150 lines) - DELETE
- `gembrain/ui/widgets/vault_panel.py` (~100 lines) - DELETE

---

## Appendix B: Data Flow Diagrams

### Current Iteration Context Flow (BROKEN)
```
Start
  ↓
Orchestrator._build_context()
  → Fetch Tasks (once)
  → Fetch Memory (once)
  → Fetch Goals (once)
  → Return initial_context
  ↓
IterativeReasoner.reason(initial_context)
  ↓
Iteration 1
  → _build_iteration_context()
    → Use initial_context (has 3 tasks)
    → Add previous iterations (none)
  → LLM sees 3 tasks
  → Execute actions: Create 2 new tasks
  ↓
Iteration 2
  → _build_iteration_context()
    → Use initial_context (STILL has 3 tasks!) ❌
    → Add previous iterations (shows "Created 2 tasks")
  → LLM sees 3 tasks in context (missing the 2 new ones!)
  → LLM might create duplicates or get confused
```

### Proposed Iteration Context Flow (FIXED)
```
Start
  ↓
Orchestrator._build_context()
  → Build minimal initial context (optional)
  → Return initial_context
  ↓
IterativeReasoner.reason(initial_context)
  ↓
Iteration 1
  → _build_iteration_context()
    → Fetch current Tasks from DB (3 tasks)
    → Fetch current Memory from DB
    → Fetch current Goals from DB
    → Add previous iterations (none)
  → LLM sees 3 tasks
  → Execute actions: Create 2 new tasks
  ↓
Iteration 2
  → _build_iteration_context()
    → Fetch current Tasks from DB (5 tasks now!) ✅
    → Fetch current Memory from DB
    → Fetch current Goals from DB
    → Add previous iterations
  → LLM sees ALL 5 tasks in context
  → LLM can reference the 2 new tasks it created
  → Feedback loop is complete!
```

---

## Appendix C: Key Code References

### Services Location
```python
# In ActionExecutor (tools.py line 84-87)
self.task_service = TaskService(db)
self.memory_service = MemoryService(db)
self.goal_service = GoalService(db)
self.datavault_service = DatavaultService(db)

# Accessible in IterativeReasoner via:
self.action_handler.task_service
self.action_handler.memory_service
self.action_handler.goal_service
```

### Task Statuses
```python
# From core/models.py line 21-27
class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    ONGOING = "ongoing"
    PAUSED = "paused"
    COMPLETED = "completed"
```

### Repository Methods
```python
# Task CRUD (all repos follow same pattern)
TaskRepository.create(db, content, notes, status)
TaskRepository.get_by_id(db, task_id)
TaskRepository.get_all(db, status=None)
TaskRepository.search(db, query_text)
TaskRepository.update(db, task_id, **kwargs)
TaskRepository.delete(db, task_id)
```

---

## Questions for Review

1. **Part 1 Priority:** Should we implement full context refresh (Tasks + Memory + Goals) or just Tasks?
   - Recommendation: All three for consistency

2. **Repository Refactor:** Should we use BaseRepository or keep explicit code?
   - Recommendation: Use BaseRepository - cleaner and maintainable

3. **Service Layer:** Keep services or merge into repositories?
   - Recommendation: Keep services - provides good separation

4. **Code API:** Simplify with generic methods or keep explicit?
   - Recommendation: Simplify - reduces ~400 lines with minimal risk

5. **Dependency Injection:** Implement now or defer?
   - Recommendation: Defer to Phase 3 - not urgent

---

## Conclusion

This plan addresses all three objectives:

1. ✅ **Critical Fix**: Tasks will be automatically passed with each iteration
2. ✅ **Modularity**: Identified and planned fixes for duplication and coupling
3. ✅ **Dead Code**: Identified unused files and imports for removal

**Recommended Approach:** Implement in phases, starting with Part 1 (critical fix), then Part 3 (easy wins), then Parts 2 and 4 (refactoring).

**Total Estimated Time:** 15-20 hours across all phases  
**Risk Level:** Low-Medium (Phase 1 is low risk, Phases 2-4 are medium risk)  
**Expected Impact:** High (improves reliability, maintainability, and reduces confusion)

---

**Document Version:** 1.0  
**Author:** Claude (Sonnet 4.5)  
**Review Status:** Pending user review
