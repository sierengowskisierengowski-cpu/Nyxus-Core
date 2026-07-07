#!/usr/bin/env python3
"""Enrich nyxus-dockd JSON lines with resolved icon_path for eww :image :path."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

SIZE = int(os.environ.get("NYXUS_DOCK_ICON_SIZE", "48"))
THEMES = os.environ.get(
    "GTK_ICON_THEME", "NYXUS-Dark:NYXUS-Aurora:Adwaita:hicolor"
).split(":")

ICON_DIRS = ("apps", "status", "places", "devices", "mimetypes")
SUBDIRS = (
    f"{SIZE}x{SIZE}",
    "scalable",
    "48x48",
    "32x32",
    "24x24",
    "symbolic",
)


def _bases() -> list[Path]:
    out: list[Path] = []
    home = Path.home()
    for p in (
        home / ".local/share/icons",
        home / ".icons",
        Path("/usr/share/icons"),
        Path("/usr/local/share/icons"),
    ):
        if p.is_dir():
            out.append(p)
    return out


def resolve_icon(name: str) -> str:
    if not name or name in ("null", "None"):
        return ""
    if name.startswith("/") and Path(name).is_file():
        return name

    stem = Path(name).stem
    bases = _bases()
    exts = (".svg", ".png", ".xpm")

    for theme in THEMES:
        for base in bases:
            theme_dir = base / theme
            if not theme_dir.is_dir():
                continue
            for sub in SUBDIRS:
                for cat in ICON_DIRS:
                    for ext in exts:
                        for candidate in (name, stem):
                            p = theme_dir / sub / cat / f"{candidate}{ext}"
                            if p.is_file():
                                return str(p.resolve())
    return ""


def _enrich_obj(obj: dict) -> None:
    icon = obj.get("icon") or ""
    obj["icon_path"] = resolve_icon(str(icon))


def enrich(state: dict) -> dict:
    for entry in state.get("entries") or []:
        if isinstance(entry, dict):
            _enrich_obj(entry)
    for stack in state.get("stacks") or []:
        if isinstance(stack, dict):
            _enrich_obj(stack)
    trash = state.get("trash")
    if isinstance(trash, dict):
        _enrich_obj(trash)
    return state


def main() -> int:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            state = json.loads(line)
        except json.JSONDecodeError:
            print(line, flush=True)
            continue
        print(json.dumps(enrich(state), separators=(",", ":")), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
