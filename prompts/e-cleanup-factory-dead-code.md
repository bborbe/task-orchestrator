---
status: created
created: "2026-03-11T22:00:00Z"
---
<summary>
- The unused client factory function is removed from the factory module
- Integration tests that called the factory are updated to create clients directly
- SDK imports that were only used by the dead factory are cleaned up
- Watcher shutdown errors now include full stack traces for debugging
- No runtime behavior changes — only test setup code changes
</summary>

<objective>
`create_claude_client_factory()` is removed from `factory.py` along with its now-unused imports, and integration tests are updated to construct clients directly. Watcher error logging includes stack traces.
</objective>

<context>
Read CLAUDE.md for project conventions.
Read `src/task_orchestrator/factory.py` — the factory module. `create_claude_client_factory()` is at ~line 64.
Read `tests/test_session_manager_integration.py` — imports and calls `create_claude_client_factory` at lines 11, 20, and 70.

The function is NOT called from any production code path, but IS used by two integration tests. Those tests must be updated before deletion.
</context>

<requirements>
1. In `tests/test_session_manager_integration.py`, replace the `create_claude_client_factory` import and usage. Instead of calling the factory, construct the client directly:
   ```python
   # OLD
   from task_orchestrator.factory import create_claude_client_factory
   factory = create_claude_client_factory()
   client = factory()

   # NEW
   from claude_code_sdk import ClaudeCodeOptions, ClaudeSDKClient
   options = ClaudeCodeOptions(permission_mode="acceptEdits")
   client = ClaudeSDKClient(options=options)
   ```
   Apply this at both test locations (~lines 20 and 70).

2. Delete the `create_claude_client_factory()` function from `factory.py` (~lines 64-75).

3. Remove the import `from claude_code_sdk import ClaudeCodeOptions, ClaudeSDKClient` from `factory.py` (~line 9) — but ONLY if these names are not used anywhere else in `factory.py` after deleting `create_claude_client_factory`.

4. In `stop_task_watchers()`, add `exc_info=True` to the error log (~line 160):
   ```python
   # OLD
   logger.error(f"[Factory] Failed to stop watcher for {vault_name}: {e}")
   # NEW
   logger.error(f"[Factory] Failed to stop watcher for {vault_name}: {e}", exc_info=True)
   ```
</requirements>

<constraints>
- Do NOT commit — dark-factory handles git
- Existing tests must still pass (after updating integration tests in req 1)
- Do NOT change any other factory functions or the lifespan handler
</constraints>

<verification>
Run `make precommit` -- must pass.
</verification>
