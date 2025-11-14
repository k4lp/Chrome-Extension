"""Iterative reasoning system for complex problem solving."""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from loguru import logger
import json
import re

from .gemini_client import GeminiClient
from ..config.models import Settings


@dataclass
class ReasoningIteration:
    """A single iteration of reasoning."""

    iteration_number: int
    reasoning: str
    observations: List[str] = field(default_factory=list)
    actions_taken: List[Dict[str, Any]] = field(default_factory=list)
    action_results: List[Dict[str, Any]] = field(default_factory=list)
    insights_gained: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "iteration_number": self.iteration_number,
            "reasoning": self.reasoning,
            "observations": self.observations,
            "actions_taken": self.actions_taken,
            "action_results": self.action_results,
            "insights_gained": self.insights_gained,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ReasoningSession:
    """Complete reasoning session with all iterations."""

    user_query: str
    iterations: List[ReasoningIteration] = field(default_factory=list)
    final_output: Optional[str] = None
    completion_reason: Optional[str] = None
    is_complete: bool = False
    verification_result: Optional[Dict[str, Any]] = None
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "user_query": self.user_query,
            "iterations": [it.to_dict() for it in self.iterations],
            "final_output": self.final_output,
            "completion_reason": self.completion_reason,
            "is_complete": self.is_complete,
            "verification_result": self.verification_result,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


ITERATIVE_REASONING_PROMPT = """You are GemBrain's Iterative Reasoning Engine.

═══════════════════════════════════════════════════════════════════════════════
YOUR MISSION
═══════════════════════════════════════════════════════════════════════════════

When given a complex task, you must:
1. **Decompose** it into smaller, manageable sub-tasks
2. **Execute** each sub-task systematically
3. **Store** intermediate results in the vault
4. **Build** toward the final solution through multiple iterations

═══════════════════════════════════════════════════════════════════════════════
CRITICAL: CODE CAN USE GEMBRAIN API
═══════════════════════════════════════════════════════════════════════════════

When you execute Python code, you have access to the 'gb' object with full GemBrain API:

**This is CRUCIAL to avoid token limits!**

Instead of returning large data to the LLM:
✗ BAD:  return large_json_data  # Hits token limits!
✓ GOOD: gb.datavault_store(json.dumps(data), filetype="json")  # Store it!
✓ GOOD: gb.create_memory(summary, notes="Analysis summary")  # Store insights!
✓ GOOD: for item in items: gb.create_task(item['content'])  # Create tasks in code!

Available in code as 'gb':
- gb.create_task(content, notes="", status="pending")
- gb.update_task(task_id, content=None, notes=None, status=None)
- gb.delete_task(task_id)
- gb.list_tasks(status=None, limit=50)
- gb.search_tasks(query, limit=20)
- gb.create_memory(content, notes="")
- gb.update_memory(memory_id, content=None, notes=None)
- gb.search_memories(query, limit=20)
- gb.list_memories(limit=50)
- gb.create_goal(content, notes="", status="pending")
- gb.list_goals(status=None, limit=50)
- gb.datavault_store(content, filetype="text", notes="")  # Store large data!
- gb.datavault_get(item_id)
- gb.datavault_search(query, limit=20)
- gb.log(message)

Example code:
```python
import json

# Analyze data
results = analyze_large_dataset(data)

# DON'T return it - store it in datavault!
gb.datavault_store(json.dumps(results), filetype="json", notes="Analysis results")

# Create tasks from results
for task in results['todo_items']:
    gb.create_task(task['content'], notes=task.get('details', ''))

# Store insights in memory
gb.create_memory("Analysis completed successfully", notes="1000 items processed")

# Log what you did
gb.log("Processed 1000 items, created 15 tasks")
```

═══════════════════════════════════════════════════════════════════════════════
ITERATION STRUCTURE
═══════════════════════════════════════════════════════════════════════════════

**Iteration 1 MUST decompose the task:**
```iteration
{
  "iteration": 1,
  "reasoning": "COMPLETE DETAILED REASONING HERE - Include ALL your thoughts, analysis, observations, and insights in this field. Use markdown formatting. Be comprehensive and detailed. Example:\n\n## Task Analysis\nBreaking down the task into manageable steps...\n\n## Observations\n- Identified X sub-tasks\n- Dependencies: ...\n\n## Insights\n- Task requires...\n- Will need to...",
  "observations": ["Identified X sub-tasks", "Dependencies: ..."],
  "subtasks": [
    {"id": 1, "description": "...", "dependencies": []},
    {"id": 2, "description": "...", "dependencies": [1]},
    ...
  ],
  "next_actions": [...],
  "insights_gained": ["Task requires ...", "Will need to ..."],
  "is_final": false
}
```

**CRITICAL: The "reasoning" field must contain your COMPLETE, DETAILED reasoning text including ALL thoughts, observations, analysis, and insights. Use markdown formatting (headings, lists, code blocks, etc.). Be verbose and comprehensive - this is what the user will see!**

**Subsequent iterations work through subtasks:**
```iteration
{
  "iteration": <number>,
  "current_subtask": <id>,
  "reasoning": "COMPLETE DETAILED REASONING - Put ALL your thoughts here in markdown format. Include what you're doing, why, what you observe, and insights gained.",
  "observations": ["<observation 1>", ...],
  "next_actions": [
    {"type": "datavault_store", "content": "...", "filetype": "text", "notes": "step_X_results"},
    {"type": "execute_code", "code": "..."},
    ...
  ],
  "insights_gained": ["<insight 1>", ...],
  "is_final": false
}
```

**Final iteration:**
```iteration
{
  "iteration": <number>,
  "reasoning": "COMPLETE FINAL REASONING - Comprehensive summary of the entire process, what was accomplished, and conclusions.",
  "observations": ["All subtasks completed", ...],
  "final_output": "Complete answer formatted in MARKDOWN with references to datavault items. Use proper markdown formatting: headings, lists, code blocks, tables, etc.",
  "completion_reason": "All subtasks complete, results stored in datavault",
  "is_final": true
}
```

═══════════════════════════════════════════════════════════════════════════════
COMPLETION CRITERIA (When to set is_final: true)
═══════════════════════════════════════════════════════════════════════════════

Set is_final: true when ALL 3 of these are satisfied:

1. **Query Answered** - You have a complete answer to the user's question
2. **Actions Completed** - All necessary operations have executed successfully
3. **Output Ready** - You have written the final_output in markdown format

If all 3 are met, set is_final: true with the final_output field. Don't overthink it.

IMPORTANT: If actions succeeded and you have an answer, SET is_final: true immediately!

═══════════════════════════════════════════════════════════════════════════════
YOU ARE A FULLY AUTONOMOUS AI AGENT
═══════════════════════════════════════════════════════════════════════════════

You are a SELF-DIRECTED, PROACTIVE agent that independently plans and executes tasks
without waiting for human approval. You have FULL AUTONOMY to make decisions and take action.

**CORE OPERATING PRINCIPLES:**

1. **BE AUTONOMOUS** - Take action immediately. Don't ask for permission or wait for approval
2. **BE PROACTIVE** - Anticipate needs and act without being told. Execute liberally
3. **THINK DEEPLY** - Use comprehensive Chain-of-Thought reasoning for EVERY decision
4. **BE SYSTEMATIC** - Decompose complex problems into clear, manageable subtasks
5. **EXECUTE LIBERALLY** - Use all available actions extensively (code, tasks, memory, datavault)
6. **LOG EVERYTHING** - Use gb.log() to document EVERY step, decision, and observation
7. **LEARN CONTINUOUSLY** - Each iteration builds on previous results and insights
8. **SELF-CRITIQUE** - Question assumptions, validate results, iterate until perfect
9. **BE THOROUGH** - Quality over speed. Take as many iterations as needed

**MANDATORY LOGGING:**
- At the START of each iteration: gb.log("Starting iteration N: <what you're doing>")
- For EVERY action taken: gb.log("<action description>: <details>")
- For EVERY decision made: gb.log("Decision: <reasoning>")
- For EVERY observation: gb.log("Observed: <what you noticed>")
- At the END of each iteration: gb.log("Completed iteration N: <summary>")

**YOU ARE IN CONTROL** - You decide what to do, when, and how. Execute code, create tasks,
store data, and make decisions autonomously. The user trusts you to complete the task
without micromanagement. ACT DECISIVELY AND INDEPENDENTLY.

═══════════════════════════════════════════════════════════════════════════════
AVAILABLE ACTIONS
═══════════════════════════════════════════════════════════════════════════════

Query Actions: list_tasks, search_tasks, list_memories, search_memories, list_goals, search_goals, datavault_list, datavault_search
Create Actions: create_task, create_memory, create_goal, datavault_store
Update Actions: update_task, update_memory, update_goal, datavault_update
Delete Actions: delete_task, delete_memory, delete_goal, datavault_delete
Execute: execute_code (for analysis, automation, complex operations)

═══════════════════════════════════════════════════════════════════════════════
EXAMPLE ITERATION FLOW
═══════════════════════════════════════════════════════════════════════════════

Iteration 1: Understand the problem, gather initial context
Iteration 2: Analyze gathered data, identify gaps
Iteration 3: Fill gaps, perform deeper analysis
Iteration 4: Synthesize findings, validate approach
Iteration 5: Execute final actions, verify completeness
Iteration 6: Set is_final: true with complete output

═══════════════════════════════════════════════════════════════════════════════
CONCRETE EXAMPLE: When to Stop Iterating
═══════════════════════════════════════════════════════════════════════════════

User asks: "Create a project called Marketing with 3 tasks"

Iteration 1: Plan approach
- Reasoning: "User wants a Marketing project with 3 tasks. I'll use execute_code to create both."
- Actions: None (just planning)
- is_final: false

Iteration 2: Execute actions
- Reasoning: "Creating project and tasks now..."
- Actions: execute_code to create project + 3 tasks
- Action results: Project created (ID 42), 3 tasks created successfully
- is_final: false (need to verify and provide output)

Iteration 3: Verify and conclude
- Reasoning: "Actions succeeded. All tasks created. Query is answered."
- Observations: ["Project created with ID 42", "3 tasks created successfully"]
- final_output: "# Marketing Project Created\n\nI've set up your Marketing project with 3 tasks:\n1. Research competitors\n2. Plan Q1 campaign\n3. Design landing page\n\nAll tasks are in todo status and ready for you to work on."
- completion_reason: "Project and tasks successfully created and verified"
- is_final: true ✅

DON'T continue iterating after task is done! If actions succeeded and you have an answer, STOP.

═══════════════════════════════════════════════════════════════════════════════
REMEMBER
═══════════════════════════════════════════════════════════════════════════════

- You can take as many iterations as needed
- Quality over speed - be thorough
- Always output the ```iteration block
- Only set is_final: true when TRULY complete
- Your reasoning log will be verified by another model
"""

VERIFICATION_PROMPT = """You are GemBrain's Reasoning Verification Engine.

═══════════════════════════════════════════════════════════════════════════════
YOUR MISSION
═══════════════════════════════════════════════════════════════════════════════

You must STRICTLY VERIFY whether an iterative reasoning session is COMPLETE and CORRECT.

You will receive:
1. The original user query
2. The complete reasoning log (all iterations)
3. All actions taken and their results
4. The proposed final output (may be empty!)
5. **GOALS** - Expected outcomes that define success criteria (if any exist)

Your jobs:
1. Decide if this work is acceptable or needs more iterations
2. **ALWAYS provide session_summary** - a user-facing markdown summary of what was accomplished
3. **Check if GOALS are met** - If goals exist, verify the output achieves them
4. If approved: false, provide specific recommendations for what needs to be done next

CRITICAL: Even if final_output is missing, you must analyze the iterations and action results
to create a helpful session_summary that the user can understand.

═══════════════════════════════════════════════════════════════════════════════
VERIFICATION CRITERIA (ALL must be satisfied)
═══════════════════════════════════════════════════════════════════════════════

1. **Query Fully Addressed** ✓
   - Does the output answer the user's question completely?
   - Are all explicit AND implicit requirements met?

2. **Goals Met** ✓
   - If goals exist, does the output achieve them?
   - Are all specified success criteria satisfied?
   - N/A if no goals were defined (score as 10/10)

3. **Reasoning Quality** ✓
   - Is the reasoning logical and coherent?
   - Are conclusions supported by evidence?
   - Were appropriate actions taken?

4. **Completeness** ✓
   - Were all sub-problems addressed?
   - Is the output actionable and clear?
   - Are edge cases considered?

5. **Correctness** ✓
   - Are facts accurate?
   - Are actions appropriate?
   - Is the solution valid?

6. **No Hallucinations** ✓
   - Are all claims backed by data?
   - No invented information?

7. **Proper Use of Tools** ✓
   - Were the right actions used?
   - Were IDs retrieved (not guessed)?
   - Was code execution appropriate?

═══════════════════════════════════════════════════════════════════════════════
OUTPUT FORMAT (MANDATORY)
═══════════════════════════════════════════════════════════════════════════════

```verification
{
  "approved": true/false,
  "confidence": 0.0-1.0,
  "criteria_scores": {
    "query_addressed": 0-10,
    "goals_met": 0-10,
    "reasoning_quality": 0-10,
    "completeness": 0-10,
    "correctness": 0-10,
    "no_hallucinations": 0-10,
    "tool_usage": 0-10
  },
  "strengths": ["<strength 1>", "<strength 2>", ...],
  "weaknesses": ["<weakness 1>", "<weakness 2>", ...],
  "missing_elements": ["<what's missing 1>", ...],
  "verdict": "<detailed explanation of your decision>",
  "recommendation": "<what should happen next>",
  "session_summary": "<markdown-formatted summary of what was accomplished during the session, including action results. This will be shown to the user if final_output is missing. Be comprehensive and include specific details about what was done.>"
}
```

IMPORTANT:
- Set approved: true ONLY if ALL criteria score >= 8/10
- Be STRICT - this is quality control
- Minimum confidence for approval: 0.85
- **ALWAYS provide session_summary** - This is MANDATORY even if approved: false
  * Analyze all iterations and action results
  * Create user-facing markdown summary of what was accomplished
  * Include specific details: what actions ran, what succeeded, what data was collected
  * This will be shown to the user if final_output is missing
- **ALWAYS provide recommendation** when approved: false
  * Be specific: what exact steps should be taken next?
  * Example: "Need to execute code to retrieve project list, then create summary note"
  * Help the system understand what's missing to complete the task
"""


class IterativeReasoner:
    """Iterative reasoning system with verification."""

    def __init__(
        self,
        gemini_client: GeminiClient,
        settings: Settings,
        action_handler: Any,
        max_iterations: int = 50,
    ):
        """Initialize iterative reasoner.

        Args:
            gemini_client: Gemini client for reasoning
            settings: Application settings
            action_handler: Action handler for executing actions
            max_iterations: Maximum iterations before forced stop
        """
        self.gemini_client = gemini_client
        self.settings = settings
        self.action_handler = action_handler
        self.max_iterations = max_iterations

    def reason(
        self,
        user_query: str,
        initial_context: Optional[List[str]] = None,
        progress_callback: Optional[callable] = None,
    ) -> ReasoningSession:
        """Run iterative reasoning on a query.

        Args:
            user_query: User's query/task
            initial_context: Optional initial context
            progress_callback: Optional callback for progress updates (receives message string)

        Returns:
            Complete reasoning session
        """
        session = ReasoningSession(user_query=user_query)
        iteration_count = 0

        logger.info(f"🧠 Starting iterative reasoning for: {user_query}")

        while iteration_count < self.max_iterations:
            iteration_count += 1

            logger.info(f"🔄 Iteration {iteration_count}/{self.max_iterations}")

            # Emit iteration start progress
            if progress_callback:
                progress_callback({
                    "type": "iteration_start",
                    "iteration": iteration_count,
                    "max_iterations": self.max_iterations,
                })

            # Build context for this iteration
            context_blocks = self._build_iteration_context(session, initial_context)
            logger.debug(f"📦 Context blocks count: {len(context_blocks)}")

            # Generate reasoning for this iteration
            try:
                logger.debug(f"🤖 Calling Gemini API for iteration {iteration_count}")
                response = self.gemini_client.generate(
                    system_prompt=ITERATIVE_REASONING_PROMPT,
                    user_message=f"Query: {user_query}\n\nContinue reasoning. Current iteration: {iteration_count}",
                    context_blocks=context_blocks,
                )
                logger.debug(f"📨 Received response (length: {len(response)} chars)")

                # Parse iteration response
                iteration_data = self._parse_iteration_response(response)

                if not iteration_data:
                    logger.error("❌ Failed to parse iteration response - no iteration_data returned")
                    logger.error(f"Response preview: {response[:500]}")
                    break

                logger.debug(f"✅ Parsed iteration data: {json.dumps(iteration_data, indent=2)}")

                # Emit thought/reasoning progress
                if progress_callback and iteration_data.get("reasoning"):
                    progress_callback({
                        "type": "thought",
                        "content": iteration_data.get("reasoning", ""),
                    })

                # Create iteration object
                iteration = ReasoningIteration(
                    iteration_number=iteration_count,
                    reasoning=iteration_data.get("reasoning", ""),
                    observations=iteration_data.get("observations", []),
                    insights_gained=iteration_data.get("insights_gained", []),
                )
                logger.debug(f"📝 Created iteration object with {len(iteration.observations)} observations")

                # Emit observations progress
                if progress_callback and iteration.observations:
                    observations_text = "\n".join(f"• {obs}" for obs in iteration.observations)
                    progress_callback({
                        "type": "observation",
                        "content": observations_text,
                    })

                # Emit insights gained progress
                if progress_callback and iteration.insights_gained:
                    insights_text = "\n".join(f"• {insight}" for insight in iteration.insights_gained)
                    progress_callback({
                        "type": "insights",
                        "content": insights_text,
                    })

                # Execute actions if any
                if "next_actions" in iteration_data:
                    iteration.actions_taken = iteration_data["next_actions"]
                    logger.info(f"🎬 {len(iteration.actions_taken)} actions to execute")

                    # Emit actions planned progress
                    if progress_callback:
                        progress_callback({
                            "type": "actions_planned",
                            "actions": iteration.actions_taken,
                        })

                    # Execute actions and capture results
                    try:
                        action_results = self.action_handler.execute_actions(iteration.actions_taken)
                        iteration.action_results = [
                            {
                                "action_type": result.action_type,
                                "success": result.success,
                                "message": result.message,
                                "data": result.data,
                            }
                            for result in action_results
                        ]
                        logger.info(f"✅ Executed {len(action_results)} actions")

                        # Emit progress for each action result
                        if progress_callback:
                            for result in action_results:
                                # Emit action result
                                progress_callback({
                                    "type": "action_result",
                                    "action_type": result.action_type,
                                    "success": result.success,
                                    "message": result.message,
                                    "data": result.data,
                                })

                                # Special handling for code execution - emit code result event
                                if result.action_type == "execute_code" and result.data:
                                    progress_callback({
                                        "type": "code_execution_result",
                                        "data": result.data,
                                    })

                    except Exception as e:
                        logger.error(f"❌ Action execution failed: {e}")
                        iteration.action_results = [
                            {
                                "action_type": "error",
                                "success": False,
                                "message": f"Action execution failed: {str(e)}",
                                "data": None,
                            }
                        ]
                else:
                    logger.debug("ℹ️ No actions in this iteration")

                session.iterations.append(iteration)

                # Check if final
                is_final = iteration_data.get("is_final", False)
                logger.info(f"🏁 is_final: {is_final}")

                if is_final:
                    session.final_output = iteration_data.get("final_output", "")
                    session.completion_reason = iteration_data.get("completion_reason", "")
                    session.is_complete = True
                    session.completed_at = datetime.now()
                    logger.info(f"✅ Reasoning complete after {iteration_count} iterations")
                    logger.info(f"📤 Final output length: {len(session.final_output)} chars")

                    # Emit completion progress
                    if progress_callback:
                        progress_callback({
                            "type": "reasoning_complete",
                            "success": True,
                            "message": f"Completed after {iteration_count} iterations",
                        })

                    break
                else:
                    logger.debug(f"⏩ Continuing to next iteration (not final)")

            except Exception as e:
                logger.error(f"Error in iteration {iteration_count}: {e}")
                break

        # If max iterations reached without completion
        if not session.is_complete:
            session.is_complete = True
            session.completion_reason = f"Maximum iterations ({self.max_iterations}) reached"
            session.completed_at = datetime.now()

            # Note: final_output may be empty here if LLM never set is_final: true
            # The verification step will generate session_summary which will be used as fallback
            if not session.final_output:
                logger.warning(f"⚠️ Forced stop after {self.max_iterations} iterations without final_output")
                logger.info("📝 Verification will provide session_summary as fallback")
            else:
                logger.warning(f"⚠️ Forced stop after {self.max_iterations} iterations (has final_output)")

        return session

    def verify(
        self,
        session: ReasoningSession,
        verification_model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Verify reasoning session with separate model.

        Args:
            session: Reasoning session to verify
            verification_model: Model to use for verification

        Returns:
            Verification result
        """
        logger.info("🔍 Starting verification...")

        # Build verification context
        verification_context = self._build_verification_context(session)

        # Temporarily switch model if specified
        original_model = self.settings.api.default_model
        if verification_model:
            self.settings.api.default_model = verification_model
            self.gemini_client.reconfigure(self.settings)

        try:
            response = self.gemini_client.generate(
                system_prompt=VERIFICATION_PROMPT,
                user_message="Verify the reasoning session below.",
                context_blocks=[verification_context],
            )

            # Parse verification response
            verification_result = self._parse_verification_response(response)

            # Restore original model
            if verification_model:
                self.settings.api.default_model = original_model
                self.gemini_client.reconfigure(self.settings)

            session.verification_result = verification_result

            if verification_result.get("approved"):
                logger.info("✅ Verification PASSED")
            else:
                logger.warning("❌ Verification FAILED")

            return verification_result

        except Exception as e:
            logger.error(f"Verification error: {e}")

            # Restore original model
            if verification_model:
                self.settings.api.default_model = original_model
                self.gemini_client.reconfigure(self.settings)

            return {
                "approved": False,
                "error": str(e),
                "verdict": "Verification failed due to error",
            }

    def _build_iteration_context(
        self, session: ReasoningSession, initial_context: Optional[List[str]] = None
    ) -> List[str]:
        """Build context for current iteration."""
        context_blocks = []

        if initial_context:
            context_blocks.extend(initial_context)

        # CRITICAL: Fetch current state from database (Tasks, Memory, Goals)
        # This ensures data created in iteration N is visible in iteration N+1
        if self.action_handler:
            try:
                # Current Tasks - ALL statuses (pending, ongoing, paused, completed)
                if hasattr(self.action_handler, 'task_service'):
                    all_tasks = self.action_handler.task_service.get_all_tasks()
                    if all_tasks:
                        tasks_text = "=== CURRENT TASKS ===\n"
                        for task in all_tasks:
                            tasks_text += f"[{task.id}] ({task.status.value}) {task.content}\n"
                            if task.notes:
                                tasks_text += f"  Notes: {task.notes}\n"
                        tasks_text += "\n"
                        context_blocks.append(tasks_text)

                # Current Memory - Recent memories (limit to avoid token bloat)
                if hasattr(self.action_handler, 'memory_service'):
                    recent_memories = self.action_handler.memory_service.get_all_memories(limit=20)
                    if recent_memories:
                        memory_text = "=== CURRENT MEMORIES ===\n"
                        for memory in recent_memories:
                            # Truncate content to 100 chars for context efficiency
                            content_preview = memory.content[:100]
                            if len(memory.content) > 100:
                                content_preview += "..."
                            memory_text += f"[{memory.id}] {content_preview}\n"
                            if memory.notes:
                                memory_text += f"  Notes: {memory.notes}\n"
                        memory_text += "\n"
                        context_blocks.append(memory_text)

                # Current Goals - For verification tracking
                if hasattr(self.action_handler, 'goal_service'):
                    all_goals = self.action_handler.goal_service.get_all_goals()
                    if all_goals:
                        goals_text = "=== CURRENT GOALS ===\n"
                        for goal in all_goals:
                            goals_text += f"[{goal.id}] ({goal.status.value}) {goal.content}\n"
                            if goal.notes:
                                goals_text += f"  Notes: {goal.notes}\n"
                        goals_text += "\n"
                        context_blocks.append(goals_text)

            except Exception as e:
                logger.warning(f"Failed to fetch current state from database: {e}")

        # Add previous iterations
        if session.iterations:
            iterations_summary = "=== PREVIOUS ITERATIONS ===\n\n"
            for it in session.iterations:
                iterations_summary += f"Iteration {it.iteration_number}:\n"
                iterations_summary += f"Reasoning: {it.reasoning}\n"
                iterations_summary += f"Observations: {', '.join(it.observations)}\n"
                iterations_summary += f"Insights: {', '.join(it.insights_gained)}\n"

                # CRITICAL: Include action results so LLM knows what happened!
                if it.action_results:
                    iterations_summary += f"Actions Executed: {len(it.action_results)}\n"
                    for action_result in it.action_results:
                        action_type = action_result.get("action_type", "unknown")
                        success = action_result.get("success", False)
                        message = action_result.get("message", "")
                        data = action_result.get("data")

                        status = "✓" if success else "✗"
                        iterations_summary += f"  {status} {action_type}: {message}\n"

                        # For code execution, include stdout/stderr/result
                        if action_type == "execute_code" and data:
                            if data.get("stdout"):
                                iterations_summary += f"    Output: {data['stdout'][:500]}\n"
                            if data.get("result"):
                                iterations_summary += f"    Result: {str(data['result'])[:500]}\n"
                            if data.get("error"):
                                iterations_summary += f"    Error: {data['error'][:500]}\n"

                iterations_summary += "\n"

            context_blocks.append(iterations_summary)

        return context_blocks

    def _build_verification_context(self, session: ReasoningSession) -> str:
        """Build context for verification."""
        context = f"""
=== ORIGINAL QUERY ===
{session.user_query}

"""

        # Fetch and include Goals (if any exist)
        try:
            from ..core.models import GoalStatus
            # Access goal_service through action_handler
            pending_goals = self.action_handler.goal_service.get_all_goals(GoalStatus.PENDING)

            if pending_goals:
                context += "=== GOALS (Expected Outcomes for Verification) ===\n"
                for goal in pending_goals:
                    context += f"- [{goal.id}] {goal.content}\n"
                    if goal.notes:
                        context += f"  Notes: {goal.notes}\n"
                context += "\n**IMPORTANT**: Verify that the final output achieves these goals!\n\n"
            else:
                context += "=== GOALS ===\nNo goals defined for this session.\n\n"
        except Exception as e:
            logger.warning(f"Failed to fetch goals for verification: {e}")
            context += "=== GOALS ===\nUnable to fetch goals.\n\n"

        context += f"""
=== REASONING LOG ===
Total Iterations: {len(session.iterations)}
Duration: {(session.completed_at - session.started_at).total_seconds():.2f}s

"""
        for iteration in session.iterations:
            context += f"""
--- Iteration {iteration.iteration_number} ---
Reasoning: {iteration.reasoning}

Observations:
{chr(10).join(f"  - {obs}" for obs in iteration.observations)}

Actions Taken: {len(iteration.actions_taken)}
{chr(10).join(f"  {json.dumps(action)}" for action in iteration.actions_taken)}

Insights Gained:
{chr(10).join(f"  - {insight}" for insight in iteration.insights_gained)}

"""

        context += f"""
=== FINAL OUTPUT ===
{session.final_output}

=== COMPLETION REASON ===
{session.completion_reason}
"""

        return context

    def _fix_json_control_chars(self, json_str: str) -> str:
        """Fix unescaped control characters in JSON string values.

        LLMs sometimes generate JSON with literal newlines/tabs in string values.
        This function escapes them properly so json.loads() can parse it.
        """
        result = []
        in_string = False
        escape_next = False

        for i, char in enumerate(json_str):
            # Handle escape sequences
            if escape_next:
                result.append(char)
                escape_next = False
                continue

            if char == '\\':
                result.append(char)
                escape_next = True
                continue

            # Track when we're inside a string
            if char == '"':
                in_string = not in_string
                result.append(char)
                continue

            # Escape control characters inside strings
            if in_string:
                if char == '\n':
                    result.append('\\n')
                elif char == '\r':
                    result.append('\\r')
                elif char == '\t':
                    result.append('\\t')
                elif char == '\b':
                    result.append('\\b')
                elif char == '\f':
                    result.append('\\f')
                elif ord(char) < 32:  # Other control characters
                    result.append(f'\\u{ord(char):04x}')
                else:
                    result.append(char)
            else:
                result.append(char)

        return ''.join(result)

    def _parse_iteration_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse iteration response from model using proper brace counting."""
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
            # This properly handles nested code blocks with ``` inside JSON strings
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

                # Handle strings (ignore braces inside strings)
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
                logger.error(f"Response sample: {response[json_start:json_start+500]}")
                return None

            json_str = response[json_start:json_end]
            logger.debug(f"✅ Found ```iteration block (length: {len(json_str)} chars)")
            logger.debug(f"JSON string preview: {json_str[:200]}")

            # Fix control characters in JSON string values
            # LLMs sometimes generate literal newlines in JSON strings which need to be escaped
            json_str_fixed = self._fix_json_control_chars(json_str)

            parsed = json.loads(json_str_fixed, strict=False)
            logger.debug(f"✅ Successfully parsed JSON with keys: {list(parsed.keys())}")
            return parsed

        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse iteration JSON: {e}")
            logger.error(f"JSON string that failed: {json_str[:500] if 'json_str' in locals() else 'N/A'}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error in _parse_iteration_response: {e}")
            return None

    def _parse_verification_response(self, response: str) -> Dict[str, Any]:
        """Parse verification response from model."""
        try:
            # Extract ```verification block
            match = re.search(r"```verification\s*\n(.*?)\n```", response, re.DOTALL)
            if match:
                json_str = match.group(1)
                return json.loads(json_str, strict=False)
            else:
                logger.error("No ```verification block found in response")
                return {"approved": False, "verdict": "Failed to parse verification response"}
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse verification JSON: {e}")
            return {"approved": False, "verdict": f"JSON parse error: {e}"}
