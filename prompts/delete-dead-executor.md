---
status: created
created: "2026-03-11T22:00:00Z"
---
<summary>
- Dead executor module is removed (replaced by session manager)
- Factory no longer exports unused executor functions
- No behavior changes — executor was not called from any API route
</summary>

<objective>
Delete the dead `executor.py` module and its factory wiring. The `SessionManager` replaced all executor functionality; `ClaudeCodeExecutor` and `get_executor()` are never called from any API endpoint.
</objective>

<context>
Read CLAUDE.md for project conventions.
Read `src/task_orchestrator/claude/executor.py` — the dead module.
Read `src/task_orchestrator/factory.py` — imports and `get_executor()` function.

Verify before deleting: grep the entire `src/` directory for `get_executor`, `ClaudeCodeExecutor`, `ClaudeExecutor`, and `create_session` (excluding session_manager.py). None should be called from API routes.
</context>

<requirements>
1. Delete `src/task_orchestrator/claude/executor.py`.

2. In `factory.py`, remove:
   - The import: `from task_orchestrator.claude.executor import ClaudeCodeExecutor, ClaudeExecutor`
   - The function `get_executor()` (~lines 58-61)

3. Check if any test file imports from `executor.py` or `get_executor`. If so, remove those tests too.
</requirements>

<constraints>
- Do NOT commit — dark-factory handles git
- Existing tests must still pass
- Do NOT change session_manager.py or any API behavior
</constraints>

<verification>
Run `make precommit` -- must pass.
</verification>
