"""Dependency injection factory."""

import asyncio
import logging
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from pathlib import Path

from claude_code_sdk import ClaudeCodeOptions, ClaudeSDKClient
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from task_orchestrator.claude.executor import ClaudeCodeExecutor, ClaudeExecutor
from task_orchestrator.config import Config, VaultConfig
from task_orchestrator.obsidian.task_reader import ObsidianTaskReader, TaskReader
from task_orchestrator.obsidian.task_watcher import TaskWatcher
from task_orchestrator.status_cache import StatusCache
from task_orchestrator.websocket.connection_manager import ConnectionManager

logger = logging.getLogger(__name__)

# Global config instance for dependency injection
_config: Config | None = None

# Global connection manager and watchers
_connection_manager: ConnectionManager | None = None
_watchers: dict[str, TaskWatcher] = {}
_status_cache: StatusCache | None = None


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


def get_status_cache() -> StatusCache:
    """Get or create StatusCache singleton."""
    global _status_cache
    if _status_cache is None:
        _status_cache = StatusCache()
    return _status_cache


def start_task_watchers() -> None:
    """Start file watchers for all configured vaults (21-24 folders)."""
    global _watchers
    config = get_config()
    connection_manager = get_connection_manager()
    cache = get_status_cache()

    # Get the running event loop to schedule coroutines from threads
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        logger.error("[Factory] No running event loop found")
        return

    # Watch ALL hierarchy folders (not just tasks)
    folders_to_watch = ["21 Themes", "22 Objectives", "23 Goals", "24 Tasks"]

    for vault in config.vaults:
        vault_path = Path(vault.vault_path)

        for folder in folders_to_watch:
            folder_path = vault_path / folder
            if not folder_path.exists():
                logger.warning(f"[Factory] Folder not found: {folder_path}")
                continue

            try:
                watcher = TaskWatcher(folder_path, vault.name)

                # Wire callback to invalidate cache AND broadcast
                def make_callback(vault_name: str) -> Callable[[str, str, str], None]:
                    def callback(event_type: str, item_id: str, vault_arg: str) -> None:
                        # Invalidate cache
                        cache.invalidate(vault_arg, item_id)

                        # Broadcast to UI clients
                        message = {"type": event_type, "task_id": item_id, "vault": vault_arg}
                        asyncio.run_coroutine_threadsafe(
                            connection_manager.broadcast(message), loop
                        )

                    return callback

                watcher.set_callback(make_callback(vault.name))
                watcher.start(background=True)

                # Use unique key per folder
                watcher_key = f"{vault.name}:{folder}"
                _watchers[watcher_key] = watcher
                logger.info(f"[Factory] Watching {folder} for {vault.name}")

            except Exception as e:
                logger.error(
                    f"[Factory] Failed to start watcher for {folder} in {vault.name}: {e}",
                    exc_info=True,
                )


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


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifecycle - startup and shutdown."""
    # Populate status cache before starting watchers
    logger.info("[Lifespan] Loading status cache...")
    cache = get_status_cache()
    config = get_config()
    for vault in config.vaults:
        vault_path = Path(vault.vault_path)
        cache.load_vault(vault.name, vault_path)

    logger.info("[Lifespan] Starting task watchers...")
    start_task_watchers()
    try:
        yield
    finally:
        logger.info("[Lifespan] Stopping task watchers...")
        stop_task_watchers()


def create_app() -> FastAPI:
    """Create FastAPI application (composition root)."""
    from task_orchestrator.api.tasks import router as tasks_router
    from task_orchestrator.api.websocket import router as ws_router

    app = FastAPI(
        title="TaskOrchestrator",
        description="Orchestrate Claude Code sessions from Obsidian tasks",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Mount API routes
    app.include_router(tasks_router, prefix="/api")
    app.include_router(ws_router)  # WebSocket at /ws

    # Mount static files (HTML/CSS/JS)
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

    return app
