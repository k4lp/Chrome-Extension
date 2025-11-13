# GemBrain Comprehensive Improvement Plan

**Generated:** 2025-11-13
**Status:** Awaiting User Approval
**Estimated Total Work:** 1500-2000 lines of code

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Critical Bug Fixes](#critical-bug-fixes)
3. [Major UI Restructuring](#major-ui-restructuring)
4. [Vault System Enhancement](#vault-system-enhancement)
5. [Tool Access Expansion](#tool-access-expansion)
6. [Memory System Accessibility](#memory-system-accessibility)
7. [Project CRUD Completion](#project-crud-completion)
8. [Automation System Exposure](#automation-system-exposure)
9. [UI Panel Creation](#ui-panel-creation)
10. [Enhanced Logging](#enhanced-logging)
11. [Implementation Roadmap](#implementation-roadmap)
12. [Testing Strategy](#testing-strategy)

---

## Executive Summary

This plan addresses **7 critical bugs**, **1 major UI restructuring**, and **multiple missing features** discovered through comprehensive codebase audit.

### Key Findings
- **Memory system** nearly inaccessible to both LLM and user
- **Vault system** missing update functionality and robust UI
- **Automation rules** completely hidden from user
- **Critical parsing bug** in iterative reasoner causing premature termination
- **UI lacks separation** between final output and technical details
- **Project and vault CRUD** operations incomplete

### Success Criteria
1. All database entities accessible via UI and LLM actions
2. Clear visual separation between user-facing output and technical logs
3. Real-time visibility into reasoning process and code execution
4. Zero critical bugs preventing normal operation
5. All CRUD operations complete for all entities

---

## Critical Bug Fixes

### BUG-001: Iteration Block Regex Parsing Failure ⚠️ CRITICAL

**Severity:** HIGH - Breaks iterative reasoning
**Impact:** Iterative reasoning terminates prematurely when JSON contains code blocks with backticks

**Current Code:**
```python
# File: gembrain/agents/iterative_reasoner.py:557
match = re.search(r"```iteration\s*\n(.*?)\n```", response, re.DOTALL)
```

**Problem:**
- Lazy match `(.*?)` stops at first `\n````, even if inside JSON string
- Example: When `"code": "```python\nprint('test')\n```"` appears in JSON
- Regex matches up to the code block's closing ``` instead of the iteration block's closing ```

**Evidence from Logs:**
```
2025-11-13 12:48:18 | ERROR | ❌ No ```iteration block found in response
2025-11-13 12:48:18 | ERROR | Response sample: ```iteration
{
  "iteration": 16,
  "current_subtask": 2,
  "reasoning": "...",
  "next_actions": [
    {
      "type": "execute_code",
      "code": "import json\n\ndef get_final_status():\n..."
```

**Solution:**
Replace regex with manual parsing that properly handles nested code blocks.

**Proposed Fix:**
```python
# File: gembrain/agents/iterative_reasoner.py:552-572

def _parse_iteration_response(self, response: str) -> Optional[Dict[str, Any]]:
    """Parse iteration response from model."""
    try:
        logger.debug("🔍 Searching for ```iteration block in response")

        # Find start of iteration block
        start_marker = "```iteration"
        start_idx = response.find(start_marker)

        if start_idx == -1:
            logger.error("❌ No ```iteration block found in response")
            logger.error(f"Response sample (first 1000 chars): {response[:1000]}")
            return None

        # Find the newline after the opening marker
        json_start = response.find("\n", start_idx) + 1

        # Find the closing marker by counting braces
        brace_count = 0
        in_string = False
        escape_next = False
        json_end = json_start

        for i in range(json_start, len(response)):
            char = response[i]

            # Handle escape sequences
            if escape_next:
                escape_next = False
                continue

            if char == '\\':
                escape_next = True
                continue

            # Handle strings
            if char == '"':
                in_string = not in_string
                continue

            # Only count braces outside strings
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        json_end = i + 1
                        break

        if brace_count != 0:
            logger.error(f"❌ Unbalanced braces in iteration JSON (count: {brace_count})")
            return None

        json_str = response[json_start:json_end]
        logger.debug(f"✅ Found ```iteration block (length: {len(json_str)} chars)")
        logger.debug(f"JSON string preview: {json_str[:200]}")

        parsed = json.loads(json_str)
        logger.debug(f"✅ Successfully parsed JSON with keys: {list(parsed.keys())}")
        return parsed

    except json.JSONDecodeError as e:
        logger.error(f"❌ Failed to parse iteration JSON: {e}")
        logger.error(f"JSON string that failed: {json_str[:500] if 'json_str' in locals() else 'N/A'}")
        return None
```

**Estimated Time:** 30 minutes
**Priority:** IMMEDIATE
**Files Modified:** 1 (`iterative_reasoner.py`)

---

### BUG-002: code_api.list_memories() Calls Non-Existent Method ⚠️ CRITICAL

**Severity:** HIGH - Crashes code execution
**Impact:** Any code using `gb.list_memories()` will crash with AttributeError

**Current Code:**
```python
# File: gembrain/agents/code_api.py:273
memories = self.memory_service.get_important_memories(importance_threshold)
```

**Problem:**
- MemoryService has no method `get_important_memories()`
- Correct method is `get_all_memories(min_importance=threshold)`

**Solution:**
```python
# File: gembrain/agents/code_api.py:273
memories = self.memory_service.get_all_memories(min_importance=importance_threshold)
```

**Estimated Time:** 5 minutes
**Priority:** IMMEDIATE
**Files Modified:** 1 (`code_api.py`)

---

## Major UI Restructuring

### FEATURE-001: Split-Screen Layout (Upper Output / Lower Technical Details)

**Requirement:**
> All reasoning logs, code execution details, and technical information should be shown in the LOWER half of the screen. Final output/chat should be displayed in the UPPER half.

**Current State:**
- Single chat panel shows everything mixed together
- No separation between user-facing output and technical details
- Logs only visible in terminal, not in UI

**Proposed Design:**

```
┌────────────────────────────────────────────────────────────────┐
│ GemBrain - Second Brain Assistant                              │
├────────────────────────────────────────────────────────────────┤
│ [Chat] [Notes] [Tasks] [Projects] [Vault] [Memory] [Settings] │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  UPPER HALF - CONVERSATION & FINAL OUTPUT                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 👤 You: Can you check if I have internet connectivity?  │  │
│  │                                                          │  │
│  │ 🤖 GemBrain: I'll test internet connectivity for you.  │  │
│  │                                                          │  │
│  │ ✅ Result: Your system has full internet connectivity. │  │
│  │ • Successfully connected to google.com                  │  │
│  │ • DNS resolution working                                │  │
│  │ • HTTP request completed in 234ms                       │  │
│  │                                                          │  │
│  │ [Input box for user messages]                           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  LOWER HALF - REASONING LOGS & CODE EXECUTION                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ [Reasoning] [Code Execution] [Actions] [All Logs]       │  │
│  │ ─────────────────────────────────────────────────────────│  │
│  │ 🔄 Iteration 1/50                                        │  │
│  │   Reasoning: Breaking down connectivity test...         │  │
│  │   Observations: Need to test DNS, HTTP, HTTPS          │  │
│  │   Actions: execute_code (test_connectivity.py)         │  │
│  │                                                          │  │
│  │ 💻 Code Execution #1234 (234ms) ✓ SUCCESS              │  │
│  │   Code:                                                 │  │
│  │   import requests                                       │  │
│  │   response = requests.get('https://google.com')        │  │
│  │   print(f"Status: {response.status_code}")             │  │
│  │                                                          │  │
│  │   Output:                                               │  │
│  │   Status: 200                                           │  │
│  │                                                          │  │
│  │   Result: {'status': 200, 'time_ms': 234}              │  │
│  │                                                          │  │
│  │ 🔄 Iteration 2/50                                        │  │
│  │   is_final: true                                        │  │
│  │   Completion: All tests passed                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

**Layout Specifications:**

1. **Screen Division:**
   - Upper half: 55% of vertical space (conversation priority)
   - Lower half: 45% of vertical space (technical details)
   - Resizable splitter between halves (QSplitter)
   - Minimum height: 200px for each half

2. **Upper Half Components:**
   - **Conversation View** (scrollable)
     - User messages (blue, left-aligned)
     - Agent messages (green, left-aligned)
     - System messages (gray, italic)
     - Final outputs highlighted with box/background
   - **Input Area** (fixed at bottom)
     - Text input box (expandable, max 100px)
     - Send button
     - Auto-apply checkbox
     - Character count

3. **Lower Half Components:**
   - **Tab Widget** with 4 tabs:
     - **Reasoning Tab:** Iteration logs, observations, insights
     - **Code Execution Tab:** All code runs with outputs
     - **Actions Tab:** All action executions with results
     - **All Logs Tab:** Raw log stream (advanced)
   - **Auto-scroll toggle** (enable/disable)
   - **Clear logs button**
   - **Export logs button**
   - **Filter controls** (by log level, type)

**Implementation Details:**

**File: gembrain/ui/widgets/chat_panel.py** (MAJOR REFACTOR)

```python
# New structure:

class ConversationView(QWidget):
    """Upper half - User-facing conversation and final outputs."""

    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Conversation history (scrollable)
        self.conversation = QTextEdit()
        self.conversation.setReadOnly(True)
        layout.addWidget(self.conversation, stretch=1)

        # Input area
        input_frame = QFrame()
        input_layout = QVBoxLayout(input_frame)

        self.input_box = QTextEdit()
        self.input_box.setMaximumHeight(100)
        input_layout.addWidget(self.input_box)

        button_row = QHBoxLayout()
        self.auto_apply = QCheckBox("Auto-apply actions")
        self.send_btn = QPushButton("Send")
        button_row.addWidget(self.auto_apply)
        button_row.addStretch()
        button_row.addWidget(self.send_btn)
        input_layout.addLayout(button_row)

        layout.addWidget(input_frame)

    def append_user_message(self, text: str):
        """Add user message to conversation."""
        self.conversation.append(
            f"<div style='margin: 8px 0;'>"
            f"<b style='color: #0066cc;'>👤 You:</b> {text}"
            f"</div>"
        )

    def append_agent_message(self, text: str):
        """Add agent final output to conversation."""
        self.conversation.append(
            f"<div style='margin: 8px 0;'>"
            f"<b style='color: #00aa00;'>🤖 GemBrain:</b> {text}"
            f"</div>"
        )

    def append_final_output(self, text: str):
        """Add highlighted final output box."""
        self.conversation.append(
            f"<div style='background: #f0f8ff; border: 2px solid #4a90e2; "
            f"border-radius: 8px; padding: 12px; margin: 12px 0;'>"
            f"<b style='color: #2c5aa0;'>✅ Final Result:</b><br/>"
            f"{text}"
            f"</div>"
        )


class TechnicalDetailsView(QWidget):
    """Lower half - Reasoning logs, code execution, actions."""

    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Tab widget for different log types
        self.tabs = QTabWidget()

        # Reasoning tab
        self.reasoning_view = QTextEdit()
        self.reasoning_view.setReadOnly(True)
        self.reasoning_view.setStyleSheet("font-family: 'Courier New', monospace;")
        self.tabs.addTab(self.reasoning_view, "🧠 Reasoning")

        # Code execution tab
        self.code_view = QTextEdit()
        self.code_view.setReadOnly(True)
        self.code_view.setStyleSheet("font-family: 'Courier New', monospace;")
        self.tabs.addTab(self.code_view, "💻 Code Execution")

        # Actions tab
        self.actions_view = QTextEdit()
        self.actions_view.setReadOnly(True)
        self.actions_view.setStyleSheet("font-family: 'Courier New', monospace;")
        self.tabs.addTab(self.actions_view, "🎬 Actions")

        # All logs tab
        self.logs_view = QTextEdit()
        self.logs_view.setReadOnly(True)
        self.logs_view.setStyleSheet("font-family: 'Courier New', monospace; font-size: 10pt;")
        self.tabs.addTab(self.logs_view, "📋 All Logs")

        layout.addWidget(self.tabs)

        # Controls row
        controls = QHBoxLayout()
        self.auto_scroll = QCheckBox("Auto-scroll")
        self.auto_scroll.setChecked(True)
        self.clear_btn = QPushButton("Clear")
        self.export_btn = QPushButton("Export")

        controls.addWidget(self.auto_scroll)
        controls.addStretch()
        controls.addWidget(self.clear_btn)
        controls.addWidget(self.export_btn)

        layout.addLayout(controls)

    def append_iteration(self, iteration_num: int, max_iterations: int,
                         reasoning: str, observations: list, actions: list,
                         is_final: bool):
        """Add iteration details to reasoning view."""
        html = f"<div style='border-left: 3px solid #4a90e2; padding-left: 8px; margin: 8px 0;'>"
        html += f"<b style='color: #2c5aa0;'>🔄 Iteration {iteration_num}/{max_iterations}</b><br/>"
        html += f"<b>Reasoning:</b> {reasoning[:200]}...<br/>"

        if observations:
            html += f"<b>Observations:</b><ul>"
            for obs in observations[:3]:
                html += f"<li>{obs}</li>"
            html += "</ul>"

        if actions:
            html += f"<b>Actions:</b> {len(actions)} to execute<br/>"

        html += f"<b>is_final:</b> {is_final}<br/>"
        html += "</div>"

        self.reasoning_view.append(html)
        if self.auto_scroll.isChecked():
            self.reasoning_view.moveCursor(QTextCursor.MoveOperation.End)

    def append_code_execution(self, execution_id: str, code: str,
                             stdout: str, stderr: str, result: any,
                             success: bool, execution_time: float):
        """Add code execution details."""
        color = "#00aa00" if success else "#cc0000"
        icon = "✓" if success else "✗"

        html = f"<div style='background: #f5f5f5; border-left: 4px solid {color}; "
        html += f"padding: 8px; margin: 8px 0; font-family: monospace;'>"
        html += f"<b style='color: {color};'>{icon} Execution #{execution_id} ({execution_time:.3f}s)</b><br/>"
        html += f"<details><summary>Code</summary><pre>{code}</pre></details>"

        if stdout:
            html += f"<b>Output:</b><pre>{stdout}</pre>"
        if stderr:
            html += f"<b style='color: #cc6600;'>Warnings:</b><pre>{stderr}</pre>"
        if result:
            html += f"<b>Result:</b> <code>{result}</code>"

        html += "</div>"

        self.code_view.append(html)
        if self.auto_scroll.isChecked():
            self.code_view.moveCursor(QTextCursor.MoveOperation.End)

    def append_action(self, action_type: str, params: dict,
                     success: bool, message: str, execution_time: float):
        """Add action execution details."""
        color = "#00aa00" if success else "#cc0000"
        icon = "✓" if success else "✗"

        html = f"<div style='margin: 4px 0;'>"
        html += f"<b style='color: {color};'>{icon} {action_type}</b> "
        html += f"({execution_time:.3f}s): {message}<br/>"
        html += f"<small>Params: {params}</small>"
        html += "</div>"

        self.actions_view.append(html)
        if self.auto_scroll.isChecked():
            self.actions_view.moveCursor(QTextCursor.MoveOperation.End)

    def append_log(self, log_line: str):
        """Add raw log line to all logs tab."""
        self.logs_view.append(log_line)
        if self.auto_scroll.isChecked():
            self.logs_view.moveCursor(QTextCursor.MoveOperation.End)


class ChatPanel(QWidget):
    """Refactored chat panel with split view."""

    def __init__(self, db_session, orchestrator, settings):
        super().__init__()
        self.db_session = db_session
        self.orchestrator = orchestrator
        self.settings = settings
        self.worker = None

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Create splitter for upper/lower halves
        self.splitter = QSplitter(Qt.Orientation.Vertical)

        # Upper half - Conversation
        self.conversation_view = ConversationView()
        self.splitter.addWidget(self.conversation_view)

        # Lower half - Technical details
        self.technical_view = TechnicalDetailsView()
        self.splitter.addWidget(self.technical_view)

        # Set initial sizes (55% upper, 45% lower)
        self.splitter.setStretchFactor(0, 55)
        self.splitter.setStretchFactor(1, 45)

        layout.addWidget(self.splitter)

        # Connect signals
        self.conversation_view.send_btn.clicked.connect(self._send_message)
        self.technical_view.clear_btn.clicked.connect(self._clear_technical_logs)
        self.technical_view.export_btn.clicked.connect(self._export_logs)

    def _send_message(self):
        """Send message via worker thread (existing logic)."""
        # ... existing worker thread code ...
        pass

    def _on_progress_update(self, progress_data: dict):
        """Handle progress update from worker thread.

        progress_data = {
            'type': 'iteration' | 'code_execution' | 'action',
            'data': {...}
        }
        """
        if progress_data['type'] == 'iteration':
            self.technical_view.append_iteration(**progress_data['data'])
        elif progress_data['type'] == 'code_execution':
            self.technical_view.append_code_execution(**progress_data['data'])
        elif progress_data['type'] == 'action':
            self.technical_view.append_action(**progress_data['data'])

    def _on_response_ready(self, response: OrchestratorResponse):
        """Handle final response."""
        # Show final output in upper half
        self.conversation_view.append_final_output(response.reply_text)

        # Re-enable UI
        self._freeze_ui(False)
```

**Changes to OrchestratorWorker:**

Need to emit structured progress data instead of just strings:

```python
class OrchestratorWorker(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    progress = pyqtSignal(dict)  # Changed from str to dict

    def run(self):
        def on_progress(progress_type: str, data: dict):
            """Enhanced progress callback."""
            self.progress.emit({
                'type': progress_type,
                'data': data
            })

        response = self.orchestrator.run_user_message(
            user_message=self.user_message,
            ui_context=self.ui_context,
            auto_apply_actions=self.auto_apply,
            progress_callback=on_progress,
        )

        self.finished.emit(response)
```

**Changes to IterativeReasoner:**

Need to call progress callback with detailed data:

```python
# File: gembrain/agents/iterative_reasoner.py:400-420

# After creating iteration object
if progress_callback:
    progress_callback('iteration', {
        'iteration_num': iteration_count,
        'max_iterations': self.max_iterations,
        'reasoning': iteration.reasoning,
        'observations': iteration.observations,
        'actions': iteration.actions_taken,
        'is_final': is_final,
    })
```

**Changes to ActionExecutor:**

Need to accept and call progress callback:

```python
# File: gembrain/agents/tools.py:235-340

def execute_action(
    self,
    action: Dict[str, Any],
    progress_callback: Optional[callable] = None,
) -> ActionResult:
    # ... existing execution logic ...

    # After execution
    if progress_callback:
        progress_callback('action', {
            'action_type': action_type,
            'params': action_params,
            'success': result.success,
            'message': result.message,
            'execution_time': elapsed,
        })

    return result
```

**Changes to CodeExecutor:**

Need to accept and call progress callback:

```python
# File: gembrain/agents/code_executor.py:36-107

def execute(
    self,
    code: str,
    timeout: Optional[float] = None,
    progress_callback: Optional[callable] = None,
) -> Dict[str, Any]:
    # ... existing execution logic ...

    # After execution
    if progress_callback:
        progress_callback('code_execution', {
            'execution_id': execution_id,
            'code': code,
            'stdout': stdout_capture.getvalue(),
            'stderr': stderr_capture.getvalue(),
            'result': str(result) if result else None,
            'success': success,
            'execution_time': elapsed,
        })

    return result_dict
```

**Estimated Time:** 8-10 hours
**Priority:** HIGH
**Files Modified:** 6
**Files Created:** 0
**Lines Changed:** ~500 lines

**Testing Checklist:**
- [ ] Upper/lower split renders correctly
- [ ] Splitter is resizable and remembers position
- [ ] Conversation view shows only final outputs
- [ ] Technical view shows all iterations in real-time
- [ ] Code executions appear in code tab
- [ ] Actions appear in actions tab
- [ ] All logs tab shows everything
- [ ] Auto-scroll works correctly
- [ ] Clear button clears technical logs
- [ ] Export button exports logs to file
- [ ] UI remains responsive during iterative reasoning

---

## Vault System Enhancement

### FEATURE-002: Complete Vault CRUD Operations

**Current Gaps:**
- ✗ No update method in repository
- ✗ No update method in service
- ✗ No update/delete action handlers
- ✗ No list_vault_items action
- ✗ UI cannot edit vault items

**Changes Required:**

#### 1. Add VaultItemRepository.update()

**File:** `gembrain/core/repository.py`
**Location:** After line 409 (after `search()` method)

```python
@staticmethod
def update(db: Session, item_id: int, **kwargs) -> Optional[VaultItem]:
    """Update vault item fields.

    Args:
        db: Database session
        item_id: Vault item ID
        **kwargs: Fields to update (title, type, path_or_url, item_metadata)

    Returns:
        Updated VaultItem or None if not found
    """
    item = VaultItemRepository.get_by_id(db, item_id)
    if not item:
        return None

    for key, value in kwargs.items():
        if hasattr(item, key):
            setattr(item, key, value)

    db.commit()
    db.refresh(item)
    return item
```

**Estimated Time:** 15 minutes

#### 2. Add VaultService.update_item()

**File:** `gembrain/core/services.py`
**Location:** After line 295 (after `search_items()` method)

```python
def update_item(self, item_id: int, **kwargs) -> Optional[VaultItem]:
    """Update vault item.

    Args:
        item_id: Vault item ID
        **kwargs: Fields to update

    Returns:
        Updated VaultItem or None if not found
    """
    # Handle metadata as dict and convert to JSON
    if 'metadata' in kwargs:
        import json
        kwargs['item_metadata'] = json.dumps(kwargs.pop('metadata'))

    item = VaultItemRepository.update(self.db, item_id, **kwargs)
    if item:
        logger.info(f"Updated vault item: {item.title}")
    return item
```

**Estimated Time:** 15 minutes

#### 3. Add Action Handlers

**File:** `gembrain/agents/tools.py`
**Location:** After line 899 (after existing vault handlers)

```python
def _update_vault_item(self, action: Dict[str, Any]) -> ActionResult:
    """Update a vault item.

    Args:
        action: {
            'type': 'update_vault_item',
            'item_id': int,
            'title': str (optional),
            'vault_type': str (optional),
            'path_or_url': str (optional),
            'metadata': dict (optional)
        }
    """
    item_id = action.get('item_id')
    if not item_id:
        return ActionResult(
            action_type='update_vault_item',
            success=False,
            message='item_id is required'
        )

    # Build update kwargs
    update_fields = {}
    if 'title' in action:
        update_fields['title'] = action['title']
    if 'vault_type' in action:
        try:
            from ..core.models import VaultItemType
            update_fields['type'] = VaultItemType[action['vault_type'].upper()]
        except KeyError:
            return ActionResult(
                action_type='update_vault_item',
                success=False,
                message=f"Invalid vault_type: {action['vault_type']}"
            )
    if 'path_or_url' in action:
        update_fields['path_or_url'] = action['path_or_url']
    if 'metadata' in action:
        update_fields['metadata'] = action['metadata']

    item = self.vault_service.update_item(item_id, **update_fields)

    if item:
        return ActionResult(
            action_type='update_vault_item',
            success=True,
            message=f"Updated vault item: {item.title}",
            data={'item_id': item.id, 'title': item.title}
        )
    else:
        return ActionResult(
            action_type='update_vault_item',
            success=False,
            message=f"Vault item {item_id} not found"
        )


def _delete_vault_item(self, action: Dict[str, Any]) -> ActionResult:
    """Delete a vault item.

    Args:
        action: {'type': 'delete_vault_item', 'item_id': int}
    """
    item_id = action.get('item_id')
    if not item_id:
        return ActionResult(
            action_type='delete_vault_item',
            success=False,
            message='item_id is required'
        )

    # Get item details before deleting
    item = self.vault_service.get_item(item_id)
    if not item:
        return ActionResult(
            action_type='delete_vault_item',
            success=False,
            message=f"Vault item {item_id} not found"
        )

    title = item.title
    success = self.vault_service.delete_item(item_id)

    if success:
        return ActionResult(
            action_type='delete_vault_item',
            success=True,
            message=f"Deleted vault item: {title}"
        )
    else:
        return ActionResult(
            action_type='delete_vault_item',
            success=False,
            message=f"Failed to delete vault item {item_id}"
        )


def _list_vault_items(self, action: Dict[str, Any]) -> ActionResult:
    """List all vault items.

    Args:
        action: {
            'type': 'list_vault_items',
            'vault_type': str (optional) - filter by type
        }
    """
    vault_type = None
    if 'vault_type' in action:
        try:
            from ..core.models import VaultItemType
            vault_type = VaultItemType[action['vault_type'].upper()]
        except KeyError:
            return ActionResult(
                action_type='list_vault_items',
                success=False,
                message=f"Invalid vault_type: {action['vault_type']}"
            )

    items = self.vault_service.get_all_items(type=vault_type)

    items_data = [
        {
            'id': item.id,
            'title': item.title,
            'type': item.type.value,
            'path_or_url': item.path_or_url,
            'created_at': item.created_at.isoformat() if item.created_at else None,
        }
        for item in items
    ]

    return ActionResult(
        action_type='list_vault_items',
        success=True,
        message=f"Found {len(items)} vault items",
        data={'items': items_data, 'count': len(items)}
    )
```

**Also update action handlers dict (line ~280):**
```python
'update_vault_item': self._update_vault_item,
'delete_vault_item': self._delete_vault_item,
'list_vault_items': self._list_vault_items,
```

**Estimated Time:** 1 hour

#### 4. Update code_api.py

**File:** `gembrain/agents/code_api.py`
**Location:** After line 364 (after existing vault methods)

```python
def update_vault_item(self, item_id: int, **kwargs) -> bool:
    """Update a vault item.

    Args:
        item_id: Item ID
        **kwargs: Fields to update (title, type, path_or_url, metadata)

    Returns:
        True if updated, False if not found

    Example:
        gb.update_vault_item(123, title="New Title", metadata={"version": 2})
    """
    item = self.vault_service.update_item(item_id, **kwargs)
    return item is not None


def list_vault_items(self, vault_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all vault items.

    Args:
        vault_type: Optional type filter ("file", "url", "snippet", "other")

    Returns:
        List of vault item dictionaries

    Example:
        snippets = gb.list_vault_items(vault_type="snippet")
    """
    from ..core.models import VaultItemType

    type_filter = None
    if vault_type:
        try:
            type_filter = VaultItemType[vault_type.upper()]
        except KeyError:
            self.log(f"Invalid vault_type: {vault_type}")
            return []

    items = self.vault_service.get_all_items(type=type_filter)

    return [
        {
            'id': item.id,
            'title': item.title,
            'type': item.type.value,
            'path_or_url': item.path_or_url,
            'metadata': json.loads(item.item_metadata) if item.item_metadata else {},
            'created_at': item.created_at.isoformat() if item.created_at else None,
        }
        for item in items
    ]
```

**Estimated Time:** 30 minutes

#### 5. Enhance Vault UI Panel

**File:** `gembrain/ui/widgets/vault_panel.py`
**Complete rewrite required**

```python
"""Enhanced vault panel with full CRUD operations."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QLineEdit, QTextEdit, QComboBox, QDialog,
    QDialogButtonBox, QFormLayout, QMessageBox, QSplitter, QGroupBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from loguru import logger
import json

from ...core.models import VaultItemType


class VaultItemDialog(QDialog):
    """Dialog for creating/editing vault items."""

    def __init__(self, parent=None, item=None):
        super().__init__(parent)
        self.item = item
        self.setWindowTitle("Edit Vault Item" if item else "New Vault Item")
        self.setMinimumWidth(500)
        self.setup_ui()

        if item:
            self.load_item()

    def setup_ui(self):
        layout = QFormLayout(self)

        # Title
        self.title_edit = QLineEdit()
        layout.addRow("Title:", self.title_edit)

        # Type
        self.type_combo = QComboBox()
        self.type_combo.addItems([t.value for t in VaultItemType])
        layout.addRow("Type:", self.type_combo)

        # Path/URL
        self.path_edit = QLineEdit()
        layout.addRow("Path/URL:", self.path_edit)

        # Metadata (JSON)
        self.metadata_label = QLabel("Metadata (JSON):")
        self.metadata_edit = QTextEdit()
        self.metadata_edit.setMaximumHeight(150)
        self.metadata_edit.setPlaceholderText('{\n  "key": "value"\n}')
        layout.addRow(self.metadata_label, self.metadata_edit)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def load_item(self):
        """Load item data into form."""
        self.title_edit.setText(self.item.title)
        self.type_combo.setCurrentText(self.item.type.value)
        self.path_edit.setText(self.item.path_or_url or "")

        # Load metadata
        if self.item.item_metadata:
            try:
                metadata = json.loads(self.item.item_metadata)
                self.metadata_edit.setPlainText(json.dumps(metadata, indent=2))
            except json.JSONDecodeError:
                self.metadata_edit.setPlainText(self.item.item_metadata)

    def validate_and_accept(self):
        """Validate form and accept dialog."""
        if not self.title_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "Title is required")
            return

        # Validate metadata JSON
        metadata_text = self.metadata_edit.toPlainText().strip()
        if metadata_text:
            try:
                json.loads(metadata_text)
            except json.JSONDecodeError as e:
                QMessageBox.warning(
                    self, "Invalid JSON",
                    f"Metadata must be valid JSON:\n{str(e)}"
                )
                return

        self.accept()

    def get_data(self):
        """Get form data as dict."""
        metadata_text = self.metadata_edit.toPlainText().strip()
        metadata = json.loads(metadata_text) if metadata_text else {}

        return {
            'title': self.title_edit.text().strip(),
            'type': VaultItemType[self.type_combo.currentText().upper()],
            'path_or_url': self.path_edit.text().strip(),
            'metadata': metadata,
        }


class VaultPanel(QWidget):
    """Enhanced vault panel with CRUD operations."""

    def __init__(self, db_session, vault_service):
        super().__init__()
        self.db_session = db_session
        self.vault_service = vault_service
        self.current_item = None

        self.setup_ui()
        self.refresh()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        # Title and controls
        header = QHBoxLayout()
        title = QLabel("Vault")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        header.addWidget(title)

        # Type filter
        self.type_filter = QComboBox()
        self.type_filter.addItem("All Types", None)
        for vtype in VaultItemType:
            self.type_filter.addItem(vtype.value.title(), vtype)
        self.type_filter.currentIndexChanged.connect(self.refresh)
        header.addWidget(QLabel("Filter:"))
        header.addWidget(self.type_filter)

        # Search
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search vault...")
        self.search_box.textChanged.connect(self.refresh)
        header.addWidget(self.search_box)

        # Refresh button
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.clicked.connect(self.refresh)
        header.addWidget(self.refresh_btn)

        # New item button
        new_btn = QPushButton("➕ New Item")
        new_btn.clicked.connect(self.create_item)
        header.addWidget(new_btn)

        layout.addLayout(header)

        # Splitter for list and detail
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Item list
        self.item_list = QListWidget()
        self.item_list.itemSelectionChanged.connect(self.on_selection_changed)
        self.item_list.itemDoubleClicked.connect(self.edit_item)
        splitter.addWidget(self.item_list)

        # Right: Detail view
        detail_widget = QWidget()
        detail_layout = QVBoxLayout(detail_widget)

        detail_title = QLabel("Item Details")
        detail_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        detail_layout.addWidget(detail_title)

        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        detail_layout.addWidget(self.detail_text)

        # Action buttons
        button_row = QHBoxLayout()
        self.edit_btn = QPushButton("✏️ Edit")
        self.edit_btn.clicked.connect(self.edit_item)
        self.edit_btn.setEnabled(False)

        self.delete_btn = QPushButton("🗑️ Delete")
        self.delete_btn.clicked.connect(self.delete_item)
        self.delete_btn.setEnabled(False)

        self.open_btn = QPushButton("🔗 Open")
        self.open_btn.clicked.connect(self.open_item)
        self.open_btn.setEnabled(False)

        button_row.addWidget(self.edit_btn)
        button_row.addWidget(self.delete_btn)
        button_row.addWidget(self.open_btn)
        button_row.addStretch()

        detail_layout.addLayout(button_row)
        splitter.addWidget(detail_widget)

        # Set splitter sizes (60% list, 40% detail)
        splitter.setStretchFactor(0, 60)
        splitter.setStretchFactor(1, 40)

        layout.addWidget(splitter)

    def refresh(self):
        """Refresh item list."""
        self.item_list.clear()

        # Get filter type
        filter_type = self.type_filter.currentData()

        # Get search query
        search_query = self.search_box.text().strip()

        # Fetch items
        if search_query:
            items = self.vault_service.search_items(search_query)
            if filter_type:
                items = [i for i in items if i.type == filter_type]
        else:
            items = self.vault_service.get_all_items(type=filter_type)

        # Populate list
        for item in items:
            icon = self._get_icon_for_type(item.type)
            list_item = QListWidgetItem(f"{icon} {item.title}")
            list_item.setData(Qt.ItemDataRole.UserRole, item)
            self.item_list.addItem(list_item)

    def on_selection_changed(self):
        """Handle item selection."""
        selected = self.item_list.selectedItems()
        if selected:
            self.current_item = selected[0].data(Qt.ItemDataRole.UserRole)
            self.show_detail(self.current_item)
            self.edit_btn.setEnabled(True)
            self.delete_btn.setEnabled(True)
            self.open_btn.setEnabled(True)
        else:
            self.current_item = None
            self.detail_text.clear()
            self.edit_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)
            self.open_btn.setEnabled(False)

    def show_detail(self, item):
        """Show item details."""
        try:
            metadata = json.loads(item.item_metadata) if item.item_metadata else {}
            metadata_str = json.dumps(metadata, indent=2)
        except:
            metadata_str = item.item_metadata or "{}"

        html = f"""
        <div style='padding: 8px;'>
            <p><b>Title:</b> {item.title}</p>
            <p><b>Type:</b> {item.type.value}</p>
            <p><b>Path/URL:</b> {item.path_or_url or 'N/A'}</p>
            <p><b>Created:</b> {item.created_at.strftime('%Y-%m-%d %H:%M') if item.created_at else 'N/A'}</p>
            <p><b>Metadata:</b></p>
            <pre style='background: #f5f5f5; padding: 8px; border-radius: 4px;'>{metadata_str}</pre>
        </div>
        """
        self.detail_text.setHtml(html)

    def create_item(self):
        """Create new vault item."""
        dialog = VaultItemDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            try:
                self.vault_service.add_item(
                    title=data['title'],
                    type=data['type'],
                    path_or_url=data['path_or_url'],
                    metadata=data['metadata'],
                )
                self.refresh()
                logger.info(f"Created vault item: {data['title']}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create item: {str(e)}")

    def edit_item(self):
        """Edit selected vault item."""
        if not self.current_item:
            return

        dialog = VaultItemDialog(self, self.current_item)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            try:
                self.vault_service.update_item(
                    item_id=self.current_item.id,
                    title=data['title'],
                    type=data['type'],
                    path_or_url=data['path_or_url'],
                    metadata=data['metadata'],
                )
                self.refresh()
                logger.info(f"Updated vault item: {data['title']}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to update item: {str(e)}")

    def delete_item(self):
        """Delete selected vault item."""
        if not self.current_item:
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete '{self.current_item.title}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.vault_service.delete_item(self.current_item.id)
                self.refresh()
                logger.info(f"Deleted vault item: {self.current_item.title}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete item: {str(e)}")

    def open_item(self):
        """Open vault item (URL or file)."""
        if not self.current_item or not self.current_item.path_or_url:
            return

        import webbrowser
        import os

        path = self.current_item.path_or_url

        if path.startswith(('http://', 'https://')):
            webbrowser.open(path)
        elif os.path.exists(path):
            os.startfile(path) if os.name == 'nt' else os.system(f'open "{path}"')
        else:
            QMessageBox.warning(self, "Cannot Open", f"Path does not exist: {path}")

    def _get_icon_for_type(self, vtype: VaultItemType) -> str:
        """Get emoji icon for vault type."""
        icons = {
            VaultItemType.FILE: "📄",
            VaultItemType.URL: "🔗",
            VaultItemType.SNIPPET: "📋",
            VaultItemType.OTHER: "📦",
        }
        return icons.get(vtype, "📦")
```

**Estimated Time:** 3 hours

**Total for FEATURE-002:** ~5 hours

---

## Memory System Accessibility

### FEATURE-003: Expose Memory Operations

**Current Gaps:**
- ✗ No list_memories action
- ✗ No get_memory action
- ✗ No delete_memory action
- ✗ No Memory UI panel
- ✗ BUG: code_api.list_memories() broken

**Changes Required:**

#### 1. Fix code_api.list_memories() Bug

**File:** `gembrain/agents/code_api.py`
**Location:** Line 273

```python
# BEFORE (BROKEN):
memories = self.memory_service.get_important_memories(importance_threshold)

# AFTER (FIXED):
memories = self.memory_service.get_all_memories(min_importance=importance_threshold)
```

**Estimated Time:** 2 minutes

#### 2. Add Memory Action Handlers

**File:** `gembrain/agents/tools.py`
**Location:** After line 899

```python
def _list_memories(self, action: Dict[str, Any]) -> ActionResult:
    """List all memories.

    Args:
        action: {
            'type': 'list_memories',
            'min_importance': int (optional, default 1)
        }
    """
    min_importance = action.get('min_importance', 1)
    memories = self.memory_service.get_all_memories(min_importance=min_importance)

    memories_data = [
        {
            'key': mem.key,
            'content': mem.content[:200] + '...' if len(mem.content) > 200 else mem.content,
            'importance': mem.importance,
            'updated_at': mem.updated_at.isoformat() if mem.updated_at else None,
        }
        for mem in memories
    ]

    return ActionResult(
        action_type='list_memories',
        success=True,
        message=f"Found {len(memories)} memories (importance >= {min_importance})",
        data={'memories': memories_data, 'count': len(memories)}
    )


def _get_memory(self, action: Dict[str, Any]) -> ActionResult:
    """Get a specific memory by key.

    Args:
        action: {'type': 'get_memory', 'key': str}
    """
    key = action.get('key')
    if not key:
        return ActionResult(
            action_type='get_memory',
            success=False,
            message='key is required'
        )

    memory = self.memory_service.get_memory(key)

    if memory:
        return ActionResult(
            action_type='get_memory',
            success=True,
            message=f"Retrieved memory: {key}",
            data={
                'key': memory.key,
                'content': memory.content,
                'importance': memory.importance,
                'updated_at': memory.updated_at.isoformat() if memory.updated_at else None,
            }
        )
    else:
        return ActionResult(
            action_type='get_memory',
            success=False,
            message=f"Memory not found: {key}"
        )


def _delete_memory(self, action: Dict[str, Any]) -> ActionResult:
    """Delete a memory.

    Args:
        action: {'type': 'delete_memory', 'key': str}
    """
    key = action.get('key')
    if not key:
        return ActionResult(
            action_type='delete_memory',
            success=False,
            message='key is required'
        )

    success = self.memory_service.delete_memory(key)

    if success:
        return ActionResult(
            action_type='delete_memory',
            success=True,
            message=f"Deleted memory: {key}"
        )
    else:
        return ActionResult(
            action_type='delete_memory',
            success=False,
            message=f"Memory not found: {key}"
        )
```

**Also update action handlers dict (~line 280):**
```python
'list_memories': self._list_memories,
'get_memory': self._get_memory,
'delete_memory': self._delete_memory,
```

**Estimated Time:** 45 minutes

#### 3. Add code_api Methods

**File:** `gembrain/agents/code_api.py`
**Location:** After line 282

```python
def delete_memory(self, key: str) -> bool:
    """Delete a memory.

    Args:
        key: Memory key

    Returns:
        True if deleted, False if not found

    Example:
        gb.delete_memory("user_preferences_old")
    """
    return self.memory_service.delete_memory(key)
```

**Estimated Time:** 10 minutes

#### 4. Create Memory UI Panel

**File:** `gembrain/ui/widgets/memory_panel.py` (NEW FILE)

```python
"""Memory panel for viewing and managing long-term memories."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QLineEdit, QTextEdit, QSpinBox, QDialog,
    QDialogButtonBox, QFormLayout, QMessageBox, QSplitter,
)
from PyQt6.QtCore import Qt
from loguru import logger

from ...core.models import Memory


class MemoryDialog(QDialog):
    """Dialog for creating/editing memories."""

    def __init__(self, parent=None, memory=None):
        super().__init__(parent)
        self.memory = memory
        self.setWindowTitle("Edit Memory" if memory else "New Memory")
        self.setMinimumWidth(500)
        self.setup_ui()

        if memory:
            self.load_memory()

    def setup_ui(self):
        layout = QFormLayout(self)

        # Key
        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("e.g., user_name, preferred_language")
        if self.memory:
            self.key_edit.setReadOnly(True)  # Can't change key
        layout.addRow("Key:", self.key_edit)

        # Content
        self.content_edit = QTextEdit()
        self.content_edit.setPlaceholderText("Memory content...")
        self.content_edit.setMinimumHeight(150)
        layout.addRow("Content:", self.content_edit)

        # Importance
        self.importance_spin = QSpinBox()
        self.importance_spin.setRange(1, 10)
        self.importance_spin.setValue(3)
        layout.addRow("Importance (1-10):", self.importance_spin)

        # Info label
        info = QLabel("Higher importance = higher priority in context retrieval")
        info.setStyleSheet("color: #666; font-style: italic; font-size: 10pt;")
        layout.addRow("", info)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def load_memory(self):
        """Load memory data into form."""
        self.key_edit.setText(self.memory.key)
        self.content_edit.setPlainText(self.memory.content)
        self.importance_spin.setValue(self.memory.importance)

    def validate_and_accept(self):
        """Validate form and accept."""
        if not self.key_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "Key is required")
            return
        if not self.content_edit.toPlainText().strip():
            QMessageBox.warning(self, "Validation Error", "Content is required")
            return
        self.accept()

    def get_data(self):
        """Get form data as dict."""
        return {
            'key': self.key_edit.text().strip(),
            'content': self.content_edit.toPlainText().strip(),
            'importance': self.importance_spin.value(),
        }


class MemoryPanel(QWidget):
    """Panel for managing long-term memories."""

    def __init__(self, db_session, memory_service):
        super().__init__()
        self.db_session = db_session
        self.memory_service = memory_service
        self.current_memory = None

        self.setup_ui()
        self.refresh()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        # Title and controls
        header = QHBoxLayout()
        title = QLabel("Memory")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        header.addWidget(title)

        # Importance filter
        header.addWidget(QLabel("Min Importance:"))
        self.importance_filter = QSpinBox()
        self.importance_filter.setRange(1, 10)
        self.importance_filter.setValue(1)
        self.importance_filter.valueChanged.connect(self.refresh)
        header.addWidget(self.importance_filter)

        header.addStretch()

        # Refresh button
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.clicked.connect(self.refresh)
        header.addWidget(self.refresh_btn)

        # New memory button
        new_btn = QPushButton("➕ New Memory")
        new_btn.clicked.connect(self.create_memory)
        header.addWidget(new_btn)

        layout.addLayout(header)

        # Splitter for list and detail
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Memory list
        self.memory_list = QListWidget()
        self.memory_list.itemSelectionChanged.connect(self.on_selection_changed)
        self.memory_list.itemDoubleClicked.connect(self.edit_memory)
        splitter.addWidget(self.memory_list)

        # Right: Detail view
        detail_widget = QWidget()
        detail_layout = QVBoxLayout(detail_widget)

        detail_title = QLabel("Memory Details")
        detail_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        detail_layout.addWidget(detail_title)

        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        detail_layout.addWidget(self.detail_text)

        # Action buttons
        button_row = QHBoxLayout()
        self.edit_btn = QPushButton("✏️ Edit")
        self.edit_btn.clicked.connect(self.edit_memory)
        self.edit_btn.setEnabled(False)

        self.delete_btn = QPushButton("🗑️ Delete")
        self.delete_btn.clicked.connect(self.delete_memory)
        self.delete_btn.setEnabled(False)

        button_row.addWidget(self.edit_btn)
        button_row.addWidget(self.delete_btn)
        button_row.addStretch()

        detail_layout.addLayout(button_row)
        splitter.addWidget(detail_widget)

        # Set splitter sizes (50/50)
        splitter.setStretchFactor(0, 50)
        splitter.setStretchFactor(1, 50)

        layout.addWidget(splitter)

        # Info footer
        info = QLabel(
            "💡 Memories are long-term facts the agent remembers about you. "
            "Higher importance = included in more contexts."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #666; padding: 8px; font-size: 10pt;")
        layout.addWidget(info)

    def refresh(self):
        """Refresh memory list."""
        self.memory_list.clear()

        min_importance = self.importance_filter.value()
        memories = self.memory_service.get_all_memories(min_importance=min_importance)

        for memory in memories:
            icon = "⭐" * memory.importance  # Star rating
            list_item = QListWidgetItem(f"{icon} {memory.key}")
            list_item.setData(Qt.ItemDataRole.UserRole, memory)
            self.memory_list.addItem(list_item)

    def on_selection_changed(self):
        """Handle memory selection."""
        selected = self.memory_list.selectedItems()
        if selected:
            self.current_memory = selected[0].data(Qt.ItemDataRole.UserRole)
            self.show_detail(self.current_memory)
            self.edit_btn.setEnabled(True)
            self.delete_btn.setEnabled(True)
        else:
            self.current_memory = None
            self.detail_text.clear()
            self.edit_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)

    def show_detail(self, memory):
        """Show memory details."""
        html = f"""
        <div style='padding: 8px;'>
            <p><b>Key:</b> {memory.key}</p>
            <p><b>Importance:</b> {"⭐" * memory.importance} ({memory.importance}/10)</p>
            <p><b>Updated:</b> {memory.updated_at.strftime('%Y-%m-%d %H:%M') if memory.updated_at else 'N/A'}</p>
            <hr/>
            <p><b>Content:</b></p>
            <div style='background: #f5f5f5; padding: 12px; border-radius: 4px; white-space: pre-wrap;'>{memory.content}</div>
        </div>
        """
        self.detail_text.setHtml(html)

    def create_memory(self):
        """Create new memory."""
        dialog = MemoryDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            try:
                self.memory_service.update_memory(
                    key=data['key'],
                    content=data['content'],
                    importance=data['importance']
                )
                self.refresh()
                logger.info(f"Created memory: {data['key']}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create memory: {str(e)}")

    def edit_memory(self):
        """Edit selected memory."""
        if not self.current_memory:
            return

        dialog = MemoryDialog(self, self.current_memory)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            try:
                self.memory_service.update_memory(
                    key=data['key'],
                    content=data['content'],
                    importance=data['importance']
                )
                self.refresh()
                logger.info(f"Updated memory: {data['key']}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to update memory: {str(e)}")

    def delete_memory(self):
        """Delete selected memory."""
        if not self.current_memory:
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete memory '{self.current_memory.key}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.memory_service.delete_memory(self.current_memory.key)
                self.refresh()
                logger.info(f"Deleted memory: {self.current_memory.key}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete memory: {str(e)}")
```

**Estimated Time:** 2.5 hours

#### 5. Add Memory Panel to Main Window

**File:** `gembrain/ui/main_window.py`
**Location:** In `_setup_navigation()` method

```python
# Add memory panel
self.memory_panel = MemoryPanel(self.db_session, self.memory_service)
self.content_stack.addWidget(self.memory_panel)

# Add to nav buttons
memory_btn = QPushButton("🧠 Memory")
memory_btn.clicked.connect(lambda: self.content_stack.setCurrentWidget(self.memory_panel))
nav_layout.addWidget(memory_btn)
```

**Estimated Time:** 15 minutes

**Total for FEATURE-003:** ~3.5 hours

---

## Project CRUD Completion

### FEATURE-004: Complete Project Operations

**Current Gaps:**
- ✗ No update_project action
- ✗ No delete_project action
- ✗ No search_projects action
- ✗ Projects panel missing edit/delete

**Changes Required:**

#### 1. Add Project Action Handlers

**File:** `gembrain/agents/tools.py`
**Location:** After line 899

```python
def _update_project(self, action: Dict[str, Any]) -> ActionResult:
    """Update a project.

    Args:
        action: {
            'type': 'update_project',
            'project_id': int,
            'name': str (optional),
            'description': str (optional),
            'status': str (optional),
            'tags': list (optional)
        }
    """
    project_id = action.get('project_id')
    if not project_id:
        return ActionResult(
            action_type='update_project',
            success=False,
            message='project_id is required'
        )

    # Build update kwargs
    update_fields = {}
    if 'name' in action:
        update_fields['name'] = action['name']
    if 'description' in action:
        update_fields['description'] = action['description']
    if 'status' in action:
        try:
            from ..core.models import ProjectStatus
            update_fields['status'] = ProjectStatus[action['status'].upper()]
        except KeyError:
            return ActionResult(
                action_type='update_project',
                success=False,
                message=f"Invalid status: {action['status']}"
            )
    if 'tags' in action:
        update_fields['tags'] = ','.join(action['tags'])

    project = self.project_service.update_project(project_id, **update_fields)

    if project:
        return ActionResult(
            action_type='update_project',
            success=True,
            message=f"Updated project: {project.name}",
            data={'project_id': project.id, 'name': project.name}
        )
    else:
        return ActionResult(
            action_type='update_project',
            success=False,
            message=f"Project {project_id} not found"
        )


def _delete_project(self, action: Dict[str, Any]) -> ActionResult:
    """Delete a project.

    Args:
        action: {'type': 'delete_project', 'project_id': int}
    """
    project_id = action.get('project_id')
    if not project_id:
        return ActionResult(
            action_type='delete_project',
            success=False,
            message='project_id is required'
        )

    # Get project details before deleting
    project = self.project_service.get_project(project_id)
    if not project:
        return ActionResult(
            action_type='delete_project',
            success=False,
            message=f"Project {project_id} not found"
        )

    name = project.name
    success = self.project_service.delete_project(project_id)

    if success:
        return ActionResult(
            action_type='delete_project',
            success=True,
            message=f"Deleted project: {name}"
        )
    else:
        return ActionResult(
            action_type='delete_project',
            success=False,
            message=f"Failed to delete project {project_id}"
        )


def _search_projects(self, action: Dict[str, Any]) -> ActionResult:
    """Search projects by name.

    Args:
        action: {
            'type': 'search_projects',
            'query': str,
            'status': str (optional)
        }
    """
    query = action.get('query', '')

    # Get all projects (filtered by status if specified)
    status_filter = None
    if 'status' in action:
        try:
            from ..core.models import ProjectStatus
            status_filter = ProjectStatus[action['status'].upper()]
        except KeyError:
            return ActionResult(
                action_type='search_projects',
                success=False,
                message=f"Invalid status: {action['status']}"
            )

    all_projects = self.project_service.get_all_projects(status=status_filter)

    # Filter by query
    if query:
        query_lower = query.lower()
        projects = [
            p for p in all_projects
            if query_lower in p.name.lower() or query_lower in (p.description or '').lower()
        ]
    else:
        projects = all_projects

    projects_data = [
        {
            'id': p.id,
            'name': p.name,
            'status': p.status.value,
            'description': p.description[:100] + '...' if p.description and len(p.description) > 100 else p.description,
        }
        for p in projects
    ]

    return ActionResult(
        action_type='search_projects',
        success=True,
        message=f"Found {len(projects)} projects",
        data={'projects': projects_data, 'count': len(projects)}
    )
```

**Also update action handlers dict (~line 280):**
```python
'update_project': self._update_project,
'delete_project': self._delete_project,
'search_projects': self._search_projects,
```

**Estimated Time:** 1 hour

#### 2. Add code_api Methods

**File:** `gembrain/agents/code_api.py`
**Location:** After line 242

```python
def update_project(self, project_id: int, **kwargs) -> bool:
    """Update a project.

    Args:
        project_id: Project ID
        **kwargs: Fields to update (name, description, status, tags)

    Returns:
        True if updated, False if not found

    Example:
        gb.update_project(1, status="completed", description="Finished!")
    """
    # Convert status string to enum if provided
    if 'status' in kwargs:
        from ..core.models import ProjectStatus
        if isinstance(kwargs['status'], str):
            kwargs['status'] = ProjectStatus[kwargs['status'].upper()]

    # Convert tags list to string if provided
    if 'tags' in kwargs and isinstance(kwargs['tags'], list):
        kwargs['tags'] = ','.join(kwargs['tags'])

    project = self.project_service.update_project(project_id, **kwargs)
    return project is not None


def delete_project(self, project_id: int) -> bool:
    """Delete a project.

    Args:
        project_id: Project ID

    Returns:
        True if deleted, False if not found

    Example:
        gb.delete_project(1)
    """
    return self.project_service.delete_project(project_id)


def search_projects(self, query: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
    """Search projects.

    Args:
        query: Search query
        status: Optional status filter ("active", "completed", "archived")

    Returns:
        List of project dictionaries

    Example:
        active = gb.search_projects("website", status="active")
    """
    from ..core.models import ProjectStatus

    status_filter = None
    if status:
        try:
            status_filter = ProjectStatus[status.upper()]
        except KeyError:
            self.log(f"Invalid status: {status}")
            return []

    all_projects = self.project_service.get_all_projects(status=status_filter)

    # Filter by query
    if query:
        query_lower = query.lower()
        projects = [
            p for p in all_projects
            if query_lower in p.name.lower() or query_lower in (p.description or '').lower()
        ]
    else:
        projects = all_projects

    return [
        {
            'id': p.id,
            'name': p.name,
            'status': p.status.value,
            'description': p.description,
            'tags': p.tags.split(',') if p.tags else [],
            'updated_at': p.updated_at.isoformat() if p.updated_at else None,
        }
        for p in projects
    ]
```

**Estimated Time:** 30 minutes

#### 3. Enhance Projects Panel

**File:** `gembrain/ui/widgets/projects_panel.py`
**Add edit/delete buttons and dialogs**

```python
# Add to class ProjectsPanel after line 105:

def _setup_edit_delete_buttons(self):
    """Setup edit and delete buttons in detail view."""
    button_row = QHBoxLayout()

    self.edit_btn = QPushButton("✏️ Edit Project")
    self.edit_btn.clicked.connect(self.edit_project)
    button_row.addWidget(self.edit_btn)

    self.delete_btn = QPushButton("🗑️ Delete Project")
    self.delete_btn.clicked.connect(self.delete_project)
    button_row.addWidget(self.delete_btn)

    button_row.addStretch()

    # Add to detail layout (assumes self.detail_layout exists)
    self.detail_layout.addLayout(button_row)

def edit_project(self):
    """Edit current project."""
    if not self.current_project:
        return

    # Create edit dialog (similar to MemoryDialog/VaultItemDialog)
    from PyQt6.QtWidgets import QDialog, QFormLayout, QLineEdit, QTextEdit, QComboBox, QDialogButtonBox

    dialog = QDialog(self)
    dialog.setWindowTitle("Edit Project")
    dialog.setMinimumWidth(500)

    layout = QFormLayout(dialog)

    name_edit = QLineEdit(self.current_project.name)
    layout.addRow("Name:", name_edit)

    desc_edit = QTextEdit()
    desc_edit.setPlainText(self.current_project.description or "")
    desc_edit.setMaximumHeight(100)
    layout.addRow("Description:", desc_edit)

    status_combo = QComboBox()
    from ...core.models import ProjectStatus
    for status in ProjectStatus:
        status_combo.addItem(status.value, status)
    status_combo.setCurrentText(self.current_project.status.value)
    layout.addRow("Status:", status_combo)

    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addRow(buttons)

    if dialog.exec() == QDialog.DialogCode.Accepted:
        try:
            self.project_service.update_project(
                project_id=self.current_project.id,
                name=name_edit.text().strip(),
                description=desc_edit.toPlainText().strip(),
                status=status_combo.currentData(),
            )
            self.load_projects()
            logger.info(f"Updated project: {name_edit.text()}")
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to update project: {str(e)}")

def delete_project(self):
    """Delete current project."""
    if not self.current_project:
        return

    from PyQt6.QtWidgets import QMessageBox

    reply = QMessageBox.question(
        self,
        "Confirm Delete",
        f"Are you sure you want to delete project '{self.current_project.name}'?\n\n"
        f"This will NOT delete associated tasks, but they will lose their project association.",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )

    if reply == QMessageBox.StandardButton.Yes:
        try:
            self.project_service.delete_project(self.current_project.id)
            self.load_projects()
            logger.info(f"Deleted project: {self.current_project.name}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete project: {str(e)}")
```

**Estimated Time:** 1 hour

**Total for FEATURE-004:** ~2.5 hours

---

## Enhanced Logging

### FEATURE-005: Add Detailed Logging to Iterative Reasoning

**Current Gaps:**
- Actions logged by count, not details
- Observations/insights not logged
- Reasoning text not logged

**Changes Required:**

**File:** `gembrain/agents/iterative_reasoner.py`

```python
# After line 396 (after creating iteration object):

logger.debug(f"📝 Created iteration object with {len(iteration.observations)} observations")

# ADD: Log reasoning summary
reasoning_summary = iteration.reasoning[:150] + "..." if len(iteration.reasoning) > 150 else iteration.reasoning
logger.info(f"💭 Reasoning: {reasoning_summary}")

# ADD: Log observations
if iteration.observations:
    logger.debug(f"👁️ Observations:")
    for i, obs in enumerate(iteration.observations, 1):
        logger.debug(f"  {i}. {obs}")

# ADD: Log insights
if iteration.insights_gained:
    logger.debug(f"💡 Insights gained:")
    for i, insight in enumerate(iteration.insights_gained, 1):
        logger.debug(f"  {i}. {insight}")

# Before line 401 (before logging action count):

# ADD: Log action details
if "next_actions" in iteration_data:
    iteration.actions_taken = iteration_data["next_actions"]
    logger.info(f"🎬 {len(iteration.actions_taken)} actions to execute")
    # ADD: Log each action
    for i, action in enumerate(iteration.actions_taken, 1):
        action_type = action.get('type', 'unknown')
        # Truncate large fields like 'code'
        action_summary = {k: (v[:100] + '...' if isinstance(v, str) and len(v) > 100 else v) for k, v in action.items()}
        logger.debug(f"  Action {i}: {action_type}")
        logger.debug(f"    {action_summary}")
```

**Estimated Time:** 30 minutes

---

## Automation System Exposure

### FEATURE-006: Expose Automation Rules (OPTIONAL - Low Priority)

**Note:** This is marked optional as automation rules are less critical than other features. Include if time permits.

**Changes Required:**
1. Add all CRUD action handlers for AutomationRule
2. Create AutomationPanel UI
3. Add to main window navigation
4. Update prompts to document automation features

**Estimated Time:** 4-5 hours

---

## Implementation Roadmap

### Phase 1: Critical Bugs (IMMEDIATE - 1 hour)
**Priority:** 🔴 CRITICAL
**Goal:** Fix breaking bugs

- [ ] BUG-001: Fix iteration block parsing regex (~30 min)
- [ ] BUG-002: Fix code_api.list_memories() call (~2 min)
- [ ] Test both fixes (~30 min)
- [ ] Commit and push

**Success Criteria:**
- Iterative reasoning doesn't terminate prematurely
- Code execution with gb.list_memories() works

---

### Phase 2: UI Restructuring (HIGH - 10 hours)
**Priority:** 🟡 HIGH
**Goal:** Separate final output from technical details

- [ ] FEATURE-001: Implement split-screen layout (~8-10 hours)
  - Create ConversationView class
  - Create TechnicalDetailsView class
  - Refactor ChatPanel to use splitter
  - Update OrchestratorWorker to emit structured progress
  - Update IterativeReasoner to call progress callback
  - Update ActionExecutor to call progress callback
  - Update CodeExecutor to call progress callback
  - Wire all signals/slots
  - Test UI responsiveness
  - Test real-time updates in technical view

**Success Criteria:**
- Upper half shows only conversation and final outputs
- Lower half shows all iterations, code, actions in tabs
- Real-time updates during processing
- UI remains responsive
- Splitter is resizable

---

### Phase 3: Vault Enhancement (HIGH - 5 hours)
**Priority:** 🟡 HIGH
**Goal:** Complete vault CRUD and UI

- [ ] FEATURE-002: Complete vault operations (~5 hours)
  - Add VaultItemRepository.update()
  - Add VaultService.update_item()
  - Add vault action handlers (update, delete, list)
  - Add code_api methods
  - Completely rewrite vault_panel.py
  - Test all CRUD operations
  - Test UI edit/delete functionality

**Success Criteria:**
- Can update vault items via UI and actions
- Can delete vault items via UI and actions
- Can list all vault items
- UI shows full item details including metadata
- JSON metadata editor works

---

### Phase 4: Memory Accessibility (HIGH - 3.5 hours)
**Priority:** 🟡 HIGH
**Goal:** Make memory system visible and manageable

- [ ] FEATURE-003: Expose memory operations (~3.5 hours)
  - Add memory action handlers (list, get, delete)
  - Add code_api methods
  - Create MemoryPanel UI
  - Add to main window navigation
  - Test all memory operations
  - Update prompts to document memory actions

**Success Criteria:**
- Can list all memories via UI and actions
- Can edit/delete memories in UI
- LLM can query and manage memories
- Memory importance visible and editable

---

### Phase 5: Project CRUD (MEDIUM - 2.5 hours)
**Priority:** 🟠 MEDIUM
**Goal:** Complete project operations

- [ ] FEATURE-004: Complete project CRUD (~2.5 hours)
  - Add project action handlers (update, delete, search)
  - Add code_api methods
  - Enhance projects panel with edit/delete
  - Test all operations
  - Update prompts

**Success Criteria:**
- Can update/delete projects via UI and actions
- Can search projects by name
- Projects panel has edit/delete buttons

---

### Phase 6: Enhanced Logging (MEDIUM - 30 min)
**Priority:** 🟠 MEDIUM
**Goal:** Better visibility into reasoning process

- [ ] FEATURE-005: Add detailed logging (~30 min)
  - Log action details in iterative_reasoner
  - Log observations and insights
  - Log reasoning summaries
  - Test log output

**Success Criteria:**
- Can see what actions LLM decided to take in each iteration
- Can see observations and insights
- Logs help debug reasoning issues

---

### Phase 7: Prompt Updates (LOW - 1 hour)
**Priority:** 🟢 LOW
**Goal:** Document all new features

- [ ] Update prompts.py with new actions
  - Add memory operations documentation
  - Add project CRUD documentation
  - Add vault CRUD documentation
  - Add code examples

**Success Criteria:**
- Prompts accurately reflect all available actions
- Examples show how to use new features

---

### Phase 8: Testing & Polish (ONGOING)
**Priority:** 🟢 LOW
**Goal:** Ensure quality

- [ ] Write unit tests for new repository methods
- [ ] Test all UI panels thoroughly
- [ ] Test all action handlers
- [ ] Test code_api methods
- [ ] Performance testing with large datasets
- [ ] UI polish (icons, styling, tooltips)

---

## Total Time Estimates

| Phase | Priority | Time | Cumulative |
|-------|----------|------|------------|
| Phase 1: Critical Bugs | 🔴 CRITICAL | 1 hour | 1 hour |
| Phase 2: UI Restructuring | 🟡 HIGH | 10 hours | 11 hours |
| Phase 3: Vault Enhancement | 🟡 HIGH | 5 hours | 16 hours |
| Phase 4: Memory Accessibility | 🟡 HIGH | 3.5 hours | 19.5 hours |
| Phase 5: Project CRUD | 🟠 MEDIUM | 2.5 hours | 22 hours |
| Phase 6: Enhanced Logging | 🟠 MEDIUM | 0.5 hours | 22.5 hours |
| Phase 7: Prompt Updates | 🟢 LOW | 1 hour | 23.5 hours |
| Phase 8: Testing & Polish | 🟢 LOW | 4-6 hours | ~28 hours |

**Total Estimated Time:** ~28 hours (3-4 days of focused work)

---

## Testing Strategy

### Unit Tests

**Create test files:**
- `tests/test_vault_repository.py` - Test vault CRUD
- `tests/test_memory_actions.py` - Test memory action handlers
- `tests/test_project_actions.py` - Test project action handlers
- `tests/test_iteration_parsing.py` - Test regex fix

### Integration Tests

**Test scenarios:**
1. **Iterative Reasoning Flow:**
   - Start reasoning session
   - Verify progress updates reach UI
   - Verify code execution results shown
   - Verify actions logged correctly
   - Verify final output in upper half

2. **Vault Operations:**
   - Create vault item via UI
   - Update via UI
   - Delete via UI
   - List via action
   - Search via action

3. **Memory Operations:**
   - Create memory via action
   - List via UI
   - Edit via UI
   - Delete via UI
   - Access via code execution

4. **Project Operations:**
   - Create via UI
   - Update via action
   - Delete via UI
   - Search via action

### UI Tests

**Manual testing checklist:**
- [ ] Split-screen layout renders correctly on different screen sizes
- [ ] Splitter resizes smoothly
- [ ] All tabs in technical view work
- [ ] Auto-scroll toggle works
- [ ] Clear/export buttons work
- [ ] All CRUD dialogs validate input
- [ ] All panels have refresh buttons
- [ ] All lists handle empty state
- [ ] All error messages are clear

### Performance Tests

**Test with large datasets:**
- 1000+ notes
- 500+ tasks
- 100+ vault items
- 50+ memories
- 20+ projects

**Verify:**
- UI remains responsive
- Lists load within 1 second
- Search is fast (<500ms)
- No memory leaks during long sessions

---

## Rollback Plan

If any phase causes critical issues:

1. **Immediate Actions:**
   - Revert commit
   - Document issue in GitHub issue
   - Disable feature with settings flag

2. **Feature Flags:**
   Add to `config/defaults.py`:
   ```python
   "ui": {
       "enable_split_screen": True,
       "enable_memory_panel": True,
       "enable_enhanced_vault": True,
   }
   ```

3. **Graceful Degradation:**
   - Old chat panel available as fallback
   - Old vault panel available if new one has issues

---

## Success Metrics

### Functionality
- ✅ All database entities accessible via UI
- ✅ All database entities accessible via LLM actions
- ✅ All CRUD operations complete
- ✅ Zero critical bugs
- ✅ Code execution history visible

### Usability
- ✅ Clear separation between output and logs
- ✅ Real-time visibility into reasoning
- ✅ Refresh buttons on all panels
- ✅ Edit/delete available for all entities
- ✅ Intuitive UI layout

### Performance
- ✅ UI remains responsive during reasoning
- ✅ Lists load within 1 second
- ✅ No UI freezes

### Code Quality
- ✅ All new code has docstrings
- ✅ Consistent naming conventions
- ✅ Error handling in all operations
- ✅ Logging at appropriate levels
- ✅ Type hints where applicable

---

## Approval Required

**User:** Please review this plan and approve the following:

1. **Priority Order:** Are phases in correct priority order?
2. **Scope:** Any features to add/remove?
3. **UI Design:** Split-screen layout acceptable?
4. **Time Estimates:** Realistic? Need adjustments?
5. **Start Point:** Begin with Phase 1 (critical bugs)?

**To Approve:**
Reply with "APPROVED" or specific changes needed.

**To Request Changes:**
Specify which sections need modification.

---

**End of Plan Document**
