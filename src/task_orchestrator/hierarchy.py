"""Hierarchy folder discovery utilities."""

from pathlib import Path

HIERARCHY_SUFFIXES = ("Themes", "Objectives", "Goals", "Tasks")


def discover_hierarchy_folders(vault_path: Path) -> list[Path]:
    """Discover hierarchy folders under a vault path.

    Matches top-level directories ending with one of:
    - Themes
    - Objectives
    - Goals
    - Tasks

    Examples:
    - "21 Themes", "22 Objectives", "23 Goals", "24 Tasks"
    - "37 Tasks", "40 Tasks"
    - "Tasks", "Goals"
    """
    if not vault_path.exists():
        return []

    folders = [
        entry
        for entry in vault_path.iterdir()
        if entry.is_dir() and any(entry.name.endswith(suffix) for suffix in HIERARCHY_SUFFIXES)
    ]

    category_order = {suffix: idx for idx, suffix in enumerate(HIERARCHY_SUFFIXES)}

    def _sort_key(path: Path) -> tuple[int, int, str]:
        name = path.name
        suffix = next((s for s in HIERARCHY_SUFFIXES if name.endswith(s)), "")
        prefix = name[: -len(suffix)].strip() if suffix else ""
        try:
            numeric_prefix = int(prefix.split()[0]) if prefix else 9999
        except ValueError:
            numeric_prefix = 9999

        return (category_order.get(suffix, 9999), numeric_prefix, name.lower())

    return sorted(folders, key=_sort_key)
