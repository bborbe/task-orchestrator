"""Tests for API endpoints."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from task_orchestrator.__main__ import create_app
from task_orchestrator.config import Config


@pytest.fixture
def test_client(
    tmp_vault: Path, sample_task_file: Path, monkeypatch: pytest.MonkeyPatch
) -> TestClient:
    """Create test client with mocked config."""
    from unittest.mock import AsyncMock, MagicMock

    from task_orchestrator.config import VaultConfig

    # Create test config with test vault
    test_config = Config(
        vaults=[
            VaultConfig(
                name="TestVault",
                vault_path=str(tmp_vault),
                vault_name="TestVault",
                tasks_folder="24 Tasks",
            )
        ],
        claude_cli="claude",
        host="127.0.0.1",
        port=8000,
    )

    # Override factory config
    monkeypatch.setattr("task_orchestrator.factory._config", test_config)

    # Mock session manager and client factory
    mock_session_manager = MagicMock()
    mock_session_manager.create_session = AsyncMock()
    mock_session_manager.send_prompt = AsyncMock(return_value=("test-session-id", "Mocked response"))

    # Inject mocks into tasks module
    monkeypatch.setattr("task_orchestrator.api.tasks._session_manager", mock_session_manager)

    # Create app
    app = create_app()

    return TestClient(app)


def test_list_tasks_endpoint(test_client: TestClient) -> None:
    """Test GET /api/tasks endpoint."""
    response = test_client.get("/api/tasks?vault=TestVault")

    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) >= 1

    task = tasks[0]
    assert "id" in task
    assert "title" in task
    assert "status" in task


def test_list_tasks_with_status_filter(test_client: TestClient) -> None:
    """Test GET /api/tasks with status filter."""
    response = test_client.get("/api/tasks?vault=TestVault&status=todo")

    assert response.status_code == 200
    tasks = response.json()

    # All tasks should have status=todo
    for task in tasks:
        assert task["status"] == "todo"


def test_run_task_endpoint_success(
    test_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test POST /api/tasks/{id}/run endpoint success."""
    response = test_client.post("/api/tasks/Test%20Task/run?vault=TestVault")

    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert "command" in data
    assert "working_dir" in data
    assert len(data["session_id"]) > 0  # Has a session ID
    assert "claude --resume" in data["command"]
    assert data["session_id"] in data["command"]


def test_run_task_endpoint_not_found(test_client: TestClient) -> None:
    """Test POST /api/tasks/{id}/run with non-existent task."""
    response = test_client.post("/api/tasks/NonExistent/run?vault=TestVault")

    assert response.status_code == 404


def test_run_task_endpoint_no_project(test_client: TestClient, tmp_vault: Path) -> None:
    """Test POST /api/tasks/{id}/run with task missing project field - should still work."""
    # Create task without project field
    tasks_dir = tmp_vault / "24 Tasks"
    task_file = tasks_dir / "No Project Task.md"

    content = """---
status: todo
---

Task without project.
"""

    task_file.write_text(content)

    response = test_client.post("/api/tasks/No%20Project%20Task/run?vault=TestVault")

    # Should succeed even without project field
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert "command" in data


def test_list_tasks_filters_deferred(test_client: TestClient, tmp_vault: Path) -> None:
    """Test that tasks with future defer_date are filtered out."""
    # Create deferred task
    tasks_dir = tmp_vault / "24 Tasks"
    task_file = tasks_dir / "Deferred Task.md"

    content = """---
status: in_progress
phase: todo
defer_date: 2026-05-01
---

# Impact
Task deferred until May.
"""

    task_file.write_text(content)

    response = test_client.get("/api/tasks?vault=TestVault")

    assert response.status_code == 200
    tasks = response.json()

    # Deferred task should not be in results
    task_ids = [t["id"] for t in tasks]
    assert "Deferred Task" not in task_ids
