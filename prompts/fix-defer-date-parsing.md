<summary>
- Defer date filtering no longer crashes when frontmatter contains a full datetime instead of date-only
- Both `2026-03-08` and `2026-03-08T21:35:32.742132+01:00` formats are accepted
- Existing date-only defer_date values continue to work unchanged
</summary>

<objective>
Fix ValueError in defer_date filtering when Obsidian frontmatter contains a full ISO datetime string instead of a date-only string. The `date.fromisoformat()` call crashes on datetime strings like `2026-03-08T21:35:32.742132+01:00`.
</objective>

<context>
Read CLAUDE.md for project conventions.
Read `src/task_orchestrator/api/tasks.py` before changing it.
</context>

<requirements>
1. In `src/task_orchestrator/api/tasks.py`, line ~141, the expression `date.fromisoformat(t.defer_date)` fails when `defer_date` contains a full datetime string
2. Import `datetime` from the `datetime` module (add to existing import on line 7)
3. Replace the inline `date.fromisoformat(t.defer_date)` with a helper that tries `date.fromisoformat()` first, and falls back to `datetime.fromisoformat().date()` on `ValueError`
4. Add a test in the appropriate test file that verifies both formats work: `"2026-03-08"` and `"2026-03-08T21:35:32.742132+01:00"`
</requirements>

<constraints>
- Do NOT commit — dark-factory handles git
- Existing tests must still pass
- Minimal change — only touch the defer_date parsing logic
</constraints>

<verification>
Run `make test` -- must pass.
</verification>
