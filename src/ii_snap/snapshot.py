from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path

from . import discovery, util
from .manifest import Manifest, build_entry


def take_snapshot(backup_root: Path) -> Path:
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    snap_dir = backup_root / ts
    files_dir = snap_dir / "files"
    files_dir.mkdir(parents=True)

    paths = discovery.discover_paths()
    entries = []
    for p in paths:
        entry = build_entry(p)
        util.copy_into(p, files_dir / entry.rel_path)
        entries.append(entry)

    manifest = Manifest(created_at=datetime.now().isoformat(), entries=entries)
    (snap_dir / "manifest.json").write_text(manifest.to_json())

    # Informational only — never auto-reinstalled by restore. Lets Rusty see
    # at a glance what was explicitly installed at snapshot time, without
    # ii-snap taking on caelback's package-tarball-caching complexity for a
    # desktop tool that isn't really about surviving a full reinstall.
    try:
        result = subprocess.run(
            ["pacman", "-Qqe"], capture_output=True, text=True, timeout=30, check=True
        )
        (snap_dir / "packages.txt").write_text(result.stdout)
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        pass

    return snap_dir
