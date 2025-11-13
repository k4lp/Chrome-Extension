# GemBrain Database Migration Guide

## ⚠️ IMPORTANT: Data Structure Refactor

GemBrain has undergone a **major data structure refactor**. The old data structures (Notes, Projects, VaultItems) have been **completely replaced** with new structures designed for iterative reasoning workflows.

## What Changed?

### Old Data Structures (REMOVED):
- ❌ **Notes** (title, content, tags)
- ❌ **Projects** (name, description, tags)
- ❌ **VaultItems** (title, type, path_or_url)
- ❌ **Old Tasks** (title, status: TODO/DOING/DONE/STALE)

### New Data Structures:
- ✅ **Tasks** - Decomposed work items
  - Fields: id, content, notes, status (pending/ongoing/paused/completed)
  - Purpose: Track what needs to be done; LLM can modify mid-execution

- ✅ **Memory** - Small hints, clues, data
  - Fields: id, content, notes
  - Purpose: Store insights and facts; accessible on demand

- ✅ **Goals** - Expected outcomes for verification
  - Fields: id, content, notes, status (pending/completed)
  - Purpose: Define success criteria; verification LLM checks if met

- ✅ **Datavault** - Large data storage
  - Fields: id, content, filetype, notes
  - Purpose: Store large blobs (code, text, outputs) to avoid token limits

## Migration Options

### Option 1: Using the UI (Recommended)

1. **Start GemBrain**
   ```bash
   python run.py
   ```

2. **Go to File Menu → Migrate to New Schema**

3. **Read the warning carefully** - ALL existing data will be deleted!

4. **Confirm migration**
   - A backup will be created automatically
   - Database will be recreated with new schema
   - Application will close

5. **Restart GemBrain**

### Option 2: Using Command-Line Script

1. **Run the migration script**
   ```bash
   python migrate_db.py
   ```

2. **Type 'yes' to confirm** when prompted

3. **Or skip confirmation** (dangerous!)
   ```bash
   python migrate_db.py --yes
   ```

### Option 3: Manual Migration

```python
from gembrain.config.manager import get_config_manager
from gembrain.core.db import close_db, recreate_db

config_manager = get_config_manager()
settings = config_manager.load()

# Close existing connections
close_db()

# Recreate database (CAUTION: Deletes all data!)
recreate_db(settings.storage.db_path)
```

## What Happens During Migration?

1. **Backup Created**: Your current database is backed up to `~/.gembrain/backups/gembrain_pre_migration_YYYYMMDD_HHMMSS.db`

2. **Old Tables Dropped**: All existing tables are removed (Notes, Projects, old Tasks, etc.)

3. **New Tables Created**: Fresh schema with Tasks, Memory, Goals, Datavault

4. **All Data Lost**: Your old notes, projects, and tasks are GONE (but backed up)

## After Migration

### New API Methods Available

**Tasks:**
```python
gb.create_task(content, notes="", status="pending")
gb.update_task(task_id, content=None, notes=None, status=None)
gb.list_tasks(status=None, limit=50)
gb.search_tasks(query, limit=20)
```

**Memory:**
```python
gb.create_memory(content, notes="")
gb.update_memory(memory_id, content=None, notes=None)
gb.list_memories(limit=50)
gb.search_memories(query, limit=20)
```

**Goals:**
```python
gb.create_goal(content, notes="", status="pending")
gb.list_goals(status=None, limit=50)
```

**Datavault:**
```python
gb.datavault_store(content, filetype="text", notes="")
gb.datavault_get(item_id)
gb.datavault_list(filetype=None, limit=50)
gb.datavault_search(query, limit=20)
```

### Action Types

**In `actions` blocks:**
```json
{
  "actions": [
    {"type": "create_task", "content": "Review code", "status": "pending"},
    {"type": "create_memory", "content": "User prefers Python"},
    {"type": "create_goal", "content": "Code should be well-documented"},
    {"type": "datavault_store", "content": "...", "filetype": "py", "notes": "Implementation"}
  ]
}
```

## UI Changes

### Available Panels:
- ✅ **Chat** - Main conversational interface
- ✅ **Tasks** - View and manage tasks
- ✅ **Context** - Shows recent tasks and memories

### Removed Panels (will be redesigned):
- ❌ Notes
- ❌ Projects
- ❌ Vault

**TODO:** New panels for Memory, Goals, and Datavault will be added in future updates.

## Goal-Based Verification

The new system includes **Goals** that work with the verification LLM:

1. **Create Goals** during task execution:
   ```python
   gb.create_goal("Output should include detailed examples", notes="Quality check")
   ```

2. **Verification LLM** receives these goals and checks if the final output meets them

3. **Criteria scoring** includes "goals_met" (0-10)

4. **Output approved** only if all goals are satisfied

## Rollback (If Needed)

If something goes wrong:

1. **Find your backup**:
   ```bash
   ls ~/.gembrain/backups/
   ```

2. **Restore from backup**:
   ```bash
   cp ~/.gembrain/backups/gembrain_pre_migration_YYYYMMDD_HHMMSS.db ~/.gembrain/gembrain.db
   ```

3. **Restart GemBrain**

**Note:** Rollback will restore your old data but use the old schema. You'll need to revert code changes to use it.

## Troubleshooting

### "ImportError: cannot import name 'NoteService'"
- **Cause:** Code still trying to use old services
- **Fix:** Migration complete - restart the application

### "Table 'notes' doesn't exist"
- **Cause:** Code trying to access old tables
- **Fix:** Migration successful - old tables removed as expected

### Migration failed with error
- **Check:** Backup should still exist in `~/.gembrain/backups/`
- **Restore:** Copy backup back to `~/.gembrain/gembrain.db`
- **Report:** Create an issue with the error message

## Questions?

- **Why the breaking change?** The new structure better supports iterative reasoning workflows and goal-based verification
- **Can I migrate my old data?** Not automatically - data structures are fundamentally different
- **When will new UI panels be ready?** They're planned but not yet implemented

## Summary

✅ **Before Migration:**
- Backup your database manually if you want extra safety
- Understand that ALL DATA WILL BE LOST
- Read this guide completely

✅ **During Migration:**
- Choose UI or command-line option
- Confirm when prompted
- Wait for completion

✅ **After Migration:**
- Restart GemBrain
- Start using new data structures (Tasks, Memory, Goals, Datavault)
- Explore goal-based verification features
