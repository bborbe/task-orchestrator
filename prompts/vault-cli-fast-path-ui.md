<summary>
- Defer and complete actions show a brief success notification instead of a session dialog
- The task list refreshes automatically after a successful defer or complete
- No "Copy Command" or "Session ID" shown for instant operations
- Session dialog still appears for work-on-task (Claude sessions) as before
</summary>

<objective>
When the backend returns an empty session_id (vault-cli fast path), the UI should show a brief success toast and refresh the task list instead of the "Session Ready" modal dialog.
</objective>

<context>
Read CLAUDE.md for project conventions.
Read `src/task_orchestrator/static/app.js` — the `executeSlashCommand` function (~line 787) always calls `showModal` after a successful response, even when `session_id` is empty (vault-cli fast path).

The backend returns `session_id=""` for vault-cli fast-path operations (defer-task, complete-task). The frontend should detect this and show a lightweight success notification instead of the full session modal.
</context>

<requirements>
1. In `src/task_orchestrator/static/app.js`, in the success path of `executeSlashCommand` (~line 809-819), check if `data.session_id` is empty
2. If `session_id` is empty (vault-cli fast path):
   - Skip the `showModal` call
   - Show a brief success toast/notification (e.g. "Task deferred" or "Task completed") that auto-dismisses after 2 seconds
   - Trigger a task list refresh by calling the existing `loadTasks()` function (or equivalent)
3. If `session_id` is not empty (Claude session): keep existing `showModal` behavior unchanged
4. The toast should be styled consistently with the existing UI (dark theme, similar to other notifications if any exist)
5. Also skip showing the loading modal for vault-cli commands since they complete instantly — check the command type before showing the loading indicator (~line 770-785)
</requirements>

<constraints>
- Do NOT commit — dark-factory handles git
- Existing tests must still pass
- Do NOT change the work-on-task flow — it still uses Claude sessions and the full modal
- Keep changes minimal — only modify the frontend JavaScript
</constraints>

<verification>
Run `make test` -- must pass.
</verification>
