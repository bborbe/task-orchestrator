"""Task reader for Obsidian vault."""

import logging
import re
from contextlib import suppress
from datetime import date, datetime
from pathlib import Path
from typing import Any, Protocol

import yaml

from task_orchestrator.api.models import Task

logger = logging.getLogger(__name__)


class TaskReader(Protocol):
    """Protocol for reading tasks."""

    def list_tasks(self, status_filter: list[str] | None = None) -> list[Task]:
        """List all tasks, optionally filtered by status."""
        ...

    def read_task(self, task_id: str) -> Task:
        """Read a specific task by ID."""
        ...

    def update_task_phase(self, task_id: str, new_phase: str) -> None:
        """Update the phase field in task frontmatter."""
        ...


class ObsidianTaskReader:
    """Task reader for Obsidian markdown files."""

    def __init__(self, vault_path: str, tasks_folder: str) -> None:
        """Initialize reader with vault and tasks folder paths."""
        self._tasks_dir = Path(vault_path) / tasks_folder

    def update_task_phase(self, task_id: str, new_phase: str) -> None:
        """Update the phase field in task frontmatter."""
        file_path = self._tasks_dir / f"{task_id}.md"
        if not file_path.exists():
            raise FileNotFoundError(f"Task not found: {task_id}")

        # Try UTF-8 first, fallback to latin-1 for non-UTF-8 files
        try:
            content = file_path.read_text(encoding="utf-8")
            encoding = "utf-8"
        except UnicodeDecodeError:
            content = file_path.read_text(encoding="latin-1")
            encoding = "latin-1"

        # Match frontmatter between --- markers
        match = re.match(r"^(---\s*\n)(.*?)(\n---)", content, re.DOTALL)
        if not match:
            raise ValueError(f"Task {task_id} has no frontmatter")

        frontmatter_text = match.group(2)

        # Parse existing frontmatter
        try:
            data = yaml.safe_load(frontmatter_text) or {}
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in task {task_id}") from e

        # Update phase
        data["phase"] = new_phase

        # Serialize back to YAML
        new_frontmatter = yaml.dump(data, default_flow_style=False, sort_keys=False)

        # Reconstruct content
        new_content = f"---\n{new_frontmatter}---" + content[match.end() :]

        # Write back with same encoding
        file_path.write_text(new_content, encoding=encoding)

    def update_task_session_id(self, task_id: str, session_id: str) -> None:
        """Update the claude_session_id field in task frontmatter."""
        file_path = self._tasks_dir / f"{task_id}.md"
        if not file_path.exists():
            raise FileNotFoundError(f"Task not found: {task_id}")

        # Try UTF-8 first, fallback to latin-1 for non-UTF-8 files
        try:
            content = file_path.read_text(encoding="utf-8")
            encoding = "utf-8"
        except UnicodeDecodeError:
            content = file_path.read_text(encoding="latin-1")
            encoding = "latin-1"

        # Match frontmatter between --- markers
        match = re.match(r"^(---\s*\n)(.*?)(\n---)", content, re.DOTALL)
        if not match:
            raise ValueError(f"Task {task_id} has no frontmatter")

        frontmatter_text = match.group(2)

        # Parse existing frontmatter
        try:
            data = yaml.safe_load(frontmatter_text) or {}
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in task {task_id}") from e

        # Update claude_session_id
        data["claude_session_id"] = session_id

        # Serialize back to YAML
        new_frontmatter = yaml.dump(data, default_flow_style=False, sort_keys=False)

        # Reconstruct content
        new_content = f"---\n{new_frontmatter}---" + content[match.end() :]

        # Write back with same encoding
        file_path.write_text(new_content, encoding=encoding)

    def list_tasks(self, status_filter: list[str] | None = None) -> list[Task]:
        """List all tasks from vault, optionally filtered by status."""
        tasks: list[Task] = []
        for file_path in self._tasks_dir.glob("*.md"):
            try:
                task = self._parse_task(file_path)
                if status_filter is None or task.status in status_filter:
                    tasks.append(task)
            except Exception as e:
                logger.warning(f"Failed to parse {file_path.name}: {e}")
                continue
        return tasks

    def read_task(self, task_id: str) -> Task:
        """Read a specific task by ID (filename without .md)."""
        file_path = self._tasks_dir / f"{task_id}.md"
        if not file_path.exists():
            raise FileNotFoundError(f"Task not found: {task_id}")
        return self._parse_task(file_path)

    def _parse_task(self, file_path: Path) -> Task:
        """Parse markdown file into Task object."""
        # Try UTF-8 first, fallback to latin-1 for non-UTF-8 files
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = file_path.read_text(encoding="latin-1")

        # Extract frontmatter
        frontmatter = self._extract_frontmatter(content)

        # Get status (required field)
        status = frontmatter.get("status", "unknown")

        # Get phase (optional: todo, planning, in_progress, ai_review, human_review, done)
        phase = frontmatter.get("phase")

        # Get project path (optional field)
        project_path = frontmatter.get("project")

        # Get date fields (optional)
        # YAML parser converts dates to date objects, convert back to ISO strings
        defer_date = self._date_to_string(frontmatter.get("defer_date"))
        planned_date = self._date_to_string(frontmatter.get("planned_date"))
        due_date = self._date_to_string(frontmatter.get("due_date"))

        # Get priority (optional, 1-3 or string like "medium", "high")
        priority = self._normalize_priority(frontmatter.get("priority"))

        # Get category (optional)
        category = frontmatter.get("category")

        # Get recurring (optional: daily, weekly, monthly)
        recurring = frontmatter.get("recurring")

        # Get Claude session ID (optional)
        claude_session_id = frontmatter.get("claude_session_id")

        # Use filename as title (not H1 headings which are section names)
        title = file_path.stem

        # Task ID is filename without extension
        task_id = file_path.stem

        # Extract description (first 100 chars after frontmatter, clean text only)
        description = self._extract_description(content)

        # Get file modification time
        modified_date = datetime.fromtimestamp(file_path.stat().st_mtime)

        return Task(
            id=task_id,
            title=title,
            status=status,
            phase=phase,
            project_path=project_path,
            content=content,
            description=description,
            modified_date=modified_date,
            defer_date=defer_date,
            planned_date=planned_date,
            due_date=due_date,
            priority=priority,
            category=category,
            recurring=recurring,
            claude_session_id=claude_session_id,
        )

    def _normalize_priority(self, value: Any) -> int | str | None:
        """Normalize priority to int or string.

        Accepts:
        - int: Passed through
        - str (numeric): Converted to int
        - str (non-numeric): Passed through (e.g., "medium", "high")
        - None: Passed through

        Rejects (returns None):
        - bool: Rejected (booleans are subclass of int, need explicit check)
        - float: Rejected (not a valid priority format)
        - Empty strings: Rejected
        - Other types: Rejected
        """
        if value is None:
            return None
        # Check bool before int (bool is subclass of int in Python)
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            # Reject empty/whitespace-only strings
            if not value.strip():
                return None
            # Try to convert numeric strings to int
            with suppress(ValueError):
                return int(value)
            # Keep non-numeric strings (medium, high, etc.)
            return value
        # Reject floats and other unexpected types
        return None

    def _date_to_string(self, value: Any) -> str | None:
        """Convert date object to ISO string or return None."""
        if value is None:
            return None
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, str):
            return value
        return None

    def _extract_frontmatter(self, content: str) -> dict[str, Any]:
        """Extract YAML frontmatter from markdown content."""
        # Match frontmatter between --- markers
        match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
        if not match:
            return {}

        try:
            frontmatter_text = match.group(1)
            data = yaml.safe_load(frontmatter_text)
            return data if isinstance(data, dict) else {}
        except yaml.YAMLError:
            return {}

    def _extract_description(self, content: str) -> str | None:
        """Extract first 100 chars of content after frontmatter for description.

        Removes frontmatter, markdown formatting, and extra whitespace.
        """
        # Remove frontmatter
        match = re.match(r"^---\s*\n.*?\n---\s*\n", content, re.DOTALL)
        if match:
            content = content[match.end() :]

        # Remove markdown headers, links, and extra whitespace
        content = re.sub(r"#{1,6}\s+", "", content)  # Headers
        content = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", content)  # Links [text](url) -> text
        content = re.sub(r"\[\[([^\]]+)\]\]", r"\1", content)  # Wikilinks [[text]] -> text
        content = re.sub(r"\s+", " ", content)  # Normalize whitespace
        content = content.strip()

        # Return first 100 chars or None if empty
        if not content:
            return None
        return content[:100] + ("..." if len(content) > 100 else "")
