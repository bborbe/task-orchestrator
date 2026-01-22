# Changelog

All notable changes to this project will be documented in this file.

Please choose versions by [Semantic Versioning](http://semver.org/).

* MAJOR version when you make incompatible API changes,
* MINOR version when you add functionality in a backwards-compatible manner, and
* PATCH version when you make backwards-compatible bug fixes.

## v0.4.3
- Use `--tool` flag for slash commands (machine-readable JSON output)
- Set phase to `human_review` on command failure
- Add create-task command support
- Migrate from deprecated on_event to lifespan context manager
- Fix loading modal dismiss not preventing session modal popup

## v0.4.2
- Add fallback polling every 60 seconds in case WebSocket misses updates

## v0.4.1
- Fix phase filtering to include tasks with invalid phase values (defaults to todo)
- Add test for tasks with defer_date=today inclusion
- Add test for invalid phase handling (phase: banana)
- Add test documenting status/phase mismatch behavior

## v0.4.0
- Add multi-vault support with "All" option in dropdown
- Add URL parameter filtering for vault (supports multiple `?vault=X&vault=Y`)
- Add assignee URL parameter filtering (`?assignee=name`)
- Add clickable assignee badges to filter tasks by assignee
- Add vault field to TaskResponse model for proper task identification
- Add 5 comprehensive tests for vault and assignee filtering
- Fix phase filtering to only show tasks without phase in todo column
- Improve WebSocket updates to handle multi-vault filtering

## v0.3.0
- Add slash command execution API endpoint with success/failure parsing
- Add loading modal with spinner and close button for command execution
- Add status message display in session modal (success/failure feedback)
- Add absolute date calculation for defer-task (tomorrow = YYYY-MM-DD)
- Fix defer_date field reading in task reader
- Improve slash command UX (non-blocking close, background execution)

## v0.2.0

- Add assignee display with 👤 icon badge in task cards
- Add Jira issue extraction from task titles with clickable 🔖 badges
- Add project domain mapping (BRO→seibertgroup.atlassian.net, TRADE→borbe.atlassian.net)
- Add configurable claude_script per vault (defaults to "claude")
- Add clickable task titles that link to Obsidian (entire title, not just icon)
- Add "Complete Task" and "Defer Task" slash command actions to dropdown menu
- Add status normalization (in-progress/inprogress/current → in_progress)
- Add executed command display in session modal
- Improve UI spacing for compact Jira-style layout
- Move menu button (⋮) to top-right corner of cards
- Replace 📝 icon with subtle ↗ arrow icon

## v0.1.0

- Add FastAPI web UI for viewing and managing Obsidian tasks
- Add vault configuration with support for multiple Obsidian vaults
- Add task filtering by status, phase, and defer dates
- Add Obsidian task reader with frontmatter parsing (status, phase, priority, dates)
- Add "Run Task" button to launch Claude Code sessions via Claude SDK
- Add persistent session UUIDs in task frontmatter (claude_session_id field)
- Add "Resume" buttons for continuing existing Claude sessions
- Add file watching with watchdog for real-time task directory monitoring
- Add WebSocket support for live UI updates without manual refresh
- Add connection status indicator (green/red dot) for WebSocket
- Add asyncio.run_coroutine_threadsafe for thread-safe event broadcasting
- Add comprehensive type hints and mypy type checking
- Add pytest test suite with task reader and API tests
- Add GitHub Actions workflow for CI/CD
