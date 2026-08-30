from __future__ import annotations

from pathlib import Path

from . import doctor, util
from .manifest import Manifest, sha256_of

HOME = Path.home()


class RestoreBlocked(Exception):
    pass


def restore_snapshot(snap_dir: Path, dry_run: bool = False, force: bool = False) -> dict:
    """Restores every file in the snapshot's manifest back to its live
    location under $HOME. Live paths that already match are skipped
    (no-op); anything else is moved aside (never deleted) before the
    snapshot's copy is written in its place.
    """
    issues = doctor.check_snapshot(snap_dir)
    if issues and not force:
        raise RestoreBlocked(
            f"{len(issues)} integrity issue(s) in {snap_dir}, refusing to restore "
            f"(use force=True to override): " + "; ".join(issues[:5])
        )

    manifest = Manifest.from_json((snap_dir / "manifest.json").read_text())
    files_dir = snap_dir / "files"

    restored, skipped_unchanged, moved_aside = [], [], []

    for entry in manifest.entries:
        live = entry.abs_path()
        stored = files_dir / entry.rel_path

        if entry.is_symlink:
            unchanged = live.is_symlink() and str(live.readlink()) == entry.symlink_target
        else:
            unchanged = live.exists() and not live.is_symlink() and sha256_of(live) == entry.sha256

        if unchanged:
            skipped_unchanged.append(entry.rel_path)
            continue

        if dry_run:
            restored.append(entry.rel_path)
            continue

        backup = util.move_aside(live)
        if backup:
            moved_aside.append(str(backup))
        util.copy_into(stored, live)
        restored.append(entry.rel_path)

    return {
        "restored": restored,
        "skipped_unchanged": skipped_unchanged,
        "moved_aside": moved_aside,
        "dry_run": dry_run,
    }
