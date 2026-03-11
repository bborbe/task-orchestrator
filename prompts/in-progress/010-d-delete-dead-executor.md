---
status: approved
created: "2026-03-11T22:00:00Z"
queued: "2026-03-11T21:25:02Z"
---
<summary>
- The dead executor module is removed (replaced by SessionManager)
- Factory no longer exports unused get_executor function
- The ClaudeExecutor protocol and ClaudeCodeExecutor class are deleted
- No API or runtime behavior changes — executor was never called from any route
- Application starts and all tests pass after deletion
</summary>

<objective>
The dead `executor.py` module and its factory wiring are removed. `SessionManager` is the sole session management mechanism.
</objective>

<context>
Read CLAUDE.md for project conventions.
Read `src/task_orchestrator/claude/executor.py` — the dead module.
Read `src/task_orchestrator/factory.py` — imports and `get_executor()` function.

Verify before deleting: grep the `src/` and `tests/` directories for `get_executor`, `ClaudeCodeExecutor`, `ClaudeExecutor`. None should be called from API routes or tests.
</context>

<requirements>
1. Delete `src/task_orchestrator/claude/executor.py`.

2. In `factory.py`, remove:
   - The import: `from task_orchestrator.claude.executor import ClaudeCodeExecutor, ClaudeExecutor` (~line 13)
   - The function `get_executor()` (~lines 58-61)

3. Verify no test files import from `executor.py` or reference `get_executor`. If any do, remove those imports/references too.
</requirements>

<constraints>
- Do NOT commit — dark-factory handles git
- Existing tests must still pass
- Do NOT change session_manager.py or any API behavior
</constraints>

<verification>
Run `make precommit` -- must pass.
</verification>
