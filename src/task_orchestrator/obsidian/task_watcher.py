"""File system watcher for task directories."""

import logging
import time
from collections.abc import Callable
from pathlib import Path
from threading import Thread

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.api import BaseObserver

logger = logging.getLogger(__name__)


class TaskWatcher:
    """Watches task directory for file changes and triggers callbacks."""

    def __init__(self, tasks_dir: Path, vault_name: str):
        """Initialize watcher for a task directory.

        Args:
            tasks_dir: Path to the tasks folder (e.g., /vault/24 Tasks)
            vault_name: Name of the vault (for callback context)
        """
        self.tasks_dir = tasks_dir
        self.vault_name = vault_name
        self._observer: BaseObserver | None = None
        self._thread: Thread | None = None
        self._callback: Callable[[str, str, str], None] | None = None

    def set_callback(self, callback: Callable[[str, str, str], None]) -> None:
        """Set callback for file system events.

        Args:
            callback: Function(event_type, task_id, vault_name) called on events
        """
        self._callback = callback

    def start(self, background: bool = True) -> None:
        """Start watching the task directory.

        Args:
            background: Run in background thread (daemon mode)
        """
        handler = _TaskEventHandler(self.vault_name, self._callback)
        self._observer = Observer()
        self._observer.schedule(handler, str(self.tasks_dir), recursive=True)
        logger.info(f"[TaskWatcher] Watching {self.tasks_dir} (vault: {self.vault_name})")
        self._observer.start()

        if background:
            self._thread = Thread(target=self._run_loop, daemon=True)
            self._thread.start()
        else:
            self._run_loop()

    def _run_loop(self) -> None:
        """Keep observer running until stopped."""
        try:
            while self._observer and self._observer.is_alive():
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self) -> None:
        """Stop watching and clean up resources."""
        if self._observer:
            logger.info(f"[TaskWatcher] Stopping watcher for {self.vault_name}")
            self._observer.stop()
            self._observer.join()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)


class _TaskEventHandler(FileSystemEventHandler):
    """Internal handler for task file system events."""

    def __init__(self, vault_name: str, callback: Callable[[str, str, str], None] | None):
        """Initialize event handler.

        Args:
            vault_name: Name of the vault
            callback: Function to call on events
        """
        self.vault_name = vault_name
        self.callback = callback

    def _extract_task_id(self, file_path: str) -> str | None:
        """Extract task ID from file path.

        Args:
            file_path: Full path to task file

        Returns:
            Task ID (filename without .md) or None if not a task file
        """
        path = Path(file_path)
        if path.suffix == ".md":
            return path.stem
        return None

    def _handle_event(self, event_type: str, event: FileSystemEvent) -> None:
        """Handle file system event and trigger callback.

        Args:
            event_type: Type of event (modified, created, deleted, moved)
            event: File system event
        """
        if event.is_directory:
            return

        # Convert bytes to str if needed
        src_path = event.src_path
        if isinstance(src_path, bytes):
            src_path = src_path.decode("utf-8")

        task_id = self._extract_task_id(src_path)
        if not task_id:
            return

        logger.debug(f"[TaskEventHandler] {event_type}: {task_id} (vault: {self.vault_name})")

        if self.callback:
            try:
                self.callback(event_type, task_id, self.vault_name)
            except Exception as e:
                logger.error(f"[TaskEventHandler] Callback error: {e}", exc_info=True)

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification events."""
        self._handle_event("modified", event)

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation events."""
        self._handle_event("created", event)

    def on_deleted(self, event: FileSystemEvent) -> None:
        """Handle file deletion events."""
        self._handle_event("deleted", event)

    def on_moved(self, event: FileSystemEvent) -> None:
        """Handle file move/rename events."""
        self._handle_event("moved", event)
