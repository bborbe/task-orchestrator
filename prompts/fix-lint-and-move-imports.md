---
status: created
created: "2026-03-11T22:00:00Z"
---
<summary>
- Lint error (unused variable) is fixed so precommit passes
- All function-body imports are moved to module level for consistency and performance
- Duplicate import is removed
</summary>

<objective>
Fix the RUF059 lint error and move all function-body imports to module level in tasks.py so that `make precommit` passes cleanly.
</objective>

<context>
Read CLAUDE.md for project conventions.
Read `src/task_orchestrator/api/tasks.py` — the file with all issues.
</context>

<requirements>
1. In `update_task_phase()` (~line 467), rename `stdout` to `_stdout` in the tuple unpacking:
   ```python
   # OLD
   stdout, stderr = await proc.communicate()
   # NEW
   _stdout, stderr = await proc.communicate()
   ```

2. Move `import json` and `import re` from inside `execute_slash_command()` (~line 376-377) to module-level imports at the top of the file. Note: `re` may already be imported at module level — if so, just remove the inner import.

3. Move `from pathlib import Path` from inside `reload_cache()` (~line 524) to module-level imports.

4. In `reload_cache()` (~line 526), remove the inner `from task_orchestrator.factory import get_config, get_status_cache`. `get_config` is already imported at module level (line 16-20). `get_status_cache` should be added to the existing module-level import from `task_orchestrator.factory`.

5. In `list_tasks()` (~line 163), remove the inner `from task_orchestrator.factory import get_status_cache`. It will now be available from the module-level import added in step 4.
</requirements>

<constraints>
- Do NOT commit — dark-factory handles git
- Existing tests must still pass
- Do NOT change any behavior — imports only
</constraints>

<verification>
Run `make precommit` -- must pass.
</verification>
