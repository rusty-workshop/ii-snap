from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path


def move_aside(path: Path) -> Path | None:
    """Moves an existing path to <path>.pre-restore-<timestamp>[-N].

    Collision-safe: appends -1, -2, ... if the timestamp-based name is
    already taken. caelback hit a real data-loss bug from a
    second-granularity timestamp colliding on two move_asides within the
    same wall-clock second — this avoids repeating that mistake.
    Returns the backup path, or None if `path` didn't exist.
    """
    if not path.exists() and not path.is_symlink():
        return None
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    candidate = path.with_name(f"{path.name}.pre-restore-{ts}")
    n = 1
    while candidate.exists() or candidate.is_symlink():
        candidate = path.with_name(f"{path.name}.pre-restore-{ts}-{n}")
        n += 1
    shutil.move(str(path), str(candidate))
    return candidate


def copy_into(src: Path, dest: Path) -> None:
    """Copies src to dest, preserving symlinks as symlinks (not their target's
    content) — real snapshots here include things like the wallpaper-path
    symlink some tools use, and dereferencing it would silently swap
    "record which file is selected" for "record a snapshot of file content
    at that moment," a different and wrong thing to capture.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() or dest.is_symlink():
        dest.unlink()
    if src.is_symlink():
        dest.symlink_to(src.readlink())
    else:
        shutil.copy2(src, dest, follow_symlinks=False)
