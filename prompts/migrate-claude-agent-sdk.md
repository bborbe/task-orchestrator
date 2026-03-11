---
status: created
created: "2026-03-11T22:00:00Z"
---
<summary>
- Project migrates from deprecated claude-code-sdk to claude-agent-sdk
- Direct __aenter__/__aexit__ calls are replaced with safer patterns
- Model references use explicit model IDs instead of short aliases
</summary>

<objective>
Migrate from the deprecated `claude-code-sdk` package to `claude-agent-sdk`. The API is nearly identical — the main change is `ClaudeCodeOptions` → `ClaudeAgentOptions` and the package import path.
</objective>

<context>
Read CLAUDE.md for project conventions.
Read `pyproject.toml` — dependency declaration (~line 12).
Read `src/task_orchestrator/claude/session_manager.py` — all SDK usage.
Read `src/task_orchestrator/factory.py` — SDK imports (may already be cleaned up by prior prompts; if no SDK imports remain, skip factory.py).

Migration mapping:
- Package: `claude-code-sdk` → `claude-agent-sdk`
- Import: `claude_code_sdk` → `claude_agent_sdk`
- `ClaudeCodeOptions` → `ClaudeAgentOptions`
- `ClaudeSDKClient` → `ClaudeSDKClient` (unchanged)
- `AssistantMessage`, `SystemMessage`, `TextBlock` → unchanged
</context>

<requirements>
1. In `pyproject.toml`, replace the dependency:
   ```toml
   # OLD
   "claude-code-sdk>=0.0.25",
   # NEW
   "claude-agent-sdk>=0.1.0",
   ```

2. In `session_manager.py`, update all imports:
   ```python
   # OLD
   from claude_code_sdk import ClaudeCodeOptions, ClaudeSDKClient
   from claude_code_sdk import AssistantMessage, SystemMessage
   from claude_code_sdk import AssistantMessage, SystemMessage, TextBlock
   # NEW
   from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
   from claude_agent_sdk import AssistantMessage, SystemMessage
   from claude_agent_sdk import AssistantMessage, SystemMessage, TextBlock
   ```
   Note: some imports are inside method bodies (`start_session` ~line 138, `send_prompt` ~line 227). If a prior prompt moved them to module level, update there instead.

3. Replace all `ClaudeCodeOptions` with `ClaudeAgentOptions` in `session_manager.py`:
   - In `start_session()` (~line 140-144)
   - In `send_prompt()` (~line 229-232)

4. Replace model short alias `"sonnet"` with explicit model ID `"claude-sonnet-4-5"` in both locations:
   - `start_session()`: `ClaudeAgentOptions(model="claude-sonnet-4-5", ...)`
   - `send_prompt()`: `ClaudeAgentOptions(model="claude-sonnet-4-5", ...)`

5. In `start_session()`, replace direct `__aenter__`/`__aexit__` with `contextlib.AsyncExitStack`:
   ```python
   from contextlib import AsyncExitStack

   # In start_session():
   stack = AsyncExitStack()
   client = ClaudeSDKClient(options=options)
   await stack.enter_async_context(client)

   # Instead of manual __aexit__ in except block:
   except Exception:
       await stack.aclose()
       raise
   ```
   Pass `stack` to `_consume_session_messages` so the background task can call `await stack.aclose()` in its `finally` block instead of `await client.__aexit__(None, None, None)`.

6. Update `_consume_session_messages` signature to accept `stack: AsyncExitStack` instead of relying on direct `client.__aexit__()`. In the `finally` block:
   ```python
   finally:
       await stack.aclose()
   ```

7. Update `Session` class if it still exists and uses `__aenter__`/`__aexit__` — replace with the same `AsyncExitStack` pattern or remove the class if unused.

8. In `factory.py`, if any `claude_code_sdk` imports remain (from `create_claude_client_factory` or others), update them to `claude_agent_sdk`. If prior prompts already removed all SDK imports from factory.py, skip this step.

9. Run `uv sync --all-extras` to install the new dependency.
</requirements>

<constraints>
- Do NOT commit — dark-factory handles git
- Existing tests must still pass
- Do NOT change the session lifecycle behavior (start_session must still return session_id quickly and consume messages in background)
- Do NOT change the API endpoints or response models
</constraints>

<verification>
Run `make precommit` -- must pass.
</verification>
