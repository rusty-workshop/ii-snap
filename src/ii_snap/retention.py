from __future__ import annotations

import shutil
from pathlib import Path

DEFAULT_BACKUP_ROOT = Path.home() / "Backups" / "ii-snap"


def list_snapshots(backup_root: Path) -> list[str]:
    if not backup_root.exists():
        return []
    return sorted(
        p.name for p in backup_root.iterdir()
        if p.is_dir() and (p / "manifest.json").exists()
    )


def starred_name(backup_root: Path) -> str | None:
    star_file = backup_root / ".starred"
    if star_file.exists():
        name = star_file.read_text().strip()
        if name and (backup_root / name / "manifest.json").exists():
            return name
    return None


def star(backup_root: Path, name: str) -> None:
    if not (backup_root / name / "manifest.json").exists():
        raise FileNotFoundError(f"no such snapshot: {name}")
    (backup_root / ".starred").write_text(name)


def unstar(backup_root: Path) -> None:
    star_file = backup_root / ".starred"
    if star_file.exists():
        star_file.unlink()


def resolve_snapshot(name: str | None, backup_root: Path) -> tuple[str, str]:
    """Returns (resolved_name, reason). Raises FileNotFoundError if nothing to resolve to."""
    if name:
        if not (backup_root / name / "manifest.json").exists():
            raise FileNotFoundError(f"no such snapshot: {name}")
        return name, "explicitly requested"

    star = starred_name(backup_root)
    if star:
        return star, "starred"

    snaps = list_snapshots(backup_root)
    if not snaps:
        raise FileNotFoundError(f"no snapshots found under {backup_root}")
    return snaps[-1], "most recent (none starred)"


def prune(backup_root: Path, keep: int) -> list[str]:
    """Deletes all but the `keep` most recent snapshots. Starred snapshot is exempt."""
    snaps = list_snapshots(backup_root)
    star = starred_name(backup_root)
    removable = [s for s in snaps if s != star]
    to_remove = removable[: max(0, len(removable) - keep)]
    for name in to_remove:
        shutil.rmtree(backup_root / name)
    return to_remove
