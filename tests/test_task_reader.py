"""Tests for ObsidianTaskReader."""

from pathlib import Path

import pytest

from task_orchestrator.obsidian.task_reader import ObsidianTaskReader


def test_list_tasks_empty(tmp_vault: Path) -> None:
    """Test listing tasks from empty vault."""
    reader = ObsidianTaskReader(str(tmp_vault), "24 Tasks")
    tasks = reader.list_tasks()
    assert len(tasks) == 0


def test_list_tasks_with_file(tmp_vault: Path, sample_task_file: Path) -> None:
    """Test listing tasks with one file."""
    reader = ObsidianTaskReader(str(tmp_vault), "24 Tasks")
    tasks = reader.list_tasks()

    assert len(tasks) == 1
    task = tasks[0]
    assert task.id == "Test Task"
    assert task.title == "Test Task"  # Title is filename, not H1 heading
    assert task.status == "in_progress"
    assert task.phase == "planning"
    assert task.project_path == "/Users/bborbe/Documents/workspaces/test-project"


def test_list_tasks_status_filter(tmp_vault: Path, sample_task_file: Path) -> None:
    """Test filtering tasks by status."""
    reader = ObsidianTaskReader(str(tmp_vault), "24 Tasks")

    # Should find in_progress task
    in_progress_tasks = reader.list_tasks(status_filter=["in_progress"])
    assert len(in_progress_tasks) == 1

    # Should not find completed tasks
    completed_tasks = reader.list_tasks(status_filter=["completed"])
    assert len(completed_tasks) == 0


def test_read_task(tmp_vault: Path, sample_task_file: Path) -> None:
    """Test reading specific task."""
    reader = ObsidianTaskReader(str(tmp_vault), "24 Tasks")
    task = reader.read_task("Test Task")

    assert task.id == "Test Task"
    assert task.title == "Test Task"  # Title is filename, not H1 heading
    assert task.status == "in_progress"
    assert task.phase == "planning"
    assert task.project_path == "/Users/bborbe/Documents/workspaces/test-project"
    assert "Success Criteria" in task.content


def test_read_task_not_found(tmp_vault: Path) -> None:
    """Test reading non-existent task."""
    reader = ObsidianTaskReader(str(tmp_vault), "24 Tasks")

    with pytest.raises(FileNotFoundError):
        reader.read_task("NonExistent")


def test_parse_task_without_project(tmp_vault: Path) -> None:
    """Test parsing task without project field."""
    tasks_dir = tmp_vault / "24 Tasks"
    task_file = tasks_dir / "No Project.md"

    content = """---
status: in_progress
phase: in_progress
---

# Impact
Task without project field.
"""

    task_file.write_text(content)

    reader = ObsidianTaskReader(str(tmp_vault), "24 Tasks")
    task = reader.read_task("No Project")

    assert task.id == "No Project"
    assert task.status == "in_progress"
    assert task.phase == "in_progress"
    assert task.project_path is None


def test_parse_task_with_dates_and_metadata(tmp_vault: Path, sample_task_file: Path) -> None:
    """Test parsing task with date fields and metadata."""
    reader = ObsidianTaskReader(str(tmp_vault), "24 Tasks")
    task = reader.read_task("Test Task")

    assert task.defer_date == "2026-01-01"
    assert task.planned_date == "2026-02-15"
    assert task.due_date == "2026-02-28"
    assert task.priority == 1
    assert task.category == "testing"
    assert task.recurring is None


def test_update_task_phase(tmp_vault: Path, sample_task_file: Path) -> None:
    """Test updating task phase."""
    reader = ObsidianTaskReader(str(tmp_vault), "24 Tasks")

    # Update phase
    reader.update_task_phase("Test Task", "in_progress")

    # Read back and verify
    task = reader.read_task("Test Task")
    assert task.phase == "in_progress"


def test_parse_task_with_future_defer_date(tmp_vault: Path) -> None:
    """Test parsing task with future defer date."""
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

    reader = ObsidianTaskReader(str(tmp_vault), "24 Tasks")
    task = reader.read_task("Deferred Task")

    assert task.id == "Deferred Task"
    assert task.defer_date == "2026-05-01"


def test_normalize_status_variations(tmp_vault: Path) -> None:
    """Test that status variations are normalized to in_progress."""
    tasks_dir = tmp_vault / "24 Tasks"
    reader = ObsidianTaskReader(str(tmp_vault), "24 Tasks")

    # Test all variations that should normalize to "in_progress"
    status_variations = [
        ("in_progress", "in_progress"),
        ("in-progress", "in_progress"),
        ("inprogress", "in_progress"),
        ("current", "in_progress"),
    ]

    for idx, (status_input, expected) in enumerate(status_variations):
        task_file = tasks_dir / f"Task{idx}.md"
        content = f"""---
status: {status_input}
---

# Task
Test task with status: {status_input}
"""
        task_file.write_text(content)

        task = reader.read_task(f"Task{idx}")
        assert task.status == expected, (
            f"Status '{status_input}' should normalize to '{expected}', got '{task.status}'"
        )


def test_normalize_status_preserves_other_statuses(tmp_vault: Path) -> None:
    """Test that other statuses are preserved as-is."""
    tasks_dir = tmp_vault / "24 Tasks"
    reader = ObsidianTaskReader(str(tmp_vault), "24 Tasks")

    # Test that other statuses are not changed
    other_statuses = ["todo", "completed", "backlog", "hold"]

    for idx, status in enumerate(other_statuses):
        task_file = tasks_dir / f"OtherTask{idx}.md"
        content = f"""---
status: {status}
---

# Task
Test task with status: {status}
"""
        task_file.write_text(content)

        task = reader.read_task(f"OtherTask{idx}")
        assert task.status == status, f"Status '{status}' should be preserved, got '{task.status}'"
