"""Stale session cleaner for TaskOrchestrator."""

import asyncio
import logging
from collections.abc import Callable
from pathlib import Path

from task_orchestrator.config import Config, VaultConfig
from task_orchestrator.obsidian.task_reader import TaskReader

logger = logging.getLogger(__name__)


def _derive_project_dir(vault_path: str) -> str:
    """Derive the Claude project directory name from a vault path.

    Replaces every '/' with '-' and prepends '-'.
    Example: '/Users/foo/Obsidian/Personal' -> '-Users-foo-Obsidian-Personal'
    """
    return "-" + vault_path.replace("/", "-")


def _session_file_exists(vault_path: str, session_id: str) -> bool:
    """Return True if the .jsonl session file exists for the given session ID.

    Validates that session_id is a non-empty string with no path separators
    before constructing the path. Returns False for invalid IDs.
    """
    if not session_id or "/" in session_id or "\\" in session_id:
        return False
    project_dir = _derive_project_dir(vault_path)
    session_file = Path.home() / ".claude" / "projects" / project_dir / f"{session_id}.jsonl"
    return session_file.exists()


class StaleSessionCleaner:
    """Detects and clears stale claude_session_id values from task frontmatter."""

    def __init__(self, config: Config, task_reader_factory: Callable[[str], TaskReader]) -> None:
        """Initialize with application config and a task reader factory.

        Args:
            config: Application Config instance.
            task_reader_factory: Callable mapping vault name to a TaskReader.
        """
        self._config = config
        self._task_reader_factory = task_reader_factory

    async def _clean_vault(self, vault: VaultConfig) -> int:
        """Clear stale session IDs for all tasks in the given vault.

        Args:
            vault: The vault configuration to process.

        Returns:
            Number of stale session IDs cleared.

        Raises:
            Exception: Re-raises any exception after logging it.
        """
        try:
            tasks = self._task_reader_factory(vault.name).list_tasks()
            cleared = 0

            for task in tasks:
                if not task.claude_session_id:
                    continue

                if _session_file_exists(vault.vault_path, task.claude_session_id):
                    continue

                vault_cli_args = [
                    vault.vault_cli_path,
                    "task",
                    "clear",
                    task.id,
                    "--vault",
                    vault.name.lower(),
                ]
                proc = await asyncio.create_subprocess_exec(
                    *vault_cli_args,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                _, stderr = await proc.communicate()

                if proc.returncode != 0:
                    logger.error(
                        "Failed to clear stale session for task %s in vault %s: %s",
                        task.id,
                        vault.name,
                        stderr.decode(),
                    )
                    continue

                logger.info(
                    "Cleared stale session ID for task %s in vault %s",
                    task.id,
                    vault.name,
                )
                cleared += 1

            return cleared
        except Exception:
            logger.error(
                "Error cleaning vault %s",
                vault.name,
                exc_info=True,
            )
            raise

    async def run_once(self) -> None:
        """Run one pass of stale session cleanup across all configured vaults."""
        for vault in self._config.vaults:
            try:
                count = await self._clean_vault(vault)
                logger.info(
                    "Stale session cleanup complete for vault %s: %d session(s) cleared",
                    vault.name,
                    count,
                )
            except Exception:
                logger.error(
                    "Stale session cleanup failed for vault %s",
                    vault.name,
                    exc_info=True,
                )

    async def run_loop(self) -> None:
        """Run stale session cleanup immediately then every 5 minutes."""
        await self.run_once()
        try:
            while True:
                await asyncio.sleep(5 * 60)  # 5 minutes
                try:
                    await self.run_once()
                except Exception:
                    logger.error("Unexpected error in stale session cleanup loop", exc_info=True)
        except asyncio.CancelledError:
            raise
