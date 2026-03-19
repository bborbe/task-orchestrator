"""Background cleanup for stale Claude session IDs."""

import asyncio
import logging
from pathlib import Path

from task_orchestrator.config import Config
from task_orchestrator.session_resolver import is_uuid
from task_orchestrator.vault_cli_client import VaultCLIClient

logger = logging.getLogger(__name__)

_CLEANUP_INTERVAL_SECONDS = 300


def derive_claude_project_dir(vault_path: str, session_project_dir: str = "") -> Path:
    """Return the Claude project directory for session file lookup.

    If session_project_dir is provided and non-empty, use it directly.
    Otherwise derive from vault_path using the standard convention.
    """
    if session_project_dir:
        return Path(session_project_dir).expanduser()
    derived = vault_path.replace("/", "-")
    return Path.home() / ".claude" / "projects" / derived


async def cleanup_stale_sessions(config: Config) -> int:
    """Clear stale claude_session_id values from tasks whose session file no longer exists.

    Returns the number of session IDs cleared across all vaults.
    """
    cleared = 0
    for vault in config.vaults:
        try:
            client = VaultCLIClient(vault.vault_cli_path, vault.name)
            tasks = await client.list_tasks(show_all=True)
            tasks_with_session = [t for t in tasks if t.claude_session_id]

            project_dir = derive_claude_project_dir(vault.vault_path, vault.session_project_dir)

            for task in tasks_with_session:
                session_id = task.claude_session_id
                assert session_id is not None  # narrowing for type checker

                if "/" in session_id or "\\" in session_id:
                    logger.warning(
                        "[Cleanup] Skipping task %s in vault %s: session_id contains invalid chars",
                        task.id,
                        vault.name,
                    )
                    continue

                if not is_uuid(session_id):
                    logger.info(
                        "[Cleanup] Clearing unresolved display-name session '%s'"
                        " from task %s in vault %s",
                        session_id,
                        task.id,
                        vault.name,
                    )
                else:
                    if task.assignee and task.assignee != config.current_user:
                        logger.info(
                            "[Cleanup] Clearing session %s from task %s: "
                            "assigned to %s, not current user %s",
                            session_id,
                            task.id,
                            task.assignee,
                            config.current_user,
                        )
                    else:
                        session_file = project_dir / f"{session_id}.jsonl"
                        if session_file.exists():
                            continue

                try:
                    vault_cli_args = [
                        vault.vault_cli_path,
                        "task",
                        "clear",
                        task.id,
                        "claude_session_id",
                        "--vault",
                        vault.name,
                    ]
                    proc = await asyncio.create_subprocess_exec(
                        *vault_cli_args,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    _stdout, stderr = await proc.communicate()
                    if proc.returncode != 0:
                        logger.error(
                            "[Cleanup] Failed to clear session for task %s in vault %s: %s",
                            task.id,
                            vault.name,
                            stderr.decode().strip(),
                        )
                    else:
                        logger.info(
                            "[Cleanup] Cleared stale session %s from task %s in vault %s",
                            session_id,
                            task.id,
                            vault.name,
                        )
                        cleared += 1
                except Exception as e:
                    logger.error(
                        "[Cleanup] Exception clearing session for task %s in vault %s: %s",
                        task.id,
                        vault.name,
                        e,
                        exc_info=True,
                    )

        except Exception as e:
            logger.error(
                "[Cleanup] Exception processing vault %s: %s",
                vault.name,
                e,
                exc_info=True,
            )

    logger.info("[Cleanup] Pass complete: cleared %d stale session(s)", cleared)
    return cleared


async def run_cleanup_loop(config: Config) -> None:
    """Run cleanup_stale_sessions once immediately, then every 300 seconds."""
    logger.info("[Cleanup] Starting cleanup loop")
    while True:
        try:
            await cleanup_stale_sessions(config)
        except asyncio.CancelledError:
            logger.info("[Cleanup] Cleanup loop cancelled")
            raise
        except Exception as e:
            logger.error("[Cleanup] Unexpected error in cleanup pass: %s", e, exc_info=True)
        try:
            await asyncio.sleep(_CLEANUP_INTERVAL_SECONDS)
        except asyncio.CancelledError:
            logger.info("[Cleanup] Cleanup loop cancelled during sleep")
            raise
