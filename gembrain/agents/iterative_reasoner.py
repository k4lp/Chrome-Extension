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
✓ GOOD: gb.vault_store("results", json.dumps(data))  # Store it!
✓ GOOD: gb.create_note("Analysis", summary)  # Create notes directly!
✓ GOOD: for item in items: gb.create_task(item)  # Create tasks in code!

Available in code as 'gb':
- gb.create_note(title, content, tags=[])
- gb.search_notes(query)
- gb.create_task(title, due_date=None, project_name=None)
- gb.search_tasks(query)
- gb.complete_task(task_id)
- gb.create_project(name, description, tags=[])
- gb.store_memory(key, content, importance=3)
- gb.get_memory(key)
- gb.vault_store(title, content, item_type="snippet")  # Store intermediate data!
- gb.vault_search(query)
- gb.vault_get(item_id)
- gb.log(message)

Example code:
```python
import json

# Analyze data
results = analyze_large_dataset(data)

# DON'T return it - store it!
gb.vault_store("analysis_results", json.dumps(results), "snippet")

# Create tasks from results
for task in results['todo_items']:
    gb.create_task(task['title'], task['due_date'])

# Create summary note
gb.create_note("Analysis Complete", summary_text, tags=["analysis"])

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
  "reasoning": "Breaking down the task into manageable steps",
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

**Subsequent iterations work through subtasks:**
```iteration
{
  "iteration": <number>,
  "current_subtask": <id>,
  "reasoning": "<reasoning for this step>",
  "observations": ["<observation 1>", ...],
  "next_actions": [
    {"type": "vault_store", "title": "step_X_results", "content": "..."},
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
  "reasoning": "<final reasoning>",
  "observations": ["All subtasks completed", ...],
  "final_output": "<complete answer with references to vault items>",
  "completion_reason": "All subtasks complete, results stored in vault",
  "is_final": true
}
```

═══════════════════════════════════════════════════════════════════════════════
COMPLETION CRITERIA (When to set is_final: true)
═══════════════════════════════════════════════════════════════════════════════

You MUST continue iterating UNTIL ALL of these are satisfied:

1. **Problem Fully Understood** - You have gathered all necessary context
2. **All Sub-tasks Addressed** - Every aspect of the query has been explored
3. **Data Collected** - All required information has been retrieved
4. **Actions Executed** - All necessary operations have been performed
5. **Solution Validated** - Your solution is complete, correct, and comprehensive
6. **Edge Cases Considered** - You've thought through potential issues
7. **Output is Actionable** - Your final output is clear and complete

DO NOT set is_final: true unless ALL criteria are met.

═══════════════════════════════════════════════════════════════════════════════
REASONING GUIDELINES
═══════════════════════════════════════════════════════════════════════════════

1. **Think Deeply** - Use Chain-of-Thought reasoning
2. **Be Systematic** - Break complex problems into steps
3. **Use Available Actions** - List notes, search data, execute code, create tasks
4. **Learn from Results** - Each iteration should build on previous results
5. **Self-Critique** - Question your assumptions
6. **Be Thorough** - Don't rush to completion

═══════════════════════════════════════════════════════════════════════════════
AVAILABLE ACTIONS
═══════════════════════════════════════════════════════════════════════════════

Query Actions: list_notes, search_notes, list_tasks, search_tasks, list_projects
Create Actions: create_note, add_task, create_project, update_memory, add_vault_item
Update Actions: update_note, update_task
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
4. The proposed final output

Your job: Decide if this work is acceptable or needs more iterations.

═══════════════════════════════════════════════════════════════════════════════
VERIFICATION CRITERIA (ALL must be satisfied)
═══════════════════════════════════════════════════════════════════════════════

1. **Query Fully Addressed** ✓
   - Does the output answer the user's question completely?
   - Are all explicit AND implicit requirements met?

2. **Reasoning Quality** ✓
   - Is the reasoning logical and coherent?
   - Are conclusions supported by evidence?
   - Were appropriate actions taken?

3. **Completeness** ✓
   - Were all sub-problems addressed?
   - Is the output actionable and clear?
   - Are edge cases considered?

4. **Correctness** ✓
   - Are facts accurate?
   - Are actions appropriate?
   - Is the solution valid?

5. **No Hallucinations** ✓
   - Are all claims backed by data?
   - No invented information?

6. **Proper Use of Tools** ✓
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
  "recommendation": "<what should happen next>"
}
```

IMPORTANT:
- Set approved: true ONLY if ALL criteria score >= 8/10
- Be STRICT - this is quality control
- If approved: false, explain exactly what's missing
- Minimum confidence for approval: 0.85
"""


class IterativeReasoner:
    """Iterative reasoning system with verification."""

    def __init__(
        self,
        gemini_client: GeminiClient,
        settings: Settings,
        max_iterations: int = 50,
    ):
        """Initialize iterative reasoner.

        Args:
            gemini_client: Gemini client for reasoning
            settings: Application settings
            max_iterations: Maximum iterations before forced stop
        """
        self.gemini_client = gemini_client
        self.settings = settings
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

            # Call progress callback if provided
            if progress_callback:
                progress_callback(f"🔄 Iteration {iteration_count}/{self.max_iterations}")

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

                # Create iteration object
                iteration = ReasoningIteration(
                    iteration_number=iteration_count,
                    reasoning=iteration_data.get("reasoning", ""),
                    observations=iteration_data.get("observations", []),
                    insights_gained=iteration_data.get("insights_gained", []),
                )
                logger.debug(f"📝 Created iteration object with {len(iteration.observations)} observations")

                # Execute actions if any
                if "next_actions" in iteration_data:
                    iteration.actions_taken = iteration_data["next_actions"]
                    logger.info(f"🎬 {len(iteration.actions_taken)} actions to execute")
                    # Action execution would happen here (integrate with ActionExecutor)
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
            logger.warning(f"⚠️ Forced stop after {self.max_iterations} iterations")

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

        # Add previous iterations
        if session.iterations:
            iterations_summary = "=== PREVIOUS ITERATIONS ===\n\n"
            for it in session.iterations:
                iterations_summary += f"Iteration {it.iteration_number}:\n"
                iterations_summary += f"Reasoning: {it.reasoning}\n"
                iterations_summary += f"Observations: {', '.join(it.observations)}\n"
                iterations_summary += f"Insights: {', '.join(it.insights_gained)}\n\n"

            context_blocks.append(iterations_summary)

        return context_blocks

    def _build_verification_context(self, session: ReasoningSession) -> str:
        """Build context for verification."""
        context = f"""
=== ORIGINAL QUERY ===
{session.user_query}

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

    def _parse_iteration_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse iteration response from model."""
        try:
            # Extract ```iteration block
            logger.debug("🔍 Searching for ```iteration block in response")
            match = re.search(r"```iteration\s*\n(.*?)\n```", response, re.DOTALL)
            if match:
                json_str = match.group(1)
                logger.debug(f"✅ Found ```iteration block (length: {len(json_str)} chars)")
                logger.debug(f"JSON string preview: {json_str[:200]}")
                parsed = json.loads(json_str)
                logger.debug(f"✅ Successfully parsed JSON with keys: {list(parsed.keys())}")
                return parsed
            else:
                logger.error("❌ No ```iteration block found in response")
                logger.error(f"Response sample (first 1000 chars): {response[:1000]}")
                return None
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse iteration JSON: {e}")
            logger.error(f"JSON string that failed: {json_str[:500] if 'json_str' in locals() else 'N/A'}")
            return None

    def _parse_verification_response(self, response: str) -> Dict[str, Any]:
        """Parse verification response from model."""
        try:
            # Extract ```verification block
            match = re.search(r"```verification\s*\n(.*?)\n```", response, re.DOTALL)
            if match:
                json_str = match.group(1)
                return json.loads(json_str)
            else:
                logger.error("No ```verification block found in response")
                return {"approved": False, "verdict": "Failed to parse verification response"}
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse verification JSON: {e}")
            return {"approved": False, "verdict": f"JSON parse error: {e}"}
