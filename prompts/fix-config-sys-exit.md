---
status: created
created: "2026-03-11T22:00:00Z"
---
<summary>
- Config loading raises an exception instead of calling sys.exit, making it testable
- The main entry point catches the error and prints the user-friendly message
- Library code no longer has side effects (print + exit)
</summary>

<objective>
Replace `print()` + `sys.exit(1)` in `load_config()` with a proper exception so the function is testable and follows composition-root principles. The entry point handles user messaging.
</objective>

<context>
Read CLAUDE.md for project conventions.
Read `src/task_orchestrator/config.py` — the `load_config()` function.
Read `src/task_orchestrator/__main__.py` — the entry point that calls the factory.
</context>

<requirements>
1. In `config.py`, replace the `print()` + `sys.exit(1)` block in `load_config()` with:
   ```python
   raise FileNotFoundError(
       f"config.yaml not found at {config_path}\n"
       "\nCreate it by copying the example:\n"
       "  cp config.yaml.example config.yaml\n"
       "\nThen edit vault paths to match your system."
   )
   ```

2. Remove `import sys` from `config.py` (no longer needed — verify no other usage first).

3. In `__main__.py`, wrap the app startup in a try/except that catches `FileNotFoundError` and prints the message to stderr before exiting:
   ```python
   except FileNotFoundError as e:
       print(str(e), file=sys.stderr)
       sys.exit(1)
   ```
   Place this around the `create_app()` call or the `uvicorn.run()` call — whichever triggers `load_config()` first.

4. Add a test in `tests/test_api.py` (or a new `tests/test_config.py`) that verifies `load_config()` raises `FileNotFoundError` when the config file doesn't exist.
</requirements>

<constraints>
- Do NOT commit — dark-factory handles git
- Existing tests must still pass
- Do NOT change config.yaml format or any other config behavior
</constraints>

<verification>
Run `make precommit` -- must pass.
</verification>
