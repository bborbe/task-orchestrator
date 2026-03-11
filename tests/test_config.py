"""Tests for config loading."""

import textwrap
from pathlib import Path

import pytest

from task_orchestrator.config import load_config


def test_load_config_reads_vaults(tmp_path: Path) -> None:
    """load_config parses vaults from YAML."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        textwrap.dedent("""\
            vaults:
              - name: Personal
                vault_path: /some/path/Personal
                vault_name: Personal
                tasks_folder: "24 Tasks"
                claude_script: claude-personal.sh
        """)
    )
    config = load_config(config_file)
    assert len(config.vaults) == 1
    vault = config.vaults[0]
    assert vault.name == "Personal"
    assert vault.vault_path == "/some/path/Personal"
    assert vault.vault_name == "Personal"
    assert vault.tasks_folder == "24 Tasks"
    assert vault.claude_script == "claude-personal.sh"


def test_load_config_multiple_vaults(tmp_path: Path) -> None:
    """load_config parses multiple vaults."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        textwrap.dedent("""\
            vaults:
              - name: A
                vault_path: /a
                vault_name: A
                tasks_folder: Tasks
              - name: B
                vault_path: /b
                vault_name: B
                tasks_folder: Tasks
        """)
    )
    config = load_config(config_file)
    assert len(config.vaults) == 2
    assert config.vaults[0].name == "A"
    assert config.vaults[1].name == "B"


def test_load_config_defaults(tmp_path: Path) -> None:
    """load_config uses defaults for optional fields."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("vaults: []\n")
    config = load_config(config_file)
    assert config.claude_cli == "claude"
    assert config.host == "127.0.0.1"
    assert config.port == 8000


def test_load_config_optional_overrides(tmp_path: Path) -> None:
    """load_config respects optional overrides."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        textwrap.dedent("""\
            vaults: []
            claude_cli: /usr/local/bin/claude
            host: 0.0.0.0
            port: 9000
        """)
    )
    config = load_config(config_file)
    assert config.claude_cli == "/usr/local/bin/claude"
    assert config.host == "0.0.0.0"
    assert config.port == 9000


def test_load_config_missing_file_raises(tmp_path: Path) -> None:
    """load_config raises FileNotFoundError when config.yaml is missing."""
    with pytest.raises(FileNotFoundError, match=r"config\.yaml not found"):
        load_config(tmp_path / "nonexistent.yaml")


def test_get_vault_returns_correct_vault(tmp_path: Path) -> None:
    """Config.get_vault finds vault by name."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        textwrap.dedent("""\
            vaults:
              - name: Personal
                vault_path: /personal
                vault_name: Personal
                tasks_folder: Tasks
              - name: Work
                vault_path: /work
                vault_name: Work
                tasks_folder: Tasks
        """)
    )
    config = load_config(config_file)
    assert config.get_vault("Personal") is not None
    assert config.get_vault("Personal").vault_path == "/personal"  # type: ignore[union-attr]
    assert config.get_vault("Work") is not None
    assert config.get_vault("Missing") is None
