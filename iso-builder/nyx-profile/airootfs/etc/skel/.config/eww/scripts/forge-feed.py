#!/usr/bin/env python3
"""
NYXUS · EWW · FORGE station feed  (Build · Code · Ship)

Repo state across ~/Projects, plus recent commit activity and open PRs.

PERF: `git status` across ~20 repos is far too slow for a poll, so results are
CACHED (60s) and every git call is short-timeout. The deck polls the cache.
This is the same lesson as the START app catalogue, which froze the search
box by re-scanning on every keystroke.
"""
import json
import os
import subprocess
import time
from pathlib import Path

HOME = Path.home()
ROOT = HOME / "Projects"
CACHE = HOME / ".cache" / "nyxus-forge.json"
TTL = 60


def _git(repo, args, timeout=4):
    try:
        return subprocess.run(["git", "-C", str(repo)] + args,
                              capture_output=True, text=True,
                              timeout=timeout).stdout.strip()
    except Exception:
        return ""


def repos():
    rows = []
    if not ROOT.is_dir():
        return rows
    for d in sorted(ROOT.iterdir()):
        if not (d / ".git").exists():
            continue
        branch = _git(d, ["branch", "--show-current"]) or "detached"
        porcelain = _git(d, ["status", "--porcelain"])
        dirty = len([l for l in porcelain.splitlines() if l.strip()])
        # ahead/behind vs upstream, when there is one
        ahead = behind = 0
        ab = _git(d, ["rev-list", "--left-right", "--count", "@{u}...HEAD"])
        if ab and "\t" in ab:
            try:
                behind, ahead = (int(x) for x in ab.split("\t")[:2])
            except Exception:
                pass
        last = _git(d, ["log", "-1", "--format=%cr|%s"])
        when, _, subject = last.partition("|")
        rows.append({
            "name": d.name[:20],
            "path": str(d),
            "branch": branch[:18],
            "dirty": dirty,
            "ahead": ahead,
            "behind": behind,
            "when": when[:14] or "-",
            "subject": subject[:40],
            "clean": dirty == 0 and ahead == 0,
        })
    return rows


def prs():
    """Open PRs the owner authored. gh is network-bound, so it gets the
    longest timeout here and degrades to an empty list rather than stalling."""
    try:
        out = subprocess.run(
            ["gh", "search", "prs", "--author", "@me", "--state", "open",
             "--limit", "6", "--json", "title,repository,number"],
            capture_output=True, text=True, timeout=8).stdout
        data = json.loads(out) if out.strip() else []
        return [{"n": str(p.get("number", "")),
                 "repo": (p.get("repository", {}) or {}).get("name", "")[:16],
                 "title": (p.get("title") or "")[:34]} for p in data]
    except Exception:
        return []


def build():
    rows = repos()
    dirty = [r for r in rows if r["dirty"] > 0]
    unpushed = [r for r in rows if r["ahead"] > 0]
    # most recently touched first, by mtime of the repo's git dir
    rows_sorted = sorted(
        rows, key=lambda r: os.path.getmtime(Path(r["path"]) / ".git"),
        reverse=True)
    return {
        "repos": rows_sorted[:12],
        "total": len(rows),
        "dirty": len(dirty),
        "dirty_rows": dirty[:6],
        "unpushed": len(unpushed),
        "unpushed_rows": unpushed[:6],
        "prs": prs(),
    }


if __name__ == "__main__":
    fallback = {"repos": [], "total": 0, "dirty": 0, "dirty_rows": [],
                "unpushed": 0, "unpushed_rows": [], "prs": []}
    try:
        if CACHE.exists() and time.time() - CACHE.stat().st_mtime < TTL:
            print(CACHE.read_text())
        else:
            data = build()
            CACHE.parent.mkdir(parents=True, exist_ok=True)
            CACHE.write_text(json.dumps(data))
            print(json.dumps(data))
    except Exception:
        print(json.dumps(fallback))
