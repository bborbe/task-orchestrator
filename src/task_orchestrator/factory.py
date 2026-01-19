"""Dependency injection factory."""

from collections.abc import Callable
from pathlib import Path

from claude_code_sdk import ClaudeCodeOptions, ClaudeSDKClient
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from task_orchestrator.claude.executor import ClaudeCodeExecutor, ClaudeExecutor
from task_orchestrator.config import Config, VaultConfig
from task_orchestrator.obsidian.task_reader import ObsidianTaskReader, TaskReader

# Global config instance for dependency injection
_config: Config | None = None


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


def create_app() -> FastAPI:
    """Create FastAPI application (composition root)."""
    from task_orchestrator.api.tasks import router

    app = FastAPI(
        title="TaskOrchestrator",
        description="Orchestrate Claude Code sessions from Obsidian tasks",
        version="0.1.0",
    )

    # Mount API routes
    app.include_router(router, prefix="/api")

    # Mount static files (HTML/CSS/JS)
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

    return app
