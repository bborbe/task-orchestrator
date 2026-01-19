"""Claude Code session executor."""

import logging
import subprocess
import uuid
from typing import Protocol

from task_orchestrator.api.models import Task

logger = logging.getLogger(__name__)


class ClaudeExecutor(Protocol):
    """Protocol for executing Claude Code sessions."""

    def create_session(self, task: Task, project_dir: str) -> str:
        """Create a new Claude Code session for the task."""
        ...


class ClaudeCodeExecutor:
    """Executor for Claude Code CLI."""

    def __init__(self, claude_cli: str) -> None:
        """Initialize with Claude CLI command path."""
        self._claude_cli = claude_cli

    def create_session(self, task: Task, project_dir: str) -> str:
        """Create a new Claude Code session for the given task.

        Args:
            task: The task to execute
            project_dir: The project directory to run Claude in

        Returns:
            Session ID for handoff

        Raises:
            RuntimeError: If Claude session creation fails
        """
        # Build prompt from task
        prompt = self._build_prompt(task)

        # Execute Claude Code command
        try:
            # Note: claude -C sets working directory
            # We use subprocess.Popen to start it in background
            # and don't wait for completion
            _ = subprocess.Popen(
                [self._claude_cli, "-C", project_dir, prompt],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # For MVP, we generate a synthetic session ID
            # since we can't easily parse it from Claude's output in background mode
            # In production, we'd need to properly capture the session ID
            # from Claude's output or use Claude's API
            session_id = str(uuid.uuid4())

            logger.info(f"Started Claude session for task {task.id} in {project_dir}")

            return session_id

        except FileNotFoundError as e:
            logger.error(f"Claude CLI not found: {self._claude_cli}")
            raise RuntimeError(f"Claude CLI not found: {self._claude_cli}") from e
        except Exception as e:
            logger.error(f"Failed to start Claude session: {e}")
            raise RuntimeError(f"Failed to start Claude session: {e}") from e

    def _build_prompt(self, task: Task) -> str:
        """Build Claude prompt from task content."""
        return f"""Complete this Obsidian task:

# {task.title}

{task.content}

Work on this task in the current project directory. When complete, \
document your work back in the Obsidian vault task file.
"""
