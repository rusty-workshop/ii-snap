from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from pathlib import Path

HOME = Path.home()


@dataclass
class Entry:
    rel_path: str  # path relative to $HOME, forward-slash, e.g. ".config/hypr/hyprland.lua"
    size: int
    sha256: str | None  # None for symlinks and unreadable files
    is_symlink: bool
    symlink_target: str | None  # only set if is_symlink

    def abs_path(self) -> Path:
        return HOME / self.rel_path


@dataclass
class Manifest:
    created_at: str
    entries: list[Entry]

    def to_json(self) -> str:
        return json.dumps(
            {"created_at": self.created_at, "entries": [asdict(e) for e in self.entries]},
            indent=2,
        )

    @classmethod
    def from_json(cls, text: str) -> "Manifest":
        data = json.loads(text)
        return cls(
            created_at=data["created_at"],
            entries=[Entry(**e) for e in data["entries"]],
        )


class ManifestBroken(Exception):
    pass


def load_manifest_safe(manifest_path: Path) -> Manifest:
    if not manifest_path.exists():
        raise ManifestBroken(f"missing manifest: {manifest_path}")
    try:
        return Manifest.from_json(manifest_path.read_text())
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        raise ManifestBroken(f"corrupt manifest {manifest_path}: {e}") from e


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build_entry(path: Path) -> Entry:
    rel = str(path.relative_to(HOME))
    if path.is_symlink():
        target = str(path.readlink())
        return Entry(rel_path=rel, size=0, sha256=None, is_symlink=True, symlink_target=target)
    size = path.stat().st_size
    digest = sha256_of(path)
    return Entry(rel_path=rel, size=size, sha256=digest, is_symlink=False, symlink_target=None)
