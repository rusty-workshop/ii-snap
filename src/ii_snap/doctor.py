from __future__ import annotations

from pathlib import Path

from .manifest import Manifest, sha256_of


def check_snapshot(snap_dir: Path) -> list[str]:
    """Verifies a snapshot's own file contents still match its manifest.
    Returns a list of issue strings; empty means clean.
    """
    manifest_path = snap_dir / "manifest.json"
    if not manifest_path.exists():
        return [f"missing manifest.json in {snap_dir}"]

    try:
        manifest = Manifest.from_json(manifest_path.read_text())
    except Exception as e:
        return [f"corrupt manifest.json: {e}"]

    issues = []
    files_dir = snap_dir / "files"
    for entry in manifest.entries:
        stored = files_dir / entry.rel_path
        if not stored.exists() and not stored.is_symlink():
            issues.append(f"missing from snapshot: {entry.rel_path}")
            continue
        if entry.is_symlink:
            if not stored.is_symlink():
                issues.append(f"expected symlink, found regular file: {entry.rel_path}")
            elif str(stored.readlink()) != entry.symlink_target:
                issues.append(f"symlink target mismatch: {entry.rel_path}")
        else:
            if sha256_of(stored) != entry.sha256:
                issues.append(f"checksum mismatch (snapshot corrupted): {entry.rel_path}")
    return issues
