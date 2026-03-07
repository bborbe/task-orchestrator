<summary>
- Defer and complete task actions now execute instantly via vault-cli instead of slow Claude Code sessions
- The UI buttons for defer-task and complete-task call vault-cli subprocess directly
- Work-on-task still uses Claude Code sessions as before
- Task list auto-refreshes after defer/complete via WebSocket notification
</summary>

<objective>
Replace the Claude Code session path for defer-task and complete-task with direct vault-cli subprocess calls. These are simple frontmatter updates that don't need an AI session — vault-cli handles them in milliseconds.
</objective>

<context>
Read CLAUDE.md for project conventions.
Read `src/task_orchestrator/api/tasks.py` — the `execute_command` endpoint (line ~257) currently routes all commands through Claude Code sessions.
Read `src/task_orchestrator/config.py` — check how vault config is structured.
The vault-cli binary is at `/Users/bborbe/Documents/workspaces/vault-cli/bin/vault-cli` (development) or just `vault-cli` if on PATH.

vault-cli command signatures:
- `vault-cli task defer <task-name> <date> --vault <vault-name>` — date is ISO format like `2026-03-09` or relative like `+1d`
- `vault-cli task complete <task-name> --vault <vault-name>`

Both commands accept `--vault <name>` to specify which vault to operate on.
</context>

<requirements>
1. In `src/task_orchestrator/api/tasks.py`, in the `execute_command` endpoint (~line 257), add a fast path for `defer-task` and `complete-task` that calls vault-cli via `asyncio.create_subprocess_exec` instead of going through `_session_manager.send_prompt`
2. For `defer-task`: run `vault-cli task defer <task-name> <tomorrow-date> --vault <vault-name>` where tomorrow is computed as `(date.today() + timedelta(days=1)).isoformat()` (matching current behavior at line ~297)
3. For `complete-task`: run `vault-cli task complete <task-name> --vault <vault-name>`
4. The vault name comes from the vault config (the key used in the vaults dict in config.yaml, e.g. "Personal")
5. On success (return code 0), return a `SessionResponse` with `session_id=""`, `command=<the vault-cli command that was run>`, `response=<stdout from vault-cli>`
6. On failure (return code != 0), raise `HTTPException(status_code=500, detail=stderr)`
7. After successful vault-cli execution, trigger a WebSocket broadcast so the UI refreshes the task list. Use the existing `ConnectionManager` to broadcast a `{"type": "task_updated", "task_id": task_id}` message
8. Add a config field `vault_cli_path` to `VaultConfig` with default `"vault-cli"` so the binary path is configurable
9. Add tests for the new fast path — mock the subprocess call and verify correct command construction for both defer and complete
</requirements>

<constraints>
- Do NOT commit — dark-factory handles git
- Existing tests must still pass
- Do NOT change the work-on-task or create-task paths — those still use Claude Code
- The vault-cli binary path should be configurable, not hardcoded
</constraints>

<verification>
Run `make test` -- must pass.
</verification>
