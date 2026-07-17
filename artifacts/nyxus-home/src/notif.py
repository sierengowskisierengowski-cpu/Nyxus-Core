"""
NYXUS Home — LIVE notifications card (rev r1 · 2026-07-12)
Real feed from `dunstctl history` (the actual dunst daemon history) —
no seeded/fake entries.  Refreshes every 5 s; dismissal removes the
item from dunst's history via `dunstctl history-rm`.
(c) 2026 Joseph A. Sierengowski - NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""
from __future__ import annotations

import json
import re
import subprocess
import threading
import time

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib  # noqa: E402

from style import PALETTE  # noqa: E402
from hud import make_ghost  # noqa: E402

_TAGS = re.compile(r"<[^>]+>")
_APP_COLORS = ["cyan", "gold", "green", "purple", "pink", "orange", "blue"]


def _dv(field):
    """Unwrap dunst's {'type':…, 'data':…} variant wrapper."""
    if isinstance(field, dict):
        return field.get("data")
    return field


class NotificationsCard:
    MAX = 6

    def __init__(self):
        self.root, content, self.set_footer = make_ghost(
            "cyan", "NOTIFICATIONS", "✉")
        self.list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                                spacing=5)
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_child(self.list_box)
        scroller.set_min_content_height(190)
        scroller.set_vexpand(True)
        content.append(scroller)

        self._items = []
        self._busy = False
        GLib.timeout_add(5000, self._poll)
        self._poll()

    def _poll(self):
        if self._busy:
            return True
        self._busy = True
        threading.Thread(target=self._poll_bg, daemon=True).start()
        return True

    def _poll_bg(self):
        items = []
        try:
            out = subprocess.run(["dunstctl", "history"], capture_output=True,
                                 text=True, timeout=5).stdout
            data = json.loads(out)
            for group in _dv(data) or []:
                for n in group:
                    items.append({
                        "id": _dv(n.get("id")),
                        "app": str(_dv(n.get("appname")) or "?"),
                        "summary": str(_dv(n.get("summary")) or ""),
                        "body": _TAGS.sub("", str(_dv(n.get("body")) or "")),
                        "ts": _dv(n.get("timestamp")) or 0,
                    })
        except Exception:
            pass

        def apply():
            self._busy = False
            self._items = items[:self.MAX]
            self._render()
            return False
        GLib.idle_add(apply)

    @staticmethod
    def _age(ts_us):
        # dunst timestamps are CLOCK_BOOTTIME microseconds
        try:
            up = float(open("/proc/uptime").read().split()[0])
            secs = max(0, int(up - ts_us / 1e6))
        except (OSError, ValueError):
            return ""
        if secs < 60:
            return f"{secs}s"
        if secs < 3600:
            return f"{secs // 60}m"
        if secs < 86400:
            return f"{secs // 3600}h"
        return f"{secs // 86400}d"

    def _dismiss(self, _b, nid):
        subprocess.Popen(["dunstctl", "history-rm", str(nid)],
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
        self._items = [n for n in self._items if n["id"] != nid]
        self._render()

    def _render(self):
        child = self.list_box.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self.list_box.remove(child)
            child = nxt

        if not self._items:
            empty = Gtk.Label(label="inbox zero · dunst history clear")
            empty.add_css_class("hud-dim-note")
            empty.set_xalign(0.0)
            self.list_box.append(empty)
        for n in self._items:
            ck = _APP_COLORS[hash(n["app"]) % len(_APP_COLORS)]
            chex = PALETTE[ck]
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            row.add_css_class(f"notif-{ck if ck != 'blue' else 'cyan'}")
            mid = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
            mid.set_hexpand(True)
            head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            title = Gtk.Label(xalign=0.0)
            title.set_ellipsize(3)
            title.set_markup(
                f"<span foreground='{chex}' font_desc='Inter Display Bold 10'>"
                f"{GLib.markup_escape_text(n['app'])}</span>  "
                f"<span foreground='{PALETTE['text']}' "
                f"font_desc='Inter Display 10'>"
                f"{GLib.markup_escape_text(n['summary'][:60])}</span>")
            title.set_hexpand(True)
            head.append(title)
            t = Gtk.Label(label=self._age(n["ts"]))
            t.add_css_class("notif-time")
            head.append(t)
            mid.append(head)
            if n["body"]:
                body = Gtk.Label(label=n["body"][:110], xalign=0.0)
                body.set_wrap(True)
                body.add_css_class("notif-body")
                mid.append(body)
            row.append(mid)
            x = Gtk.Button(label="✕")
            x.add_css_class("btn-icon-mono")
            x.set_valign(Gtk.Align.CENTER)
            x.connect("clicked", self._dismiss, n["id"])
            row.append(x)
            self.list_box.append(row)
        self.set_footer(f"{len(self._items)} SHOWN · DUNSTCTL HISTORY · 5S")
