# Changelog

All notable changes to this project will be documented in this file.

Please choose versions by [Semantic Versioning](http://semver.org/).

* MAJOR version when you make incompatible API changes,
* MINOR version when you add functionality in a backwards-compatible manner, and
* PATCH version when you make backwards-compatible bug fixes.

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
