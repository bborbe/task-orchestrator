"""Dependency injection factory."""

import asyncio
import logging
from collections.abc import Callable
from pathlib import Path

from claude_code_sdk import ClaudeCodeOptions, ClaudeSDKClient
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from task_orchestrator.claude.executor import ClaudeCodeExecutor, ClaudeExecutor
from task_orchestrator.config import Config, VaultConfig
from task_orchestrator.obsidian.task_reader import ObsidianTaskReader, TaskReader
from task_orchestrator.obsidian.task_watcher import TaskWatcher
from task_orchestrator.websocket.connection_manager import ConnectionManager

logger = logging.getLogger(__name__)

# Global config instance for dependency injection
_config: Config | None = None

# Global connection manager and watchers
_connection_manager: ConnectionManager | None = None
_watchers: dict[str, TaskWatcher] = {}


def get_config() -> Config:
    """Get or create Config instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config


def get_task_reader_for_vault(vault_name: str) -> TaskReader:
    """Create task reader for specific vault."""
    config = get_config()
    vault = config.get_vault(vault_name)
    if not vault:
        raise ValueError(f"Unknown vault: {vault_name}")
    return ObsidianTaskReader(vault.vault_path, vault.tasks_folder)


def get_vault_config(vault_name: str) -> VaultConfig:
    """Get vault config by name."""
    config = get_config()
    vault = config.get_vault(vault_name)
    if not vault:
        raise ValueError(f"Unknown vault: {vault_name}")
    return vault


def get_executor() -> ClaudeExecutor:
    """Create ClaudeExecutor for dependency injection."""
    config = get_config()
    return ClaudeCodeExecutor(config.claude_cli)


def create_claude_client_factory() -> Callable[[], ClaudeSDKClient]:
    """Create a factory function for Claude SDK clients.

    Returns a callable that creates new ClaudeSDKClient instances.
    Each call returns a fresh client for use in async context managers.
    """

    def factory() -> ClaudeSDKClient:
        options = ClaudeCodeOptions(permission_mode="acceptEdits")
        return ClaudeSDKClient(options=options)

    return factory


def get_connection_manager() -> ConnectionManager:
    """Get or create ConnectionManager singleton."""
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
    return _connection_manager


def start_task_watchers() -> None:
    """Start file watchers for all configured vaults."""
    global _watchers
    config = get_config()
    connection_manager = get_connection_manager()

    # Get the running event loop to schedule coroutines from threads
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        logger.error("[Factory] No running event loop found")
        return

    for vault in config.vaults:
        try:
            reader = get_task_reader_for_vault(vault.name)
            watcher = TaskWatcher(reader.tasks_dir, vault.name)

            # Wire callback to broadcast via connection manager
            def make_callback(vault_name: str) -> Callable[[str, str, str], None]:
                def callback(event_type: str, task_id: str, vault_arg: str) -> None:
                    # Schedule async broadcast from thread using run_coroutine_threadsafe
                    message = {"type": event_type, "task_id": task_id, "vault": vault_arg}
                    asyncio.run_coroutine_threadsafe(connection_manager.broadcast(message), loop)

                return callback

            watcher.set_callback(make_callback(vault.name))
            watcher.start(background=True)
            _watchers[vault.name] = watcher
            logger.info(f"[Factory] Started watcher for vault: {vault.name}")

        except Exception as e:
            logger.error(f"[Factory] Failed to start watcher for {vault.name}: {e}", exc_info=True)


def stop_task_watchers() -> None:
    """Stop all running file watchers."""
    global _watchers
    for vault_name, watcher in _watchers.items():
        try:
            watcher.stop()
            logger.info(f"[Factory] Stopped watcher for vault: {vault_name}")
        except Exception as e:
            logger.error(f"[Factory] Failed to stop watcher for {vault_name}: {e}")
    _watchers.clear()


def create_app() -> FastAPI:
    """Create FastAPI application (composition root)."""
    from task_orchestrator.api.tasks import router as tasks_router
    from task_orchestrator.api.websocket import router as ws_router

    app = FastAPI(
        title="TaskOrchestrator",
        description="Orchestrate Claude Code sessions from Obsidian tasks",
        version="0.1.0",
    )

    # Mount API routes
    app.include_router(tasks_router, prefix="/api")
    app.include_router(ws_router)  # WebSocket at /ws

    # Mount static files (HTML/CSS/JS)
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

    return app
