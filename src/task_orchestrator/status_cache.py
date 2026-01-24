"""In-memory cache for task/goal/theme statuses."""

import logging
import re
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


class StatusCache:
    """In-memory cache of task/goal/theme statuses for fast blocker resolution."""

    def __init__(self) -> None:
        """Initialize empty cache."""
        self._cache: dict[str, dict[str, str]] = {}
        self._vault_paths: dict[str, Path] = {}

    def load_vault(self, vault_name: str, vault_path: Path) -> None:
        """Load/reload all items from vault folders (21-24).

        Idempotent - safe to call multiple times.

        Args:
            vault_name: Name of the vault (e.g., "Personal")
            vault_path: Path to vault root directory
        """
        cache: dict[str, str] = {}  # Start fresh each time

        # Scan all hierarchy folders for items with status
        for folder in ["21 Themes", "22 Objectives", "23 Goals", "24 Tasks"]:
            folder_path = vault_path / folder
            if not folder_path.exists():
                logger.warning(f"[StatusCache] Folder not found: {folder_path}")
                continue

            for md_file in folder_path.rglob("*.md"):
                item_id = md_file.stem
                status = self._extract_status(md_file)
                if status:
                    cache[item_id] = status

        # Atomic replacement (overwrites previous cache)
        self._cache[vault_name] = cache
        self._vault_paths[vault_name] = vault_path
        logger.info(f"[StatusCache] Loaded {len(cache)} items for vault '{vault_name}'")

    def _extract_status(self, file_path: Path) -> str | None:
        """Fast status extraction from frontmatter.

        Args:
            file_path: Path to markdown file

        Returns:
            Status string if found, None otherwise
        """
        try:
            content = file_path.read_text(encoding="utf-8")
            match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
            if match:
                frontmatter = yaml.safe_load(match.group(1))
                if isinstance(frontmatter, dict):
                    return frontmatter.get("status")
            return None
        except Exception as e:
            logger.debug(f"[StatusCache] Failed to extract status from {file_path.name}: {e}")
            return None

    def get_status(self, vault_name: str, item_id: str) -> str | None:
        """Get status for item (task/goal/theme/objective).

        Args:
            vault_name: Name of the vault
            item_id: Item ID (filename without .md extension)

        Returns:
            Status string if found, None otherwise
        """
        return self._cache.get(vault_name, {}).get(item_id)

    def invalidate(self, vault_name: str, item_id: str) -> None:
        """Invalidate single item - reload from disk.

        Called by file watcher when item is modified/created/deleted.

        Args:
            vault_name: Name of the vault
            item_id: Item ID (filename without .md extension)
        """
        vault_path = self._vault_paths.get(vault_name)
        if not vault_path:
            logger.warning(f"[StatusCache] Unknown vault for invalidation: {vault_name}")
            return

        # Search for file in 21-24 folders
        for folder in ["21 Themes", "22 Objectives", "23 Goals", "24 Tasks"]:
            md_file = vault_path / folder / f"{item_id}.md"
            if md_file.exists():
                status = self._extract_status(md_file)
                if status:
                    if vault_name not in self._cache:
                        self._cache[vault_name] = {}
                    self._cache[vault_name][item_id] = status
                    logger.debug(f"[StatusCache] Updated '{item_id}' → status: {status}")
                else:
                    # Status field removed or invalid - remove from cache
                    self._cache.get(vault_name, {}).pop(item_id, None)
                    logger.debug(f"[StatusCache] Removed '{item_id}' (no valid status)")
                return

        # File deleted or moved - remove from cache
        if vault_name in self._cache:
            self._cache[vault_name].pop(item_id, None)
            logger.debug(f"[StatusCache] Removed '{item_id}' (file not found)")
