# TaskOrchestrator

Orchestrate Claude Code sessions from Obsidian tasks.

## Features

- Kanban board UI showing Obsidian tasks
- Clickable Obsidian links to open tasks in vault
- Start Claude Code sessions in project directories
- Session handoff via session ID
- Dark theme interface

## Installation

```bash
uv sync --all-extras
```

## Usage

Start server:
```bash
make run
```

Or start with auto-reload on code changes:
```bash
make watch
```

Then open http://127.0.0.1:8000

## Development

```bash
make install     # Install dependencies
make format      # Format code
make lint        # Lint code
make typecheck   # Type check
make test        # Run tests
make precommit   # Run all checks
```

## Configuration

Set via environment variables:
- `VAULT_PATH` - Path to Obsidian vault (default: `/Users/bborbe/Documents/Obsidian/Personal`)
- `VAULT_NAME` - Obsidian vault name (default: `Personal`)
- `TASKS_FOLDER` - Tasks folder name (default: `24 Tasks`)
- `CLAUDE_CLI` - Claude CLI command (default: `claude`)
- `HOST` - Server host (default: `127.0.0.1`)
- `PORT` - Server port (default: `8000`)

## Task Format

Tasks must have frontmatter with:
```yaml
---
status: todo  # or in_progress, completed
project: /path/to/project  # Required for running
---
```

## License

BSD-2-Clause license. See [LICENSE](LICENSE) file for details.
