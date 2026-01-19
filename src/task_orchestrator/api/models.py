"""API models for TaskOrchestrator."""

from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel


@dataclass
class Task:
    """Task from Obsidian vault."""

    id: str  # Filename without .md
    title: str  # First heading or filename
    status: str  # From frontmatter
    phase: (
        str | None
    )  # From frontmatter: todo, planning, in_progress, ai_review, human_review, done
    project_path: str | None  # From frontmatter
    content: str  # Full markdown content
    description: str | None  # First 100 chars of content (for card display)
    modified_date: datetime | None  # File modification time
    defer_date: str | None  # From frontmatter: YYYY-MM-DD
    planned_date: str | None  # From frontmatter: YYYY-MM-DD
    due_date: str | None  # From frontmatter: YYYY-MM-DD
    priority: int | str | None  # From frontmatter: 1-3 or "low"/"medium"/"high"/"highest"
    category: str | None  # From frontmatter
    recurring: str | None  # From frontmatter: daily, weekly, monthly
    claude_session_id: str | None  # From frontmatter: Claude Code session UUID


class TaskResponse(BaseModel):
    """API response model for tasks."""

    id: str
    title: str
    status: str
    phase: str | None
    project_path: str | None
    description: str | None
    modified_date: datetime | None
    obsidian_url: str
    defer_date: str | None
    planned_date: str | None
    due_date: str | None
    priority: int | str | None
    category: str | None
    recurring: str | None
    claude_session_id: str | None


class SessionResponse(BaseModel):
    """API response model for sessions."""

    session_id: str
    command: str
    working_dir: str
