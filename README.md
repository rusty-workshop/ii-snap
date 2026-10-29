# ii-snap

Snapshot/restore for illogical-impulse (end-4/dots-hyprland) — the
[caelback](https://github.com/rusty-workshop/caelback) tool did this job for Caelestia, but caelback is Caelestia-
specific and is now inactive since the move to ii. This is a from-scratch
rebuild for the current dots, using a genuinely better foundation:
Caelestia never shipped an installer manifest, so caelback had to
*guess* what belonged to it via a fuzzy "does this path contain
'caelestia'" scan. ii's installer writes its own file list to
`~/.config/illogical-impulse/installed_listfile` — ii-snap reads that
directly as ground truth instead of guessing.

AGPL-3.0-or-later. Python 3.12, stdlib-only, `uv`-managed with a `src/`
layout (same convention as caelback/livewall).

## What it tracks

- Every file in `installed_listfile` that actually exists on disk
  (~1170 files: `~/.config/hypr`, `~/.config/quickshell/ii`, fonts,
  shell config, etc.)
- Plus a few files ii mutates at runtime that the installer doesn't list:
  `~/.config/illogical-impulse/config.json` (wallpaper path, theming,
  every UI toggle), `~/.config/caelestia/cli.json` (special-workspace
  app bindings, which ii still reads even without Caelestia installed)
- Symlinks are preserved as symlinks (not dereferenced) — matters for
  anything that records "which file is currently selected" via a symlink
  rather than storing the content directly
- Directory entries in the listfile (e.g. a font that was vendored in via
  `git clone`) are skipped as directories — their files are separately
  listed already, and their `.git/` internals are deliberately excluded
  everywhere (re-fetchable, not user state, and were bloating snapshots
  with megabytes of git objects for zero benefit)

**Not tracked**: installed packages (a `packages.txt` list is saved
per-snapshot for reference, but never auto-reinstalled — this is a config
tool, not a full-system restore tool) or anything outside `$HOME`.

## Commands

```bash
ii-snap snapshot [--keep N]      # take a snapshot, prune beyond --keep (default 10)
ii-snap list                     # list snapshots, * marks the starred one
ii-snap show [name]              # details; defaults to starred/latest
ii-snap doctor [name] [--all]    # verify a snapshot's own files aren't corrupted
ii-snap diff [snap1] [snap2]     # diff two snapshots; no args = last two taken
ii-snap diff-live [name]         # diff a snapshot against the live filesystem right now
ii-snap restore [name] [--dry-run] [--force]
ii-snap star <name> / unstar     # pin a known-good snapshot as the default
ii-snap prune [--keep N]
```

`restore` never deletes: anything it's about to overwrite gets moved to
`<path>.pre-restore-<timestamp>` first (collision-safe naming — a lesson
carried over directly from a real caelback bug where two same-second
move-asides silently destroyed a backup). It also refuses to restore from
a snapshot `doctor` finds corrupted unless you pass `--force`.

`--backup-root` (before the subcommand, e.g.
`ii-snap --backup-root /path snapshot`) overrides the default
`~/Backups/ii-snap` — deliberately defined only once on the top-level
parser rather than duplicated on every subparser, to avoid the exact
argparse footgun caelback hit (a flag on a shared parent parser silently
resets to its default when the subparser also defines it).

## Status

Installed and running on this machine as of 2026-08-30: `uv tool install
--editable .`, first real snapshot taken and starred
(`2026-08-30_115434`, 1174 files, `doctor` clean), weekly
`ii-snap.timer` enabled via `systemctl --user`. Every command was run
live against the real system during development (not just unit-tested) —
`snapshot`, `list`, `show`, `star`, `doctor`, `doctor --all`,
`diff-live` (confirmed clean immediately after a snapshot), and
`restore --dry-run` (confirmed 0 changes needed, matching a system that
hadn't drifted since the snapshot).

**Not yet exercised**: a real `restore` onto genuinely-changed live files
(would require an actual dothop or config drift to test against safely —
same reasoning caelback used for not testing its own restore path against
synthetic no-op state). If a future dothop or bad config change happens,
that's the moment to actually run it for real.
