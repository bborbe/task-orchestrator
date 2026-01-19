"""Task API endpoints."""

# ruff: noqa: B008  # FastAPI Depends pattern is safe in function signatures

from datetime import date
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from task_orchestrator.api.models import SessionResponse, Task, TaskResponse
from task_orchestrator.claude.executor import ClaudeExecutor
from task_orchestrator.config import VaultConfig
from task_orchestrator.factory import (
    get_config,
    get_executor,
    get_task_reader_for_vault,
    get_vault_config,
)

router = APIRouter()


class VaultResponse(BaseModel):
    """API response model for vault."""

    name: str
    vault_path: str
    tasks_folder: str


class UpdatePhaseRequest(BaseModel):
    """Request model for updating task phase."""

    phase: str


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
        )
        for vault in config.vaults
    ]


@router.get("/tasks", response_model=list[TaskResponse])
async def list_tasks(
    vault: str,
    status: str | None = None,
    phase: str | None = None,
) -> list[TaskResponse]:
    """List tasks from Obsidian vault.

    Args:
        vault: Vault name to read from
        status: Comma-separated list of statuses to filter (e.g. "in_progress,todo")
        phase: Comma-separated list of phases to filter (e.g. "planning,implementation")

    Returns:
        List of tasks matching the filter
    """
    try:
        reader = get_task_reader_for_vault(vault)
        vault_config = get_vault_config(vault)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    # Parse status filter
    status_filter: list[str] | None = None
    if status:
        status_filter = [s.strip() for s in status.split(",")]

    # Parse phase filter
    phase_filter: list[str] | None = None
    if phase:
        phase_filter = [s.strip() for s in phase.split(",")]

    # Get tasks
    tasks = reader.list_tasks(status_filter=status_filter)

    # Filter by phase if specified (include tasks with None phase)
    if phase_filter:
        tasks = [t for t in tasks if t.phase in phase_filter or t.phase is None]

    # Filter out deferred tasks (defer_date in future)
    today = date.today()
    tasks = [t for t in tasks if t.defer_date is None or date.fromisoformat(t.defer_date) <= today]

    # Convert to response models
    return [_task_to_response(task, vault_config) for task in tasks]


@router.post("/tasks/{task_id}/run", response_model=SessionResponse)
async def run_task(
    vault: str,
    task_id: str,
    executor: ClaudeExecutor = Depends(get_executor),
) -> SessionResponse:
    """Start a Claude Code session for the given task.

    Args:
        vault: Vault name
        task_id: Task ID (filename without .md)
        executor: Claude executor dependency

    Returns:
        Session information for handoff

    Raises:
        HTTPException: If task not found or missing project field
    """
    try:
        reader = get_task_reader_for_vault(vault)
        # Read task
        task = reader.read_task(task_id)

        # Validate project path
        if not task.project_path:
            raise HTTPException(
                status_code=400,
                detail="Task missing 'project' field in frontmatter",
            )

        # Create session
        session_id = executor.create_session(task, task.project_path)

        return SessionResponse(
            session_id=session_id,
            handoff_command=f"claude -p {session_id}",
        )

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except RuntimeError as e:
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
        obsidian_url=obsidian_url,
        defer_date=task.defer_date,
        planned_date=task.planned_date,
        due_date=task.due_date,
        priority=task.priority,
        category=task.category,
        recurring=task.recurring,
    )
