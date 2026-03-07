"""Configuration for TaskOrchestrator."""

import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class VaultConfig:
    """Configuration for a single Obsidian vault."""

    name: str
    vault_path: str
    vault_name: str  # For obsidian:// URLs
    tasks_folder: str
    claude_script: str = "claude"  # Script to run Claude sessions (default: "claude")
    vault_cli_path: str = "vault-cli"  # Path to vault-cli binary


@dataclass
class Config:
    """Application configuration."""

    vaults: list[VaultConfig] = field(default_factory=list)
    claude_cli: str = "claude"
    host: str = "127.0.0.1"
    port: int = 8000

    def get_vault(self, name: str) -> VaultConfig | None:
        """Get vault config by name."""
        for vault in self.vaults:
            if vault.name == name:
                return vault
        return None


_CONFIG_PATH = Path(__file__).parent.parent.parent / "config.yaml"


def load_config(config_path: Path = _CONFIG_PATH) -> Config:
    """Load configuration from config.yaml. Exits with error if not found."""
    if not config_path.exists():
        print(
            f"ERROR: config.yaml not found at {config_path}\n"
            "\nCreate it by copying the example:\n"
            "  cp config.yaml.example config.yaml\n"
            "\nThen edit vault paths to match your system.",
            file=sys.stderr,
        )
        sys.exit(1)

    with config_path.open() as f:
        data = yaml.safe_load(f)

    vaults = [VaultConfig(**v) for v in data.get("vaults", [])]
    return Config(
        vaults=vaults,
        claude_cli=data.get("claude_cli", "claude"),
        host=data.get("host", "127.0.0.1"),
        port=data.get("port", 8000),
    )
