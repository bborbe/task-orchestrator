"""Configuration for TaskOrchestrator."""

from dataclasses import dataclass

from pydantic import Field
from pydantic_settings import BaseSettings


@dataclass
class VaultConfig:
    """Configuration for a single Obsidian vault."""

    name: str
    vault_path: str
    vault_name: str  # For obsidian:// URLs
    tasks_folder: str


class Config(BaseSettings):
    """Application configuration."""

    vaults: list[VaultConfig] = Field(
        default_factory=lambda: [
            VaultConfig(
                name="Personal",
                vault_path="/Users/bborbe/Documents/Obsidian/Personal",
                vault_name="Personal",
                tasks_folder="24 Tasks",
            ),
            VaultConfig(
                name="Brogrammers",
                vault_path="/Users/bborbe/Documents/Obsidian/Brogrammers",
                vault_name="Brogrammers",
                tasks_folder="40 Tasks",
            ),
        ]
    )
    claude_cli: str = Field(default="claude")
    host: str = Field(default="127.0.0.1")
    port: int = Field(default=8000)

    def get_vault(self, name: str) -> VaultConfig | None:
        """Get vault config by name."""
        for vault in self.vaults:
            if vault.name == name:
                return vault
        return None
