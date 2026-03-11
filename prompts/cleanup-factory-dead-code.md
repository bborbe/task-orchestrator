---
status: created
created: "2026-03-11T22:00:00Z"
---
<summary>
- Dead client factory function is removed from factory module
- Unused SDK imports are cleaned up
- Watcher shutdown errors now include full stack traces
</summary>

<objective>
Remove the dead `create_claude_client_factory()` function from `factory.py`, clean up its unused imports, and improve error logging in `stop_task_watchers()`.
</objective>

<context>
Read CLAUDE.md for project conventions.
Read `src/task_orchestrator/factory.py` — the factory module.

`create_claude_client_factory()` (~line 64) is never called from anywhere. It imports `ClaudeSDKClient` and `ClaudeCodeOptions` from `claude_code_sdk` — verify if these imports are used elsewhere in `factory.py` before removing.
</context>

<requirements>
1. Delete the `create_claude_client_factory()` function (~lines 64-75).

2. Remove the import `from claude_code_sdk import ClaudeCodeOptions, ClaudeSDKClient` (~line 9) — but ONLY if these names are not used elsewhere in `factory.py`. After removing `create_claude_client_factory`, they should be unused.

3. In `stop_task_watchers()`, add `exc_info=True` to the error log (~line 160):
   ```python
   logger.error(f"[Factory] Failed to stop watcher for {vault_name}: {e}", exc_info=True)
   ```
</requirements>

<constraints>
- Do NOT commit — dark-factory handles git
- Existing tests must still pass
- Do NOT change any other factory functions or the lifespan handler
</constraints>

<verification>
Run `make precommit` -- must pass.
</verification>
