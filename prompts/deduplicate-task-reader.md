---
status: created
created: "2026-03-11T22:00:00Z"
---
<summary>
- Duplicate frontmatter update code is eliminated
- File reading with encoding fallback is extracted into a reusable helper
- update_task_phase delegates to the generic frontmatter update method
</summary>

<objective>
Eliminate code duplication in `ObsidianTaskReader` by making `update_task_phase()` delegate to `_update_task_frontmatter()` and extracting the repeated UTF-8/latin-1 file reading pattern into a helper.
</objective>

<context>
Read CLAUDE.md for project conventions.
Read `src/task_orchestrator/obsidian/task_reader.py` — the `ObsidianTaskReader` class.

`update_task_phase()` (~lines 64-101) duplicates all file read/parse/write logic from `_update_task_frontmatter()` (~lines 103-149). The UTF-8/latin-1 fallback read pattern is copy-pasted in `update_task_phase`, `_update_task_frontmatter`, and `_parse_task`.
</context>

<requirements>
1. Add a private helper method `_read_file(self, file_path: Path) -> tuple[str, str]` that returns `(content, encoding)`:
   ```python
   def _read_file(self, file_path: Path) -> tuple[str, str]:
       """Read file with UTF-8/latin-1 fallback.

       Args:
           file_path: Path to file

       Returns:
           Tuple of (content, encoding used)
       """
       try:
           return file_path.read_text(encoding="utf-8"), "utf-8"
       except UnicodeDecodeError:
           return file_path.read_text(encoding="latin-1"), "latin-1"
   ```

2. Replace the try/except UTF-8/latin-1 blocks in `_update_task_frontmatter()` and `_parse_task()` with calls to `self._read_file(file_path)`.

3. Replace the body of `update_task_phase()` with a one-liner:
   ```python
   def update_task_phase(self, task_id: str, new_phase: str) -> None:
       """Update the phase field in task frontmatter."""
       self._update_task_frontmatter(task_id, {"phase": new_phase})
   ```

4. Keep `update_task_phase` in the `TaskReader` protocol (line 33-34) — callers still use it.
</requirements>

<constraints>
- Do NOT commit — dark-factory handles git
- Existing tests must still pass
- Do NOT change the TaskReader protocol interface
- Do NOT change the behavior of any public method
</constraints>

<verification>
Run `make precommit` -- must pass.
</verification>
