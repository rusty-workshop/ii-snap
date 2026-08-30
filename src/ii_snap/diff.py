from __future__ import annotations

from .manifest import Manifest


def diff_manifests(a: Manifest, b: Manifest) -> dict:
    """Diffs manifest `a` (older) against `b` (newer). Symlinks are compared
    by target, regular files by sha256 — content, not mtime, so a
    touch-without-edit never shows up as a false change.
    """
    a_by_path = {e.rel_path: e for e in a.entries}
    b_by_path = {e.rel_path: e for e in b.entries}

    added = sorted(set(b_by_path) - set(a_by_path))
    removed = sorted(set(a_by_path) - set(b_by_path))
    changed = []
    for rel in sorted(set(a_by_path) & set(b_by_path)):
        ea, eb = a_by_path[rel], b_by_path[rel]
        if ea.is_symlink or eb.is_symlink:
            if ea.symlink_target != eb.symlink_target or ea.is_symlink != eb.is_symlink:
                changed.append(rel)
        elif ea.sha256 != eb.sha256:
            changed.append(rel)

    return {"added": added, "removed": removed, "changed": changed}


def render_diff(d: dict) -> str:
    if not d["added"] and not d["removed"] and not d["changed"]:
        return "No differences."
    lines = []
    if d["added"]:
        lines.append(f"{len(d['added'])} path(s) added:")
        lines += [f"  + {p}" for p in d["added"]]
    if d["removed"]:
        lines.append(f"{len(d['removed'])} path(s) removed:")
        lines += [f"  - {p}" for p in d["removed"]]
    if d["changed"]:
        lines.append(f"{len(d['changed'])} path(s) changed:")
        lines += [f"  ~ {p}" for p in d["changed"]]
    return "\n".join(lines)
