from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import diff as diffmod
from . import discovery, doctor, live, retention, restore, snapshot
from .manifest import Manifest
from .retention import DEFAULT_BACKUP_ROOT


def _resolve_and_announce(name: str | None, backup_root: Path) -> str:
    resolved, reason = retention.resolve_snapshot(name, backup_root)
    if name is None:
        print(f"No snapshot given — using '{resolved}' ({reason}).")
        if reason == "most recent (none starred)":
            print("Consider `ii-snap star <name>` to pin a known-good snapshot as the default.")
    return resolved


def cmd_snapshot(args):
    backup_root = args.backup_root
    prev = retention.list_snapshots(backup_root)
    snap_dir = snapshot.take_snapshot(backup_root)
    print(f"Snapshot created: {snap_dir.name} ({len(list((snap_dir / 'files').rglob('*')))} files copied)")

    if prev:
        prev_manifest = Manifest.from_json((backup_root / prev[-1] / "manifest.json").read_text())
        new_manifest = Manifest.from_json((snap_dir / "manifest.json").read_text())
        d = diffmod.diff_manifests(prev_manifest, new_manifest)
        if d["added"] or d["removed"] or d["changed"]:
            print("\nChanged since previous snapshot:")
            print(diffmod.render_diff(d))

    removed = retention.prune(backup_root, args.keep)
    if removed:
        print(f"\nPruned {len(removed)} old snapshot(s): {', '.join(removed)}")


def cmd_list(args):
    backup_root = args.backup_root
    star = retention.starred_name(backup_root)
    for name in retention.list_snapshots(backup_root):
        marker = " *" if name == star else ""
        print(name + marker)


def cmd_show(args):
    name = _resolve_and_announce(args.name, args.backup_root)
    manifest = Manifest.from_json((args.backup_root / name / "manifest.json").read_text())
    print(f"{name}: {len(manifest.entries)} paths, created {manifest.created_at}")
    pkg_file = args.backup_root / name / "packages.txt"
    if pkg_file.exists():
        print(f"packages.txt: {len(pkg_file.read_text().splitlines())} explicitly-installed packages")


def cmd_doctor(args):
    backup_root = args.backup_root
    names = retention.list_snapshots(backup_root) if args.all else [_resolve_and_announce(args.name, backup_root)]
    any_issues = False
    star = retention.starred_name(backup_root)
    for name in names:
        issues = doctor.check_snapshot(backup_root / name)
        marker = " *" if name == star else ""
        if issues:
            any_issues = True
            print(f"{name}{marker}: {len(issues)} issue(s)")
            for i in issues:
                print(f"  - {i}")
        else:
            print(f"{name}{marker}: OK")
    sys.exit(1 if any_issues else 0)


def cmd_restore(args):
    backup_root = args.backup_root
    name = _resolve_and_announce(args.name, backup_root)
    try:
        result = restore.restore_snapshot(backup_root / name, dry_run=args.dry_run, force=args.force)
    except restore.RestoreBlocked as e:
        print(f"Refusing to restore: {e}", file=sys.stderr)
        sys.exit(1)

    verb = "Would restore" if args.dry_run else "Restored"
    print(f"{verb} {len(result['restored'])} path(s), {len(result['skipped_unchanged'])} already matched.")
    if result["moved_aside"]:
        print(f"Backed up {len(result['moved_aside'])} live file(s) before overwriting (not deleted):")
        for p in result["moved_aside"][:20]:
            print(f"  {p}")
        if len(result["moved_aside"]) > 20:
            print(f"  ... and {len(result['moved_aside']) - 20} more")


def cmd_diff(args):
    backup_root = args.backup_root
    snaps = retention.list_snapshots(backup_root)
    if args.snap1 and args.snap2:
        n1, n2 = args.snap1, args.snap2
    elif args.snap1:
        n1 = args.snap1
        n2 = _resolve_and_announce(None, backup_root)
    else:
        if len(snaps) < 2:
            print("Need at least 2 snapshots to diff with no arguments.", file=sys.stderr)
            sys.exit(1)
        n1, n2 = snaps[-2], snaps[-1]

    m1 = Manifest.from_json((backup_root / n1 / "manifest.json").read_text())
    m2 = Manifest.from_json((backup_root / n2 / "manifest.json").read_text())
    print(f"Diff: {n1} -> {n2}")
    print(diffmod.render_diff(diffmod.diff_manifests(m1, m2)))


def cmd_diff_live(args):
    backup_root = args.backup_root
    name = _resolve_and_announce(args.name, backup_root)
    snap_manifest = Manifest.from_json((backup_root / name / "manifest.json").read_text())
    live_manifest = live.scan_live()
    print(f"Diff: snapshot '{name}' -> live filesystem")
    print(diffmod.render_diff(diffmod.diff_manifests(snap_manifest, live_manifest)))


def cmd_star(args):
    retention.star(args.backup_root, args.name)
    print(f"Starred: {args.name}")


def cmd_unstar(args):
    retention.unstar(args.backup_root)
    print("Unstarred.")


def cmd_prune(args):
    removed = retention.prune(args.backup_root, args.keep)
    print(f"Removed {len(removed)} snapshot(s)." if removed else "Nothing to prune.")


def build_parser():
    p = argparse.ArgumentParser(prog="ii-snap", description=__doc__ or "Snapshot/restore for illogical-impulse dots")
    p.add_argument("--backup-root", type=Path, default=DEFAULT_BACKUP_ROOT)
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("snapshot", help="take a new snapshot")
    sp.add_argument("--keep", type=int, default=10)
    sp.set_defaults(func=cmd_snapshot)

    sp = sub.add_parser("list", help="list snapshots")
    sp.set_defaults(func=cmd_list)

    sp = sub.add_parser("show", help="show details of a snapshot")
    sp.add_argument("name", nargs="?", default=None)
    sp.set_defaults(func=cmd_show)

    sp = sub.add_parser("doctor", help="verify snapshot integrity")
    sp.add_argument("name", nargs="?", default=None)
    sp.add_argument("--all", action="store_true")
    sp.set_defaults(func=cmd_doctor)

    sp = sub.add_parser("restore", help="restore a snapshot")
    sp.add_argument("name", nargs="?", default=None)
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--force", action="store_true", help="restore even if doctor finds integrity issues")
    sp.set_defaults(func=cmd_restore)

    sp = sub.add_parser("diff", help="diff two snapshots (default: last two)")
    sp.add_argument("snap1", nargs="?", default=None)
    sp.add_argument("snap2", nargs="?", default=None)
    sp.set_defaults(func=cmd_diff)

    sp = sub.add_parser("diff-live", help="diff a snapshot against the live filesystem right now")
    sp.add_argument("name", nargs="?", default=None)
    sp.set_defaults(func=cmd_diff_live)

    sp = sub.add_parser("star", help="pin a snapshot as the default")
    sp.add_argument("name")
    sp.set_defaults(func=cmd_star)

    sp = sub.add_parser("unstar", help="remove the pinned default")
    sp.set_defaults(func=cmd_unstar)

    sp = sub.add_parser("prune", help="delete old snapshots beyond --keep")
    sp.add_argument("--keep", type=int, default=10)
    sp.set_defaults(func=cmd_prune)

    return p


def main():
    args = build_parser().parse_args()
    try:
        args.func(args)
    except discovery.NoListfile as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
