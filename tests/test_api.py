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
    mock_session_manager.send_prompt = AsyncMock(
        return_value=("test-session-id", "Mocked response")
    )

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


def test_list_tasks_includes_defer_date_today(test_client: TestClient, tmp_vault: Path) -> None:
    """Test that tasks with defer_date=today ARE included."""
    from datetime import date

    # Create task deferred until today
    tasks_dir = tmp_vault / "24 Tasks"
    task_file = tasks_dir / "Task Due Today.md"

    today = date.today().isoformat()
    content = f"""---
status: in_progress
phase: todo
defer_date: {today}
---

Task due today should appear.
"""

    task_file.write_text(content)

    response = test_client.get("/api/tasks?vault=TestVault")

    assert response.status_code == 200
    tasks = response.json()

    # Task with defer_date=today SHOULD be in results
    task_ids = [t["id"] for t in tasks]
    assert "Task Due Today" in task_ids


def test_list_tasks_no_vault_returns_all_vaults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test GET /api/tasks with no vault parameter returns tasks from all vaults."""
    from unittest.mock import AsyncMock, MagicMock

    from task_orchestrator.config import VaultConfig

    # Create two test vaults
    vault1 = tmp_path / "vault1"
    vault1_tasks = vault1 / "24 Tasks"
    vault1_tasks.mkdir(parents=True)

    vault2 = tmp_path / "vault2"
    vault2_tasks = vault2 / "24 Tasks"
    vault2_tasks.mkdir(parents=True)

    # Create task in vault1
    task1 = vault1_tasks / "Task1.md"
    task1.write_text("""---
status: in_progress
---
Task in vault 1
""")

    # Create task in vault2
    task2 = vault2_tasks / "Task2.md"
    task2.write_text("""---
status: in_progress
---
Task in vault 2
""")

    # Create test config with two vaults
    test_config = Config(
        vaults=[
            VaultConfig(
                name="Vault1",
                vault_path=str(vault1),
                vault_name="Vault1",
                tasks_folder="24 Tasks",
            ),
            VaultConfig(
                name="Vault2",
                vault_path=str(vault2),
                vault_name="Vault2",
                tasks_folder="24 Tasks",
            ),
        ],
        claude_cli="claude",
        host="127.0.0.1",
        port=8000,
    )

    # Override factory config
    monkeypatch.setattr("task_orchestrator.factory._config", test_config)

    # Mock session manager
    mock_session_manager = MagicMock()
    mock_session_manager.send_prompt = AsyncMock(
        return_value=("test-session-id", "Mocked response")
    )
    monkeypatch.setattr("task_orchestrator.api.tasks._session_manager", mock_session_manager)

    # Create app
    app = create_app()
    client = TestClient(app)

    # Request without vault parameter
    response = client.get("/api/tasks")

    assert response.status_code == 200
    tasks = response.json()
    task_ids = [t["id"] for t in tasks]

    # Should contain tasks from both vaults
    assert "Task1" in task_ids
    assert "Task2" in task_ids
    assert len(task_ids) >= 2


def test_list_tasks_single_vault(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test GET /api/tasks with single vault parameter."""
    from unittest.mock import AsyncMock, MagicMock

    from task_orchestrator.config import VaultConfig

    # Create two test vaults
    vault1 = tmp_path / "vault1"
    vault1_tasks = vault1 / "24 Tasks"
    vault1_tasks.mkdir(parents=True)

    vault2 = tmp_path / "vault2"
    vault2_tasks = vault2 / "24 Tasks"
    vault2_tasks.mkdir(parents=True)

    # Create task in vault1
    task1 = vault1_tasks / "Task1.md"
    task1.write_text("""---
status: in_progress
---
Task in vault 1
""")

    # Create task in vault2
    task2 = vault2_tasks / "Task2.md"
    task2.write_text("""---
status: in_progress
---
Task in vault 2
""")

    # Create test config with two vaults
    test_config = Config(
        vaults=[
            VaultConfig(
                name="Vault1",
                vault_path=str(vault1),
                vault_name="Vault1",
                tasks_folder="24 Tasks",
            ),
            VaultConfig(
                name="Vault2",
                vault_path=str(vault2),
                vault_name="Vault2",
                tasks_folder="24 Tasks",
            ),
        ],
        claude_cli="claude",
        host="127.0.0.1",
        port=8000,
    )

    # Override factory config
    monkeypatch.setattr("task_orchestrator.factory._config", test_config)

    # Mock session manager
    mock_session_manager = MagicMock()
    mock_session_manager.send_prompt = AsyncMock(
        return_value=("test-session-id", "Mocked response")
    )
    monkeypatch.setattr("task_orchestrator.api.tasks._session_manager", mock_session_manager)

    # Create app
    app = create_app()
    client = TestClient(app)

    # Request with vault=Vault1
    response = client.get("/api/tasks?vault=Vault1")

    assert response.status_code == 200
    tasks = response.json()
    task_ids = [t["id"] for t in tasks]

    # Should only contain task from Vault1
    assert "Task1" in task_ids
    assert "Task2" not in task_ids


def test_list_tasks_multiple_vaults(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test GET /api/tasks with multiple vault parameters."""
    from unittest.mock import AsyncMock, MagicMock

    from task_orchestrator.config import VaultConfig

    # Create three test vaults
    vault1 = tmp_path / "vault1"
    vault1_tasks = vault1 / "24 Tasks"
    vault1_tasks.mkdir(parents=True)

    vault2 = tmp_path / "vault2"
    vault2_tasks = vault2 / "24 Tasks"
    vault2_tasks.mkdir(parents=True)

    vault3 = tmp_path / "vault3"
    vault3_tasks = vault3 / "24 Tasks"
    vault3_tasks.mkdir(parents=True)

    # Create tasks
    task1 = vault1_tasks / "Task1.md"
    task1.write_text("""---
status: in_progress
---
Task in vault 1
""")

    task2 = vault2_tasks / "Task2.md"
    task2.write_text("""---
status: in_progress
---
Task in vault 2
""")

    task3 = vault3_tasks / "Task3.md"
    task3.write_text("""---
status: in_progress
---
Task in vault 3
""")

    # Create test config
    test_config = Config(
        vaults=[
            VaultConfig(
                name="Vault1",
                vault_path=str(vault1),
                vault_name="Vault1",
                tasks_folder="24 Tasks",
            ),
            VaultConfig(
                name="Vault2",
                vault_path=str(vault2),
                vault_name="Vault2",
                tasks_folder="24 Tasks",
            ),
            VaultConfig(
                name="Vault3",
                vault_path=str(vault3),
                vault_name="Vault3",
                tasks_folder="24 Tasks",
            ),
        ],
        claude_cli="claude",
        host="127.0.0.1",
        port=8000,
    )

    monkeypatch.setattr("task_orchestrator.factory._config", test_config)

    mock_session_manager = MagicMock()
    mock_session_manager.send_prompt = AsyncMock(
        return_value=("test-session-id", "Mocked response")
    )
    monkeypatch.setattr("task_orchestrator.api.tasks._session_manager", mock_session_manager)

    app = create_app()
    client = TestClient(app)

    # Request with vault=Vault1&vault=Vault2
    response = client.get("/api/tasks?vault=Vault1&vault=Vault2")

    assert response.status_code == 200
    tasks = response.json()
    task_ids = [t["id"] for t in tasks]

    # Should contain tasks from Vault1 and Vault2, but not Vault3
    assert "Task1" in task_ids
    assert "Task2" in task_ids
    assert "Task3" not in task_ids


def test_list_tasks_with_assignee_filter(test_client: TestClient, tmp_vault: Path) -> None:
    """Test GET /api/tasks with assignee filter."""
    # Create tasks with different assignees
    tasks_dir = tmp_vault / "24 Tasks"

    task1 = tasks_dir / "Task Assigned to Alice.md"
    task1.write_text("""---
status: in_progress
assignee: alice
---
Task for Alice
""")

    task2 = tasks_dir / "Task Assigned to Bob.md"
    task2.write_text("""---
status: in_progress
assignee: bob
---
Task for Bob
""")

    task3 = tasks_dir / "Task Unassigned.md"
    task3.write_text("""---
status: in_progress
---
Task without assignee
""")

    # Filter by assignee=alice
    response = test_client.get("/api/tasks?vault=TestVault&assignee=alice")

    assert response.status_code == 200
    tasks = response.json()
    task_ids = [t["id"] for t in tasks]

    # Should only contain Alice's task
    assert "Task Assigned to Alice" in task_ids
    assert "Task Assigned to Bob" not in task_ids
    assert "Task Unassigned" not in task_ids


def test_list_tasks_phase_filter_none_only_in_todo(
    test_client: TestClient, tmp_vault: Path
) -> None:
    """Test that tasks with None phase only appear when filtering for todo."""
    tasks_dir = tmp_vault / "24 Tasks"

    # Task with no phase
    task_no_phase = tasks_dir / "Task Without Phase.md"
    task_no_phase.write_text("""---
status: in_progress
---
Task without phase field
""")

    # Task with todo phase
    task_todo = tasks_dir / "Task Todo.md"
    task_todo.write_text("""---
status: in_progress
phase: todo
---
Task in todo
""")

    # Task with in_progress phase
    task_in_progress = tasks_dir / "Task In Progress.md"
    task_in_progress.write_text("""---
status: in_progress
phase: in_progress
---
Task in progress
""")

    # Filter by phase=todo
    response = test_client.get("/api/tasks?vault=TestVault&phase=todo")
    assert response.status_code == 200
    tasks = response.json()
    task_ids = [t["id"] for t in tasks]

    # Should include both None phase and todo phase
    assert "Task Without Phase" in task_ids
    assert "Task Todo" in task_ids
    assert "Task In Progress" not in task_ids

    # Filter by phase=in_progress
    response = test_client.get("/api/tasks?vault=TestVault&phase=in_progress")
    assert response.status_code == 200
    tasks = response.json()
    task_ids = [t["id"] for t in tasks]

    # Should NOT include None phase, only in_progress
    assert "Task Without Phase" not in task_ids
    assert "Task Todo" not in task_ids
    assert "Task In Progress" in task_ids


def test_list_tasks_invalid_phase_treated_as_todo(test_client: TestClient, tmp_vault: Path) -> None:
    """Test that tasks with invalid phase values are treated like None phase (default to todo)."""
    tasks_dir = tmp_vault / "24 Tasks"

    # Task with invalid phase
    task_invalid = tasks_dir / "Task Invalid Phase.md"
    task_invalid.write_text("""---
status: in_progress
phase: banana
---
Task with invalid phase
""")

    # Filter by phase=todo (should include invalid phases)
    response = test_client.get("/api/tasks?vault=TestVault&phase=todo")
    assert response.status_code == 200
    tasks = response.json()
    task_ids = [t["id"] for t in tasks]

    # Invalid phase should be treated like None phase and included in todo filter
    assert "Task Invalid Phase" in task_ids


def test_list_tasks_warns_on_status_phase_mismatch(
    test_client: TestClient, tmp_vault: Path
) -> None:
    """Test that tasks with status=in_progress but phase=null are still returned.

    This is a data quality issue (not a code bug), but we document the behavior:
    - Backend returns the task (correct)
    - Frontend will place it in 'todo' column (phase defaults to todo)
    - User expects it in 'in_progress' column (based on status)

    Proper fix: Ensure phase field matches status in task files.
    """
    tasks_dir = tmp_vault / "24 Tasks"

    # Task with status=in_progress but no phase field
    task_no_phase = tasks_dir / "Task Status Phase Mismatch.md"
    task_no_phase.write_text("""---
status: in_progress
---
Task with status in_progress but no phase field
""")

    # Request with phase filter that includes todo
    response = test_client.get("/api/tasks?vault=TestVault&status=in_progress&phase=todo")
    assert response.status_code == 200
    tasks = response.json()

    # Task should be returned (null phase defaults to todo)
    task_ids = [t["id"] for t in tasks]
    assert "Task Status Phase Mismatch" in task_ids

    # Verify the task has null phase (will appear in todo column on frontend)
    task = next(t for t in tasks if t["id"] == "Task Status Phase Mismatch")
    assert task["status"] == "in_progress"
    assert task["phase"] is None  # Frontend will default this to 'todo'
