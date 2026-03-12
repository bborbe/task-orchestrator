---
status: prompted
tags:
    - dark-factory
    - spec
approved: "2026-03-12T12:42:04Z"
prompted: "2026-03-12T14:40:37Z"
branch: dark-factory/spec-001
---

## Summary

- Task files retain `claude_session_id` values after the corresponding Claude sessions are deleted from disk.
- Users attempting to resume such tasks get "No conversation found" errors.
- A background process will periodically detect and remove session IDs that no longer have a matching session file on disk.
- The cleanup runs once at startup and then on a fixed interval, covering all configured vaults.
- No new configuration, endpoints, or UI changes are required.

## Problem

Claude sessions are stored as `.jsonl` files under `~/.claude/projects/`. When a session is deleted or expires, the file disappears, but the `claude_session_id` field in the task's frontmatter remains. Any attempt to resume that task fails with a "No conversation found" error. There is no mechanism today to automatically detect or repair this inconsistency.

## Goal

After this work is done, stale `claude_session_id` values are automatically removed from task frontmatter. The system heals itself in the background without user intervention. Tasks with no valid backing session file will have their `claude_session_id` cleared, allowing users to start a fresh session on their next attempt.

## Non-goals

- No new HTTP endpoints or API surface.
- No UI changes or user-visible notifications.
- No changes to the configuration schema.
- No cleanup of the `.jsonl` files themselves.
- No handling of sessions that are valid but temporarily inaccessible.
- Tests are out of scope for the first pass.

## Desired Behavior

1. On application startup, a cleanup pass runs for all configured vaults before the service begins accepting normal workload.
2. Every 5 minutes after startup, another cleanup pass runs automatically.
3. For each vault, the system identifies all tasks that currently carry a non-empty `claude_session_id`.
4. For each such task, the system checks whether the corresponding `.jsonl` session file exists at the expected path derived from the vault path and session ID.
5. If the session file is absent, the system clears the `claude_session_id` field from the task using the existing `vault-cli task clear` command.
6. Each cleanup action (session ID cleared, task affected, vault name) is logged at an informational level.
7. A failure to process one task does not prevent processing of remaining tasks in the same pass.

## Constraints

- Must reuse the existing `vault-cli task clear` subprocess invocation pattern already present in the codebase — no new inter-process communication mechanisms.
- Must use the existing task-listing mechanism (ObsidianTaskReader) to enumerate tasks — no direct filesystem traversal of vault folders.
- The Claude project directory derivation rule is fixed: replace every `/` in `vault_path` with `-` and prepend `-`.
- The session file path is always `~/.claude/projects/<derived-project-dir>/<session_id>.jsonl`.
- The cleanup loop must not block the main event loop — it must run as a background async task.
- The existing startup sequence (watchers, API server) must remain unchanged; cleanup is additive.

## Failure Modes

| Trigger | Expected behavior | Recovery |
|---|---|---|
| `vault-cli task clear` exits non-zero | Log the error with task ID and vault; continue to next task | Operator inspects logs; will retry on next 5-minute pass |
| `vault-cli` binary not found or not executable | Log error at vault level; skip that vault for this pass | Operator fixes path in config; next pass succeeds |
| ObsidianTaskReader raises exception for a vault | Log error at vault level; skip that vault for this pass | Automatic retry on next pass |
| `~/.claude/projects/` directory does not exist | No session files found; all session IDs treated as stale and cleared | Expected on fresh installs; operator awareness needed |
| Application restarts mid-pass | Pass is abandoned; full pass starts again on next startup | Idempotent: clearing an already-cleared field is a no-op |

## Security / Abuse Cases

- The derived project directory path is constructed from `vault_path` in config, which is operator-controlled and not user-supplied at runtime. No path traversal risk from untrusted input.
- The session ID comes from task frontmatter written by the orchestrator itself. Validate that the value is a non-empty string and contains no path separators before constructing the file path.
- The `vault-cli task clear` subprocess receives `task_id` from the task reader. Ensure the task ID is passed as a discrete argument, not interpolated into a shell string, to prevent injection.
- The cleanup loop runs indefinitely; an exception escaping the per-vault guard would terminate the loop silently. The outer loop must catch all exceptions to keep the background task alive.

## Acceptance Criteria

- [ ] On startup, at least one cleanup pass completes before the 5-minute interval fires, and a log line confirms it.
- [ ] A task with a `claude_session_id` whose `.jsonl` file is absent has its session ID cleared after a pass.
- [ ] A task with a `claude_session_id` whose `.jsonl` file is present retains its session ID after a pass.
- [ ] A task with no `claude_session_id` is unaffected by a pass.
- [ ] An error clearing one task's session ID does not prevent other tasks in the same pass from being processed.
- [ ] The number of sessions cleared per pass is logged.

## Verification

```
make precommit
```

Manual smoke test:
1. Create a task with a fabricated `claude_session_id` (no matching `.jsonl` file).
2. Start the application and observe logs.
3. Confirm the `claude_session_id` field is absent from the task frontmatter within 30 seconds of startup.
4. Confirm a task with a real, present session file retains its ID.

## Do-Nothing Option

Without this work, users continue to encounter "No conversation found" errors whenever a session expires. They must manually open each task and clear the field. As the number of tasks and session turnovers grows, this becomes an increasing operational burden. The current approach is not acceptable for long-running deployments.
