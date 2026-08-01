#!/usr/bin/env python3
"""
Rewrite the file_permissions array in an archiso profiledef.sh from the
profile's actual airootfs.

WHY THIS EXISTS
---------------
mkarchiso copies airootfs with --no-preserve=mode. The ONLY thing that puts an
executable bit back on the shipped image is an entry in file_permissions. That
array was hand-maintained, and on the 2026-07-31 ISO 116 executables were
missing from it -- including nyxus-consoles (the ARSENAL station launcher),
sharknoc (MESH), nyxus-home-deck (the station-to-deck watcher), every script in
~/.config/eww/scripts (all the deck feeds and bar pollers) and every script in
~/.config/hypr/scripts. They all shipped mode 644 and could not run. Nothing in
the build warned, because a 644 file is a perfectly valid file.

A hand-maintained mirror of a directory tree will always drift. This derives
the array instead. build-iso.sh runs it against the throwaway profile copy
AFTER staging, so files that only exist at bake time (the eww scripts, the Meli
venv, Bifrost, Arsenal) are covered too -- not just what is committed.

Entries whose mode is not 755, and entries pointing at directories, are treated
as hand-pinned and carried through untouched (/root 750, sudoers 440, ...).

Usage:
  regen-file-permissions.py [--profile DIR] [--check]

  --check  exit 1 and print the diff instead of writing (used by CI/verify).

(c) 2026 JOSEPH A. SIERENGOWSKI - NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENTRY_RE = re.compile(r'^\s*\["(?P<path>[^"]+)"\]="(?P<mode>[^"]+)"\s*$')

HEADER = """file_permissions=(
  # ── GENERATED — do not hand-edit the 0:0:755 block ────────────────────────
  # Regenerate with:  iso-builder/regen-file-permissions.py
  # build-iso.sh also regenerates this in the throwaway profile copy after
  # staging, so bake-time-only files are covered. archiso copies airootfs with
  # --no-preserve=mode, so anything executable that is missing here ships 644
  # and silently cannot run.
  #
  # Entries above the generated block are hand-pinned (non-755 modes and
  # directories) and are preserved by the regenerator.
"""


def read_entries(profiledef: Path) -> tuple[list[str], dict[str, str], list[str]]:
    """Split profiledef.sh into (lines before array, entries, lines after)."""
    lines = profiledef.read_text(encoding="utf-8").splitlines(keepends=True)
    start = end = None
    for i, line in enumerate(lines):
        if start is None and line.startswith("file_permissions=("):
            start = i
        elif start is not None and line.rstrip() == ")":
            end = i
            break
    if start is None or end is None:
        raise SystemExit(f"{profiledef}: could not find a file_permissions=( ... ) block")

    entries: dict[str, str] = {}
    for line in lines[start + 1 : end]:
        m = ENTRY_RE.match(line)
        if m:
            entries[m.group("path")] = m.group("mode")
    return lines[:start], entries, lines[end + 1 :]


def build_block(airootfs: Path, existing: dict[str, str]) -> tuple[str, list[str]]:
    warnings: list[str] = []

    pinned: dict[str, str] = {}
    for path, mode in existing.items():
        target = airootfs / path.lstrip("/")
        if not target.exists():
            warnings.append(f"dropping {path}: pinned in profiledef.sh but not in airootfs")
            continue
        # 0:0:755 on a regular file that IS executable on disk is exactly what
        # the generator produces, so let it be regenerated. A 755 entry on a
        # file that is NOT executable in the repo is a deliberate promotion —
        # /root/customize_airootfs.sh is the load-bearing example, since git
        # checkouts lose modes and mkarchiso must still be able to run it — so
        # keep it pinned. Dropping those would silently un-promote them.
        if (
            mode == "0:0:755"
            and target.is_file()
            and not target.is_symlink()
            and target.stat().st_mode & 0o111
        ):
            continue
        pinned[path] = mode

    generated: dict[str, str] = {}
    for dirpath, _dirnames, filenames in os.walk(airootfs):
        for name in filenames:
            fp = Path(dirpath) / name
            if fp.is_symlink():
                continue  # chmod follows the link; the target is handled on its own
            try:
                mode = fp.stat().st_mode
            except OSError:
                continue
            if not mode & 0o111:
                continue
            rel = "/" + str(fp.relative_to(airootfs))
            if rel in pinned:
                continue
            generated[rel] = "0:0:755"

    out = [HEADER]
    for path in sorted(pinned):
        out.append(f'  ["{path}"]="{pinned[path]}"\n')
    out.append("\n")
    for path in sorted(generated):
        out.append(f'  ["{path}"]="0:0:755"\n')
    out.append(")\n")
    return "".join(out), warnings


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default=str(HERE / "nyx-profile"))
    ap.add_argument("--check", action="store_true",
                    help="exit non-zero if the array is out of date instead of writing")
    args = ap.parse_args()

    profile = Path(args.profile).resolve()
    profiledef = profile / "profiledef.sh"
    airootfs = profile / "airootfs"
    if not profiledef.is_file():
        raise SystemExit(f"no profiledef.sh under {profile}")
    if not airootfs.is_dir():
        raise SystemExit(f"no airootfs under {profile}")

    before, existing, after = read_entries(profiledef)
    block, warnings = build_block(airootfs, existing)
    for w in warnings:
        print(f"[WARN] {w}", file=sys.stderr)

    new_text = "".join(before) + block + "".join(after)
    old_text = profiledef.read_text(encoding="utf-8")

    if new_text == old_text:
        print(f"[OK] file_permissions up to date ({block.count('0:0:755')} executables)")
        return 0

    if args.check:
        old_paths = set(existing)
        new_paths = set(ENTRY_RE.match(l).group("path")  # type: ignore[union-attr]
                        for l in block.splitlines(keepends=True) if ENTRY_RE.match(l))
        for p in sorted(new_paths - old_paths):
            print(f"[FAIL] missing from file_permissions (would ship 644): {p}")
        for p in sorted(old_paths - new_paths):
            print(f"[FAIL] stale entry in file_permissions: {p}")
        return 1

    profiledef.write_text(new_text, encoding="utf-8")
    print(f"[OK] rewrote file_permissions ({block.count('0:0:755')} executables)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
