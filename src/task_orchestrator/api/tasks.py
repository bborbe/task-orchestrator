"""Task API endpoints."""

# FastAPI Depends pattern is safe in function signatures

import asyncio
import logging
from datetime import date, timedelta
from typing import TYPE_CHECKING, Annotated
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from task_orchestrator.api.models import SessionResponse, Task, TaskResponse
from task_orchestrator.config import VaultConfig
from task_orchestrator.factory import (
    get_config,
    get_task_reader_for_vault,
    get_vault_config,
)

if TYPE_CHECKING:
    from task_orchestrator.claude.session_manager import SessionManager

logger = logging.getLogger(__name__)

router = APIRouter()

# Global session manager (initialized in main)
_session_manager: "SessionManager | None" = None


def set_session_manager(manager: "SessionManager") -> None:
    """Set global session manager."""
    global _session_manager
    _session_manager = manager


class VaultResponse(BaseModel):
    """API response model for vault."""

    name: str
    vault_path: str
    tasks_folder: str
    claude_script: str


class UpdatePhaseRequest(BaseModel):
    """Request model for updating task phase."""

    phase: str


class ExecuteCommandRequest(BaseModel):
    """Request model for executing slash command."""

    command: str


@router.get("/vaults", response_model=list[VaultResponse])
async def list_vaults() -> list[VaultResponse]:
    """List all configured vaults.

    Returns:
        List of available vaults
    """
    config = get_config()
    return [
        VaultResponse(
            name=vault.name,
            vault_path=vault.vault_path,
            tasks_folder=vault.tasks_folder,
            claude_script=vault.claude_script,
        )
        for vault in config.vaults
    ]


@router.get("/tasks", response_model=list[TaskResponse])
async def list_tasks(
    vault: Annotated[list[str] | None, Query()] = None,
    status: str | None = None,
    phase: str | None = None,
    assignee: str | None = None,
) -> list[TaskResponse]:
    """List tasks from Obsidian vault(s).

    Args:
        vault: Vault name(s) to read from. If empty/None, reads from all vaults.
        status: Comma-separated list of statuses to filter (e.g. "in_progress,todo")
        phase: Comma-separated list of phases to filter (e.g. "planning,implementation")
        assignee: Filter by assignee name

    Returns:
        List of tasks matching the filter
    """
    # If no vault specified, get all vaults
    config = get_config()
    vault_names = [v.name for v in config.vaults] if not vault or len(vault) == 0 else vault

    # Parse status filter
    status_filter: list[str] | None = None
    if status:
        status_filter = [s.strip() for s in status.split(",")]

    # Parse phase filter
    phase_filter: list[str] | None = None
    if phase:
        phase_filter = [s.strip() for s in phase.split(",")]

    # Collect tasks from all specified vaults
    all_tasks: list[TaskResponse] = []
    for vault_name in vault_names:
        try:
            reader = get_task_reader_for_vault(vault_name)
            vault_config = get_vault_config(vault_name)
        except ValueError:
            # Skip invalid vaults
            continue

        # Get tasks
        tasks = reader.list_tasks(status_filter=status_filter)

        # Filter by phase if specified (tasks with None/invalid phase default to todo)
        if phase_filter:
            valid_phases = ["todo", "planning", "in_progress", "ai_review", "human_review", "done"]
            tasks = [
                t
                for t in tasks
                if (t.phase in valid_phases and t.phase in phase_filter)
                or (t.phase not in valid_phases and "todo" in phase_filter)
            ]

        # Filter by assignee if specified
        if assignee:
            tasks = [t for t in tasks if t.assignee == assignee]

        # Filter out deferred tasks (defer_date in future)
        today = date.today()
        tasks = [
            t for t in tasks if t.defer_date is None or date.fromisoformat(t.defer_date) <= today
        ]

        # Filter out blocked tasks (use cache for fast lookup)
        from task_orchestrator.factory import get_status_cache

        cache = get_status_cache()
        unblocked_tasks = []

        for task in tasks:
            if not task.blocked_by:
                # No blockers, include task
                unblocked_tasks.append(task)
                continue

            # Check if all blockers are completed
            has_uncompleted_blocker = False
            for blocker_wikilink in task.blocked_by:
                # Extract item name from wikilink [[Item Name]]
                blocker_name = blocker_wikilink.strip("[]").strip()

                # Fast cache lookup (O(1) dict access, no disk I/O)
                blocker_status = cache.get_status(vault_config.name, blocker_name)

                # If not found in cache, assume deleted/completed - don't block
                if blocker_status is None:
                    continue

                # Hide only if blocker exists and is NOT completed
                if blocker_status != "completed":
                    has_uncompleted_blocker = True
                    break

            if not has_uncompleted_blocker:
                # All blockers completed (or not found), include task
                unblocked_tasks.append(task)

        tasks = unblocked_tasks

        # Convert to response models
        all_tasks.extend([_task_to_response(task, vault_config) for task in tasks])

    return all_tasks


@router.post("/tasks/{task_id}/run", response_model=SessionResponse)
async def run_task(
    vault: str,
    task_id: str,
) -> SessionResponse:
    """Create a Claude Code session for the given task.

    Args:
        vault: Vault name
        task_id: Task ID (filename without .md)

    Returns:
        Session information with command to execute

    Raises:
        HTTPException: If task not found or session creation fails
    """
    logger.info(f"run_task called: vault={vault}, task_id={task_id}")

    if not _session_manager:
        logger.error("Session manager not initialized!")
        raise HTTPException(status_code=500, detail="Session manager not initialized")

    try:
        reader = get_task_reader_for_vault(vault)
        vault_config = get_vault_config(vault)

        # Read task
        task = reader.read_task(task_id)

        # Build relative task file path (relative to vault)
        task_file_path = f"{vault_config.tasks_folder}/{task.id}.md"

        # Send /work-on-task prompt and get session_id from Claude
        # Set cwd to vault path so relative paths work
        prompt = f'/work-on-task "{task_file_path}"'
        logger.info(f"Creating session for task {task_id}, cwd: {vault_config.vault_path}")

        session_id, response = await _session_manager.send_prompt(
            prompt, cwd=vault_config.vault_path
        )
        logger.info(f"Session {session_id} created, response length: {len(response)} chars")

        # Save session_id to task frontmatter
        try:
            await asyncio.to_thread(reader.update_task_session_id, task_id, session_id)
            logger.info(f"Saved session_id to task frontmatter: {task_id}")
        except Exception as save_error:
            logger.error(f"Failed to save session_id to frontmatter: {save_error}")
            # Continue anyway - user can still use the session, just won't persist

        # Build command: use vault-specific script from config (handles cd internally)
        command = f"{vault_config.claude_script} --resume {session_id}"

        logger.info(f"Returning session response: session_id={session_id}, command={command}")

        return SessionResponse(
            session_id=session_id,
            command=command,
            working_dir=vault_config.vault_path,
            task_title=task.title,
        )

    except FileNotFoundError as e:
        logger.error(f"Task not found: {e}")
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.exception(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/tasks/{task_id}/execute-command", response_model=SessionResponse)
async def execute_slash_command(
    vault: str,
    task_id: str,
    request: ExecuteCommandRequest,
) -> SessionResponse:
    """Execute slash command in existing or new Claude session.

    Args:
        vault: Vault name
        task_id: Task ID
        request: Command to execute (e.g., "complete-task", "defer-task")

    Returns:
        Session information with resume command
    """
    logger.info(
        f"execute_slash_command: vault={vault}, task_id={task_id}, command={request.command}"
    )

    if not _session_manager:
        raise HTTPException(status_code=500, detail="Session manager not initialized")

    try:
        reader = get_task_reader_for_vault(vault)
        vault_config = get_vault_config(vault)

        # Read task
        task = reader.read_task(task_id)

        # Build task file path
        task_file_path = f"{vault_config.tasks_folder}/{task.id}.md"

        # Check if task has existing session
        existing_session_id = task.claude_session_id

        # Send slash command with --tool flag for machine-readable output
        # Commands with --tool return {"success": true/false, ...}
        if request.command == "defer-task":
            tomorrow = (date.today() + timedelta(days=1)).isoformat()
            prompt = f'/{request.command} "{task_file_path}" {tomorrow} --tool'
        elif request.command == "complete-task" or request.command == "create-task":
            prompt = f'/{request.command} "{task_file_path}" --tool'
        else:
            prompt = f'/{request.command} "{task_file_path}"'

        if existing_session_id:
            logger.info(f"Resuming existing session: {existing_session_id} with command: {prompt}")
        else:
            logger.info(f"Creating new session with command: {prompt}")

        # Send prompt to Claude
        session_id, response = await _session_manager.send_prompt(
            prompt, cwd=vault_config.vault_path
        )

        # Parse response for success/failure
        import json
        import re

        success = None
        error_message = None

        # Try to extract JSON from response
        json_match = re.search(r'\{[^}]*"success"[^}]*\}', response)
        if json_match:
            try:
                result = json.loads(json_match.group())
                success = result.get("success", None)
                error_message = result.get("error", None)
                logger.info(f"Parsed result: success={success}, error={error_message}")
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON from response: {json_match.group()}")

        # Set phase to human_review if command failed
        if success is False:
            try:
                reader.update_task_phase(task_id, "human_review")
                logger.info(f"Set phase to human_review for task {task_id} due to command failure")
            except Exception as phase_error:
                logger.error(f"Failed to set phase to human_review: {phase_error}")

        # Save session_id if new
        if not existing_session_id:
            try:
                reader.update_task_session_id(task_id, session_id)
                logger.info(f"Saved new session_id: {session_id}")
            except Exception as save_error:
                logger.error(f"Failed to save session_id: {save_error}")

        # Build resume command
        command = f"{vault_config.claude_script} --resume {session_id}"

        return SessionResponse(
            session_id=session_id,
            command=command,
            working_dir=vault_config.vault_path,
            task_title=task.title,
            executed_command=prompt,
            success=success,
            error=error_message,
        )

    except FileNotFoundError as e:
        logger.error(f"Task not found: {e}")
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.exception(f"Error executing command: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.patch("/tasks/{task_id}/phase")
async def update_task_phase(
    vault: str,
    task_id: str,
    request: UpdatePhaseRequest,
) -> dict[str, str]:
    """Update task phase in frontmatter.

    Args:
        vault: Vault name
        task_id: Task ID (filename without .md)
        request: Phase update request

    Returns:
        Success message

    Raises:
        HTTPException: If task not found or update fails
    """
    try:
        reader = get_task_reader_for_vault(vault)
        reader.update_task_phase(task_id, request.phase)
        return {"status": "success", "task_id": task_id, "phase": request.phase}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete("/tasks/{task_id}/session")
async def clear_task_session(
    vault: str,
    task_id: str,
) -> dict[str, str]:
    """Clear claude_session_id from task frontmatter.

    Args:
        vault: Vault name
        task_id: Task ID (filename without .md)

    Returns:
        Success message

    Raises:
        HTTPException: If task not found or update fails
    """
    try:
        reader = get_task_reader_for_vault(vault)
        reader.update_task_session_id(task_id, None)
        return {"status": "success", "task_id": task_id}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/cache/reload")
async def reload_cache(vault: str | None = None) -> dict[str, list[str] | dict[str, int]]:
    """Force cache reload for debugging/recovery.

    Args:
        vault: Optional vault name to reload. If None, reloads all vaults.

    Returns:
        {"reloaded": ["Personal", "Brogrammers"], "counts": {"Personal": 234, ...}}

    Raises:
        HTTPException: If vault not found
    """
    from pathlib import Path

    from task_orchestrator.factory import get_config, get_status_cache

    cache = get_status_cache()
    config = get_config()

    if vault:
        # Reload single vault
        vault_config = config.get_vault(vault)
        if not vault_config:
            raise HTTPException(status_code=404, detail=f"Unknown vault: {vault}")

        vault_path = Path(vault_config.vault_path)
        cache.load_vault(vault, vault_path)
        count = len(cache._cache.get(vault, {}))
        return {"reloaded": [vault], "counts": {vault: count}}

    # Reload all vaults
    reloaded = []
    counts = {}
    for vault_config in config.vaults:
        vault_path = Path(vault_config.vault_path)
        cache.load_vault(vault_config.name, vault_path)
        count = len(cache._cache.get(vault_config.name, {}))
        reloaded.append(vault_config.name)
        counts[vault_config.name] = count

    return {"reloaded": reloaded, "counts": counts}


def _task_to_response(task: Task, vault_config: VaultConfig) -> TaskResponse:
    """Convert Task to TaskResponse."""
    # Build Obsidian URL
    # Format: obsidian://open?vault=VaultName&file=Path/To/File.md
    file_path = f"{vault_config.tasks_folder}/{task.id}.md"
    obsidian_url = f"obsidian://open?vault={quote(vault_config.vault_name)}&file={quote(file_path)}"

    return TaskResponse(
        id=task.id,
        title=task.title,
        status=task.status,
        phase=task.phase,
        project_path=task.project_path,
        description=task.description,
        modified_date=task.modified_date,
        obsidian_url=obsidian_url,
        defer_date=task.defer_date,
        planned_date=task.planned_date,
        due_date=task.due_date,
        priority=task.priority,
        category=task.category,
        recurring=task.recurring,
        claude_session_id=task.claude_session_id,
        assignee=task.assignee,
        blocked_by=task.blocked_by,
        vault=vault_config.name,
    )
