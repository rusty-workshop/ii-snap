from __future__ import annotations

from datetime import datetime

from . import discovery
from .manifest import Manifest, build_entry


def scan_live() -> Manifest:
    """Builds a Manifest from the live filesystem right now, writing nothing
    to disk — for diffing "what's actually on disk" against a snapshot
    without needing to take a new one first.
    """
    entries = [build_entry(p) for p in discovery.discover_paths()]
    return Manifest(created_at=datetime.now().isoformat(), entries=entries)
