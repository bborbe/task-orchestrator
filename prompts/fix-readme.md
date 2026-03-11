---
status: created
created: "2026-03-11T22:00:00Z"
---
<summary>
- README install command matches actual Makefile target
- Configuration section accurately describes config.yaml instead of nonexistent env vars
- Prerequisites are documented so new contributors can set up quickly
</summary>

<objective>
Fix inaccurate documentation in README.md: wrong make target, misleading env var config section, and missing prerequisites.
</objective>

<context>
Read CLAUDE.md for project conventions.
Read `README.md` — the file to update.
Read `Makefile` — to verify target names (the correct target is `sync`, not `install`).
Read `config.yaml.example` — if it exists, use it to document the actual config format. If not, read `src/task_orchestrator/config.py` for the `Config` dataclass fields.
</context>

<requirements>
1. In the Development section, change `make install` to `make sync`:
   ```
   make sync        # Install dependencies
   ```

2. Replace the Configuration section. The app uses `config.yaml`, not environment variables. Document the actual config format:
   ```markdown
   ## Configuration

   Copy the example config and edit vault paths:
   ```bash
   cp config.yaml.example config.yaml
   ```

   Config fields:
   - `vaults` - List of Obsidian vaults (name, vault_path, vault_name, tasks_folder)
   - `claude_cli` - Claude CLI command (default: `claude`)
   - `host` - Server host (default: `127.0.0.1`)
   - `port` - Server port (default: `8000`)
   ```

3. Add a Prerequisites section before Installation:
   ```markdown
   ## Prerequisites

   - Python 3.12+
   - [uv](https://docs.astral.sh/uv/) package manager
   - [Claude CLI](https://docs.anthropic.com/en/docs/claude-code) (`claude` command)
   - [vault-cli](https://github.com/bborbe/vault-cli) (optional, for fast task operations)
   - An Obsidian vault with tasks in frontmatter format
   ```
   Adjust the vault-cli link if incorrect — check `config.py` for the default path.
</requirements>

<constraints>
- Do NOT commit — dark-factory handles git
- Do NOT change the Features, Task Format, or License sections
- Keep the README concise — no more than ~80 lines total
</constraints>

<verification>
Read the updated README and verify all referenced make targets exist in Makefile.
</verification>
