"""Finds what to snapshot.

Ground truth is the ii installer's own manifest
(~/.config/illogical-impulse/installed_listfile), NOT a fuzzy name-based
scan — this is a real improvement over caelback's approach for Caelestia,
which had no equivalent installer manifest to read and had to guess by
path substring instead.
"""
from __future__ import annotations

from pathlib import Path

LISTFILE = Path.home() / ".config/illogical-impulse/installed_listfile"

# Files the installer doesn't track (because ii itself creates/mutates
# them at runtime) but that hold real user state worth protecting.
EXTRA_PATHS = [
    Path.home() / ".config/illogical-impulse/config.json",
    Path.home() / ".config/illogical-impulse/installed_listfile",
    Path.home() / ".config/illogical-impulse/installed_true",
    Path.home() / ".config/caelestia/cli.json",  # special-workspace toggles, see memory
]


class NoListfile(Exception):
    pass


def discover_paths() -> list[Path]:
    """Returns every real, currently-existing path that should be snapshotted.

    Entries in the listfile that no longer exist on disk are silently
    skipped (the installer can list optional-feature files that were
    never actually written on this machine) rather than treated as an
    error — matches caelback's discovery.py existence-gating pattern.
    """
    if not LISTFILE.exists():
        raise NoListfile(
            f"{LISTFILE} not found — is this actually an illogical-impulse "
            "install? ii-snap only knows how to discover files via this "
            "installer manifest."
        )

    paths: set[Path] = set()
    for line in LISTFILE.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        p = Path(line)
        _maybe_add(p, paths)

    for p in EXTRA_PATHS:
        _maybe_add(p, paths)

    return sorted(paths)


def _maybe_add(p: Path, paths: set[Path]) -> None:
    # Directory entries in the listfile (e.g. a font asset that was
    # `git clone`d in as a whole dir) are skipped: files inside are still
    # individually listed, and blindly recursing into the dir itself would
    # also pull in .git internals below — see the ".git/" skip below.
    if p.is_symlink():
        paths.add(p)
        return
    if not p.exists() or p.is_dir():
        return
    if ".git" in p.parts:
        # Vendored git clones (e.g. a font installed by `git clone`) — the
        # asset files themselves are separately listed; their .git history
        # is re-fetchable and not user state worth snapshotting.
        return
    paths.add(p)
