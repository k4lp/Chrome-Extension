# Plan: Expand Final Output Block With Datavault-Aware Rendering

## 1. Context Snapshot (Current Behavior & Bindings)
- **UI flow** – `gembrain/ui/widgets/chat_panel.py` wires the send button to `OrchestratorWorker`, then displays `OrchestratorResponse.reply_text` through `ConversationView`, which simply renders markdown (`conversation_view.py`). No extra data binding happens between the final reply string and the UI; whatever the orchestrator returns is what the user sees.
- **Reasoning pipeline** – `Orchestrator.run_user_message` (`gembrain/agents/orchestrator.py`) delegates to `IterativeReasoner.reason` when iterative mode is enabled. Each iteration (described in `iterative_reasoner.py`) gathers reasoning text, actions, and optional `final_output`.
- **Verification path** – After reasoning, `IterativeReasoner.verify` builds a verification context via `_build_verification_context`, which currently injects the raw `session.final_output` straight into the verification prompt that is sent to the verification LLM.
- **Action/Datavault bindings** – Both tool execution (`ActionExecutor` in `agents/tools.py`) and code-execution helpers (`GemBrainAPI` in `agents/code_api.py`) already use `DatavaultService` (`core/services.py`), which itself wraps `DatavaultRepository`/SQLAlchemy models. So the authoritative source of datavault content is already abstracted via this service layer.
- **Observed limitation** – The reasoning prompt (see the `final_output` instructions around lines 160-210 of `iterative_reasoner.py`) tells the LLM to “use references to datavault items,” but there is no mechanism to actually expand placeholders. The UI and the verification model both see the bare reference tokens, so large, rich final answers never materialize even when multiple datavault items contain full explanations.
- **Data integrity risk** – Because the final output string is pushed through multiple layers (iterative reasoner ➜ orchestrator ➜ verification ➜ UI ➜ persisted transcripts/logs), any change that mutates the string after the fact must respect the ordering. The user explicitly wants tags rendered **BEFORE** the text is displayed to humans or to the verification LLM. We must therefore hook into the data pipeline right after the LLM emits `final_output`, while still retaining the original text for traceability.

## 2. Problem Statement
We need the final output block to support inline “datavault tags” so a reasoning pass can stitch together multiple vault entries without duplicating all of their content inside the LLM response. Currently the system cannot resolve those tags, causing short replies. The fix must:
1. Define an explicit tag syntax (e.g., `[[datavault:123|Optional Title]]`).
2. Resolve each tag to the underlying vault content **before** the string is handed to the verification LLM **and BEFORE** the UI displays the answer.
3. Preserve a raw copy for logging/inspection to avoid losing what the model actually produced.
4. Fail gracefully when an ID is missing (do not crash the pipeline; instead leave a warning stub).

## 3. Proposed Enhancements (High-Level)
1. **Datavault tag rendering helper** – Introduce a dedicated utility (new module `gembrain/utils/datavault_tags.py`) that accepts the raw final output plus a `DatavaultService` and returns:
   - the rendered markdown string with vault contents inlined,
   - metadata describing which IDs were expanded (for audit + UI badge possibilities),
   - warnings for unresolved IDs or oversized payloads.
   This helper must be pure (no UI imports), leverage compiled regex to find tags, and optionally cap each rendered block (e.g., limit per-item characters with a configurable default) so a single tag cannot lock the UI.
2. **IterativeReasoner integration** – Update `ReasoningSession` (in `iterative_reasoner.py`) to carry both `raw_final_output` and `rendered_final_output` (or at least store the rendered string plus metadata). When `is_final` arrives, call the new rendering helper immediately and store the results; this guarantees ordering (render BEFORE verification/UI). Keep the previous `session.final_output` for backwards compatibility but document how we interpret it going forward.
3. **Verification context enhancement** – `_build_verification_context` must inject the rendered output (with tags expanded) while also appending a short appendix that lists which datavault items were injected, so the verification LLM understands the provenance of the text it is judging.
4. **Orchestrator reply adaptation** – `Orchestrator.run_user_message` should use the rendered final output for `reply_text`, with fallback rules (rendered ➜ raw ➜ verification summary) to ensure we never regress. Also propagate the metadata in `OrchestratorResponse` if we want to surface it later (optional but planned to keep debugging hooks).
5. **UI adjustments** – `ChatPanel._on_response_ready` ultimately just prints `reply_text`, so once step 4 is in place the UI automatically shows rendered text. Optionally add a future-friendly hook (e.g., ability to show “Datavault Sources” in TechnicalDetailsView) but that is outside this immediate plan unless needed downstream.
6. **Telemetry & manual verification** – Expand logging in the reasoner to confirm when rendering happens, how many tags/items were expanded, and how many characters were produced. Maintain a lightweight manual checklist (store sample items, reference them, verify UI output) so releases can still be vetted without automated tests.

## 4. Detailed Implementation Steps

### Step 1 – Define Tag Syntax & Utility Module
- **File targets:** create `gembrain/utils/datavault_tags.py`; optionally expose new helpers in `__init__.py` if needed by multiple callers.
- **Syntax proposal:** `[[datavault:ID|Optional Label]]`
  - `ID` is an integer (matches DB PK).
  - `Optional Label` lets the LLM hint at how the chunk should be titled when inlined; fallback to the vault item’s `notes` or “Datavault Item <ID>”.
- **Functions to implement:**
  1. `parse_datavault_tags(text: str) -> List[TagRef]` (simple dataclass storing start/end spans, id, label).
  2. `render_datavault_tags(text: str, datavault_service: DatavaultService, *, max_chars_per_item=5000, heading_level=3) -> RenderResult` where `RenderResult` includes:
     - `rendered_text`,
     - `resolved_items` (list of dicts with id, notes, length),
     - `warnings`.
  3. Helper to format the injected markdown block (include heading + horizontal rule, or some consistent delimiter) so the final output becomes legitimately “very big” but still readable.
- **Data binding:** the utility should *only* depend on `DatavaultService` (already exposes `get_item` etc.), so the pipeline remains easy to validate by passing in a fake service.

### Step 2 – Extend `ReasoningSession` + Rendering Hook
- **File:** `gembrain/agents/iterative_reasoner.py`
- **Add fields** to `ReasoningSession`: `raw_final_output: Optional[str] = None`, `rendered_final_output: Optional[str] = None`, `final_output_sources: List[Dict[str, Any]] = field(default_factory=list)`, `final_output_warnings: List[str] = field(default_factory=list)`. Keep `final_output` for backwards compatibility but document that it now mirrors `rendered_final_output`.
- **When `is_final` is detected (currently around line 550)**:
  1. Store the raw string immediately (`session.raw_final_output = iteration_data.get("final_output", "")`).
  2. Call `render_datavault_tags(...)` BEFORE setting `session.final_output`, so `session.final_output` always represents the rendered text that downstream consumers expect.
  3. Persist metadata/warnings on the session.
  4. Emit a `progress_callback` event (e.g., `{"type": "final_output_rendered", ...}`) if we want the UI to know that tag expansion occurred (optional but helpful for debugging).
- **Edge cases to handle:**
  - Missing datavault IDs (leave a clearly marked placeholder like `> [Missing datavault item 42]`).
  - Duplicate IDs (render each occurrence to keep the final answer faithful).
  - Render helper failures should never break the session; wrap call in try/except, log the error, and fall back to the raw string.

### Step 3 – Feed Rendered Output Into Verification
- **File:** same `iterative_reasoner.py`
- Update `_build_verification_context` to use `session.final_output` (rendered) but also append a section similar to:
  ```
  === DATA VAULT SOURCES (rendered BEFORE verification) ===
  - [ID 12] Notes: research-notes (chars: 4200)
  Warnings:
  - Missing datavault item 99
  ```
  This ensures the verification LLM knows what extra material was injected and that we honored the “BEFORE” requirement.
- Ensure that when verification falls back to summaries (e.g., no final output), we still note that tag rendering was skipped.

### Step 4 – Adjust Orchestrator Output & Metadata
- **File:** `gembrain/agents/orchestrator.py`
- After `session, approved = self.run_iterative_reasoning(...)`, change the reply selection logic:
  - Prefer `session.final_output` (rendered).
  - If empty, fall back to `session.raw_final_output`.
  - If still empty, fall back to verification summary (existing behavior).
- Extend `OrchestratorResponse` or attach a new attribute (e.g., `render_metadata`) so we can propagate `session.final_output_sources` / `final_output_warnings`. This allows future UI work without re-opening the reasoner.
- When auto-applying actions, keep existing flow untouched; rendering occurs before we reach this stage.

### Step 5 – (Optional) UI Telemetry & Future Hooks
- Since `reply_text` is now rendered, `ConversationView` automatically shows the expanded answer.
- Consider (for later) adding a pill or tooltip in `TechnicalDetailsView` to show which datavault items were used, using the new metadata if we pipe it through the response. Not in scope for the immediate change, but documenting it here ensures we remember the binding.

### Step 6 – Testing & Validation
- **Manual validation checklist:** capture a short runbook for QA: create a couple of datavault items (plain + truncated), reference them in a reasoning session, confirm the UI renders the expanded content, and note any warnings that appear.
  1. Rendering with no tags returns the same string.
  2. Rendering with one tag pulls correct content and wraps it with the heading.
  3. Rendering with `|Custom Title` overrides the heading.
  4. Missing IDs produce warnings + placeholder text.
  5. Large content is truncated according to `max_chars_per_item`.
- **Integration checks:** periodically run an end-to-end reasoning session manually with datavault tags to confirm `session.final_output` equals the rendered string and that verification context shows the same sources, documenting results in release notes.
- **Manual verification checklist:** run the UI, trigger a scenario where the LLM outputs tags (can be mocked by hardcoding a session), ensure:
  - Render happens before the verification call hits the LLM (check logs where we explicitly say “BEFORE verification”).
  - Conversation view shows the expanded markdown.
  - No regressions for users who never use datavault tags.

## 5. Data-Pipeline Safeguards
- The rendering helper only reads via `DatavaultService`, so database integrity stays within the existing repository boundaries—no direct SQL.
- All new fields on `ReasoningSession` are additive; serialization via `to_dict()` must be updated accordingly so persisted session logs (if any) stay consistent.
- Because rendering happens synchronously at the end of reasoning, there’s no risk that verification or UI sees unexpanded text; logs should clearly read something like: “Rendered datavault tags BEFORE verification – expanded 3 items (total 12,340 chars).”
- Fallbacks ensure that if rendering fails, the system continues to behave like today, preventing outages.

## 6. Open Questions / Follow-ups
1. Should tag syntax be configurable (settings) or hard-coded? (Plan assumes hard-coded for now; we can add config later.) – **Decision: make it configurable so users can adjust syntax as needed.**
2. Do we need to cache datavault lookups per session? (Probably not, but we can easily memoize inside the helper.) – **Decision: no caching for now; the helper can stay straightforward.**
3. Should the UI show which datavault items were used? (Not required for the current request but now possible once metadata is exposed.) – **Decision: yes, expose this in the UI now that metadata is available.**

This plan keeps the data bindings explicit, touches only the layers that actually own the final output, and guarantees tag expansion happens **BEFORE** verification and UI rendering, protecting the rest of the project from unintended regressions.
