"""API models for TaskOrchestrator."""

from dataclasses import dataclass

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
    defer_date: str | None  # From frontmatter: YYYY-MM-DD
    planned_date: str | None  # From frontmatter: YYYY-MM-DD
    due_date: str | None  # From frontmatter: YYYY-MM-DD
    priority: int | None  # From frontmatter: 1-3
    category: str | None  # From frontmatter
    recurring: str | None  # From frontmatter: daily, weekly, monthly


class TaskResponse(BaseModel):
    """API response model for tasks."""

    id: str
    title: str
    status: str
    phase: str | None
    project_path: str | None
    obsidian_url: str
    defer_date: str | None
    planned_date: str | None
    due_date: str | None
    priority: int | None
    category: str | None
    recurring: str | None


class SessionResponse(BaseModel):
    """API response model for sessions."""

    session_id: str
    handoff_command: str
