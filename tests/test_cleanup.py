"""Tests for stale session cleanup with assignee-aware logic."""

from unittest.mock import AsyncMock, patch

import pytest

from task_orchestrator.api.models import Task
from task_orchestrator.cleanup import cleanup_stale_sessions
from task_orchestrator.config import Config, VaultConfig


def _make_task(
    session_id: str = "12345678-1234-1234-1234-123456789abc",
    assignee: str | None = None,
    task_id: str = "task-1",
) -> Task:
    return Task(
        id=task_id,
        title="Test Task",
        status="in_progress",
        phase=None,
        project_path=None,
        content="",
        description=None,
        modified_date=None,
        defer_date=None,
        planned_date=None,
        due_date=None,
        priority=None,
        category=None,
        recurring=None,
        claude_session_id=session_id,
        assignee=assignee,
        blocked_by=None,
    )


def _make_config(current_user: str = "alice") -> Config:
    vault = VaultConfig(
        name="testvault",
        vault_path="/vault",
        tasks_folder="Tasks",
        vault_cli_path="vault-cli",
    )
    return Config(vaults=[vault], current_user=current_user)


async def _run_cleanup(config: Config, tasks: list[Task], session_file_exists: bool) -> int:
    """Helper: run cleanup_stale_sessions with mocked VaultCLIClient and filesystem."""
    mock_client = AsyncMock()
    mock_client.list_tasks = AsyncMock(return_value=tasks)

    mock_proc = AsyncMock()
    mock_proc.returncode = 0
    mock_proc.communicate = AsyncMock(return_value=(b"", b""))

    with (
        patch("task_orchestrator.cleanup.VaultCLIClient", return_value=mock_client),
        patch("task_orchestrator.cleanup.Path.exists", return_value=session_file_exists),
        patch(
            "task_orchestrator.cleanup.asyncio.create_subprocess_exec",
            return_value=mock_proc,
        ),
    ):
        return await cleanup_stale_sessions(config)


@pytest.mark.asyncio
async def test_current_user_session_file_exists_not_cleared() -> None:
    """Task assigned to current user with existing session file is NOT cleared."""
    config = _make_config(current_user="alice")
    tasks = [_make_task(assignee="alice")]
    cleared = await _run_cleanup(config, tasks, session_file_exists=True)
    assert cleared == 0


@pytest.mark.asyncio
async def test_current_user_session_file_missing_cleared() -> None:
    """Task assigned to current user with missing session file IS cleared."""
    config = _make_config(current_user="alice")
    tasks = [_make_task(assignee="alice")]
    cleared = await _run_cleanup(config, tasks, session_file_exists=False)
    assert cleared == 1


@pytest.mark.asyncio
async def test_other_user_session_file_exists_always_cleared() -> None:
    """Task assigned to other user is ALWAYS cleared even if session file exists."""
    config = _make_config(current_user="alice")
    tasks = [_make_task(assignee="bob")]
    cleared = await _run_cleanup(config, tasks, session_file_exists=True)
    assert cleared == 1


@pytest.mark.asyncio
async def test_other_user_session_file_missing_always_cleared() -> None:
    """Task assigned to other user is ALWAYS cleared when session file is missing."""
    config = _make_config(current_user="alice")
    tasks = [_make_task(assignee="bob")]
    cleared = await _run_cleanup(config, tasks, session_file_exists=False)
    assert cleared == 1


@pytest.mark.asyncio
async def test_no_assignee_session_file_missing_cleared() -> None:
    """Task with no assignee and missing session file IS cleared."""
    config = _make_config(current_user="alice")
    tasks = [_make_task(assignee=None)]
    cleared = await _run_cleanup(config, tasks, session_file_exists=False)
    assert cleared == 1


@pytest.mark.asyncio
async def test_no_assignee_session_file_exists_not_cleared() -> None:
    """Task with no assignee and existing session file is NOT cleared."""
    config = _make_config(current_user="alice")
    tasks = [_make_task(assignee=None)]
    cleared = await _run_cleanup(config, tasks, session_file_exists=True)
    assert cleared == 0


@pytest.mark.asyncio
async def test_display_name_session_id_always_cleared() -> None:
    """A non-UUID session ID (display name) is cleared regardless of file existence."""
    config = _make_config(current_user="alice")
    tasks = [_make_task(session_id="trading-alerts", assignee="alice")]
    # session_file_exists=True: even if a file happened to exist with that name,
    # display names are always cleared without checking file existence
    cleared = await _run_cleanup(config, tasks, session_file_exists=True)
    assert cleared == 1


@pytest.mark.asyncio
async def test_uuid_session_id_not_cleared_when_file_exists() -> None:
    """A UUID session ID with existing session file is NOT cleared (UUID path, unchanged)."""
    config = _make_config(current_user="alice")
    tasks = [_make_task(session_id="12345678-1234-1234-1234-123456789abc", assignee="alice")]
    cleared = await _run_cleanup(config, tasks, session_file_exists=True)
    assert cleared == 0
