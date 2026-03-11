---
status: created
created: "2026-03-11T22:00:00Z"
---
<summary>
- WebSocket broadcast no longer risks concurrent list mutation errors
- Failed send operations include full stack traces in logs for debugging
</summary>

<objective>
Fix a race condition in `ConnectionManager.broadcast()` where the `active_connections` list can be mutated by `connect()`/`disconnect()` while being iterated, and improve error logging.
</objective>

<context>
Read CLAUDE.md for project conventions.
Read `src/task_orchestrator/websocket/connection_manager.py` — the `ConnectionManager` class.

The `broadcast()` method is called via `asyncio.run_coroutine_threadsafe()` from file watcher threads (see `factory.py` ~line 128). While asyncio is single-threaded within the event loop, the list snapshot is still good practice for safety against mutations during iteration (e.g., dead connection cleanup within the same loop iteration).
</context>

<requirements>
1. In `broadcast()`, snapshot the connections list before iterating:
   ```python
   # Snapshot to avoid mutation during iteration
   connections = list(self.active_connections)
   for connection in connections:
   ```
   Update the `num_clients` log to use `len(connections)` instead of `len(self.active_connections)`.

2. Add `exc_info=True` to the `logger.warning` in `broadcast()` (~line 61):
   ```python
   logger.warning(f"[ConnectionManager] Failed to send to client: {e}", exc_info=True)
   ```

3. Add `exc_info=True` to the `logger.warning` in `send_personal()` (~line 78):
   ```python
   logger.warning(f"[ConnectionManager] Failed to send personal message: {e}", exc_info=True)
   ```
</requirements>

<constraints>
- Do NOT commit — dark-factory handles git
- Existing tests must still pass
- Do NOT change the connect/disconnect API
</constraints>

<verification>
Run `make precommit` -- must pass.
</verification>
