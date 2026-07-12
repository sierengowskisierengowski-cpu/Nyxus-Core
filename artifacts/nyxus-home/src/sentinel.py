"""
NYXUS Home — SENTINEL row (rev r1 · 2026-07-12)
Live security telemetry, zero mock data:

  JettCard      — jeTT AI EDR: daemon state via systemd, mode from
                  /etc/default/jett, verdict totals seeded by a one-shot
                  background grep of /var/log/jett/jett.log, then kept
                  live by incremental tail (byte-offset follow).  Live
                  events/min sparkline + latest flagged processes.

  HoneypotCard  — docker honeypot fleet (cowrie, endlessh, heralding,
                  dionaea, conpot, http-honeypot…) health from
                  `docker ps`, plus a live attack feed scraped from
                  `docker logs --since` of the noisy pots.

(c) 2026 Joseph Sierengowski - NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""
from __future__ import annotations

import math
import os
import re
import subprocess
import threading
import time
from collections import deque

import cairo
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib  # noqa: E402

from style import PALETTE  # noqa: E402
from hud import make_ghost, GlowSpark, _rgb  # noqa: E402

JETT_LOG = os.environ.get("JETT_LOG", "/var/log/jett/jett.log")
JETT_DEFAULTS = "/etc/default/jett"
JETT_SERVICE = "jett-daemon.service"

POT_CONTAINERS = ["cowrie", "endlessh", "heralding", "dionaea",
                  "conpot", "http-honeypot", "prometheus", "loki",
                  "grafana", "promtail"]

_ANSI = re.compile(r"\x1b\[[0-9;]*m")
_EMOJI = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u27BF\uFE0F]")


def _run(cmd, timeout=6):
    try:
        return subprocess.run(cmd, capture_output=True, text=True,
                              errors="replace", timeout=timeout).stdout
    except Exception:
        return ""


def _clean(s):
    return _EMOJI.sub("", _ANSI.sub("", s)).strip()


# ═══════════════════════════════════════════════════════════════════
#  jeTT — AI EDR card
# ═══════════════════════════════════════════════════════════════════
class _VerdictBar(Gtk.DrawingArea):
    """Stacked ratio bar: ALLOW / REVIEW / QUARANTINE."""

    def __init__(self, height=14):
        super().__init__()
        self.vals = (0, 0, 0)
        self.set_content_height(height)
        self.set_hexpand(True)
        self.set_draw_func(self._draw)

    def set_vals(self, allow, review, quar):
        self.vals = (allow, review, quar)
        self.queue_draw()

    def _draw(self, _a, cr, w, h):
        total = max(1, sum(self.vals))
        colors = [PALETTE["green"], PALETTE["gold"], PALETTE["red"]]
        x = 0.0
        cr.set_line_width(0)
        for v, chex in zip(self.vals, colors):
            frac = v / total
            if frac <= 0:
                continue
            r, g, b = _rgb(chex)
            seg = max(2.0, frac * w)
            grad = cairo.LinearGradient(0, 0, 0, h)
            grad.add_color_stop_rgba(0, r, g, b, 0.95)
            grad.add_color_stop_rgba(1, r, g, b, 0.45)
            cr.set_source(grad)
            cr.rectangle(x, 3, seg - 1, h - 6)
            cr.fill()
            # glow cap
            cr.set_source_rgba(r, g, b, 0.25)
            cr.rectangle(x, 1, seg - 1, 2)
            cr.fill()
            x += seg


class JettCard:
    RECENT = 4

    def __init__(self):
        self.root, content, self.set_footer = make_ghost(
            "green", "JETT · AI EDR", "⛨")

        # status strip
        strip = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        self.state_lbl = Gtk.Label(xalign=0.0)
        self.state_lbl.set_use_markup(True)
        self.state_lbl.add_css_class("sent-state")
        strip.append(self.state_lbl)
        spacer = Gtk.Box(); spacer.set_hexpand(True)
        strip.append(spacer)
        self.rate_lbl = Gtk.Label(xalign=1.0)
        self.rate_lbl.set_use_markup(True)
        self.rate_lbl.add_css_class("sent-rate")
        strip.append(self.rate_lbl)
        content.append(strip)

        # verdict counters
        counts = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=22)
        self.count_lbls = {}
        for key, chex in (("ALLOW", PALETTE["green"]),
                          ("REVIEW", PALETTE["gold"]),
                          ("QUARANTINE", PALETTE["red"])):
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            v = Gtk.Label(label="—", xalign=0.0)
            v.add_css_class("sent-count")
            t = Gtk.Label(xalign=0.0)
            t.set_markup(f"<span foreground='{chex}' size='7500' "
                         f"letter_spacing='2600'>{key}</span>")
            box.append(v)
            box.append(t)
            counts.append(box)
            self.count_lbls[key] = v
        content.append(counts)

        self.vbar = _VerdictBar()
        content.append(self.vbar)

        # live events/min spark
        self._evt_hist = deque([0.0] * 120, maxlen=120)
        self._evt_peak = 10.0
        content.append(GlowSpark(PALETTE["green"], self._evt_hist, height=40))

        # recent flags
        self.flag_rows = []
        for _ in range(self.RECENT):
            lbl = Gtk.Label(xalign=0.0)
            lbl.set_use_markup(True)
            lbl.set_ellipsize(3)
            lbl.add_css_class("sent-flag")
            content.append(lbl)
            self.flag_rows.append(lbl)

        # state
        self._totals = {"ALLOW": None, "REVIEW": None, "QUARANTINE": None}
        self._live = {"ALLOW": 0, "REVIEW": 0, "QUARANTINE": 0}
        self._flags = deque(maxlen=self.RECENT)
        self._offset = None
        self._window = deque()      # timestamps of recent events
        self._daemon = "?"
        self._mode = "?"
        self._busy = False

        threading.Thread(target=self._seed_totals, daemon=True).start()
        GLib.timeout_add(2000, self._poll)
        self._poll()

    # one-shot full-log verdict census (heavy, so once in background)
    def _seed_totals(self):
        try:
            counts = {}
            for key, pat in (("ALLOW", "ALLOW"),
                             ("REVIEW", "REVIEW"),
                             ("QUARANTINE", "QUARANTINE (")):
                out = _run(["grep", "-ac", pat, JETT_LOG], timeout=120)
                counts[key] = int(out.strip() or 0)
        except Exception:
            counts = {}

        def apply():
            for k, v in counts.items():
                self._totals[k] = v
            self._render()
            return False
        GLib.idle_add(apply)

    def _poll(self):
        if not self._busy:
            self._busy = True
            threading.Thread(target=self._poll_bg, daemon=True).start()
        # decay events/min window + push history point
        now = time.time()
        while self._window and now - self._window[0] > 60:
            self._window.popleft()
        epm = len(self._window)
        self._evt_peak = max(self._evt_peak * 0.999, 10.0, epm)
        self._evt_hist.append(100.0 * epm / self._evt_peak)
        self._render()
        return True

    def _poll_bg(self):
        daemon = _run(["systemctl", "is-active", JETT_SERVICE]).strip() or "?"
        mode = "learn"
        dry = False
        try:
            with open(JETT_DEFAULTS) as f:
                for line in f:
                    if line.startswith("JETT_MODE="):
                        mode = line.split("=", 1)[1].strip()
                    if line.startswith("JETT_ENFORCE_DRY_RUN=1"):
                        dry = True
        except OSError:
            pass

        new_counts = {"ALLOW": 0, "REVIEW": 0, "QUARANTINE": 0}
        flags = []
        n_events = 0
        try:
            size = os.path.getsize(JETT_LOG)
            if self._offset is None or size < self._offset:
                # first pass (or rotation): only look at the tail
                self._offset = max(0, size - 131072)
            with open(JETT_LOG, "rb") as f:
                f.seek(self._offset)
                chunk = f.read(4 * 1024 * 1024)
                self._offset = f.tell()
            for raw in chunk.decode("utf-8", "replace").splitlines():
                line = _clean(raw)
                if not line.startswith("["):
                    continue
                n_events += 1
                if "QUARANTINE (" in line or "WOULD-QUARANTINE" in line:
                    new_counts["QUARANTINE"] += 1
                    m = re.match(r"\[(\d+)\]\s+(\S+)\s+PID:(\d+)", line)
                    conf = re.search(r"conf:([\d.]+)", line)
                    if m:
                        flags.append((m.group(2), m.group(3),
                                      conf.group(1) if conf else "?",
                                      "WOULD" if "WOULD-QUARANTINE" in line
                                      else "KILL"))
                elif "REVIEW" in line:
                    new_counts["REVIEW"] += 1
                elif "ALLOW" in line:
                    new_counts["ALLOW"] += 1
        except OSError:
            pass

        def apply():
            self._busy = False
            self._daemon = daemon
            self._mode = mode + (" · dry-run" if dry else "")
            for k, v in new_counts.items():
                self._live[k] += v
            now = time.time()
            for _ in range(n_events):
                self._window.append(now)
            for fl in flags[-self.RECENT:]:
                self._flags.append(fl)
            self._render()
            return False
        GLib.idle_add(apply)

    def _render(self):
        up = self._daemon == "active"
        dot = PALETTE["green"] if up else PALETTE["red"]
        mode_c = PALETTE["red"] if self._mode.startswith("enforce") \
            else PALETTE["gold"]
        self.state_lbl.set_markup(
            f"<span foreground='{dot}'>●</span> "
            f"<span foreground='{PALETTE['text']}'>DAEMON "
            f"{self._daemon.upper()}</span>"
            f"  <span foreground='{mode_c}'>{self._mode.upper()}</span>")
        epm = len(self._window)
        self.rate_lbl.set_markup(
            f"<span foreground='{PALETTE['green']}'>{epm}</span>"
            f"<span foreground='{PALETTE['dim']}' size='8000'> EV/MIN</span>")

        vals = []
        for k in ("ALLOW", "REVIEW", "QUARANTINE"):
            total = self._totals[k]
            n = (total + self._live[k]) if total is not None else None
            self.count_lbls[k].set_text(
                f"{n:,}" if n is not None else f"+{self._live[k]}")
            vals.append(n if n is not None else self._live[k])
        self.vbar.set_vals(*vals)

        flags = list(self._flags)
        for i, lbl in enumerate(self.flag_rows):
            j = len(flags) - 1 - i
            if j >= 0:
                comm, pid, conf, kind = flags[j]
                kc = PALETTE["gold"] if kind == "WOULD" else PALETTE["red"]
                lbl.set_markup(
                    f"<span foreground='{kc}'>▸ {kind}</span> "
                    f"<span foreground='{PALETTE['text']}'>"
                    f"{GLib.markup_escape_text(comm)}</span>"
                    f"<span foreground='{PALETTE['dim']}'> pid {pid} · "
                    f"conf {conf}</span>")
            else:
                lbl.set_markup(
                    f"<span foreground='{PALETTE['dim']}'>▸ —</span>")

        seeded = all(v is not None for v in self._totals.values())
        self.set_footer(
            ("ALL-TIME CENSUS" if seeded else "COUNTING FULL LOG…")
            + " · /var/log/jett · 2S FOLLOW")


# ═══════════════════════════════════════════════════════════════════
#  HONEYPOT — fleet + live attack feed
# ═══════════════════════════════════════════════════════════════════
_POT_EVENTS = [
    # (container, regex, label-builder)
    ("endlessh",
     re.compile(r"ACCEPT host=(\S+) port=(\d+)"),
     lambda m: ("endlessh", f"ssh tarpit hooked {m.group(1)}")),
    ("endlessh",
     re.compile(r"CLOSE host=(\S+) port=\d+ .*time=([\d.]+)"),
     lambda m: ("endlessh", f"{m.group(1)} wasted {float(m.group(2)):.0f}s")),
    ("cowrie",
     re.compile(r"New connection: ([\d.]+):\d+"),
     lambda m: ("cowrie", f"ssh probe from {m.group(1)}")),
    ("cowrie",
     re.compile(r"login attempt \[b?'?([^'\]]+)'?/b?'?([^'\]]+)'?\]"),
     lambda m: ("cowrie", f"login try {m.group(1)}:{m.group(2)}")),
    ("heralding",
     re.compile(r"(\d+\.\d+\.\d+\.\d+).*?(ssh|telnet|ftp|http|pop3|smtp|"
                r"rdp|vnc|mysql|postgresql|socks5)", re.I),
     lambda m: ("heralding", f"{m.group(2).lower()} creds from {m.group(1)}")),
]


class _PotPip(Gtk.DrawingArea):
    """Pulsing status pip for one container."""

    def __init__(self, size=10):
        super().__init__()
        self.up = None
        self._t0 = time.monotonic()
        self.set_content_width(size)
        self.set_content_height(size)
        self.set_draw_func(self._draw)

    def set_up(self, up):
        self.up = up
        self.queue_draw()

    def _draw(self, _a, cr, w, h):
        t = time.monotonic() - self._t0
        if self.up is None:
            chex = PALETTE["dim"]; a = 0.4
        elif self.up:
            chex = PALETTE["green"]; a = 0.55 + 0.45 * math.sin(t * 3)**2
        else:
            chex = PALETTE["red"]; a = 0.9
        r, g, b = _rgb(chex)
        cr.set_source_rgba(r, g, b, a * 0.3)
        cr.arc(w / 2, h / 2, min(w, h) / 2, 0, math.tau)
        cr.fill()
        cr.set_source_rgba(r, g, b, a)
        cr.arc(w / 2, h / 2, min(w, h) / 3.2, 0, math.tau)
        cr.fill()


class HoneypotCard:
    FEED = 5

    def __init__(self):
        self.root, content, self.set_footer = make_ghost(
            "red", "HONEYPOT GRID", "☠")

        # fleet flow
        self.flow = Gtk.FlowBox()
        self.flow.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flow.set_max_children_per_line(5)
        self.flow.set_min_children_per_line(5)
        self.flow.set_column_spacing(10)
        self.flow.set_row_spacing(4)
        self.pips = {}
        for name in POT_CONTAINERS:
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
            pip = _PotPip()
            pip.set_valign(Gtk.Align.CENTER)
            lbl = Gtk.Label(label=name[:12], xalign=0.0)
            lbl.add_css_class("pot-name")
            box.append(pip)
            box.append(lbl)
            self.flow.append(box)
            self.pips[name] = pip
        content.append(self.flow)

        rule = Gtk.Box()
        rule.add_css_class("ghost-rule-red")
        rule.set_size_request(-1, 1)
        content.append(rule)

        # live feed
        self.feed_rows = []
        for _ in range(self.FEED):
            lbl = Gtk.Label(xalign=0.0)
            lbl.set_use_markup(True)
            lbl.set_ellipsize(3)
            lbl.add_css_class("sent-flag")
            content.append(lbl)
            self.feed_rows.append(lbl)

        self._feed = deque(maxlen=64)
        self._seen = set()
        self._hits = 0
        self._busy = False
        self._anim_id = GLib.timeout_add(160, self._anim)
        GLib.timeout_add(5000, self._poll)
        self._poll()

    def _anim(self):
        for pip in self.pips.values():
            pip.queue_draw()
        return True

    def _poll(self):
        if self._busy:
            return True
        self._busy = True
        threading.Thread(target=self._poll_bg, daemon=True).start()
        return True

    def _poll_bg(self):
        out = _run(["docker", "ps", "--format", "{{.Names}}\t{{.Status}}"],
                   timeout=8)
        states = {}
        for line in out.splitlines():
            if "\t" in line:
                name, status = line.split("\t", 1)
                states[name] = status.startswith("Up")

        events = []
        for cont in ("endlessh", "cowrie", "heralding"):
            if not states.get(cont):
                continue
            logs = _run(["docker", "logs", "--since", "70s", "--timestamps",
                         cont], timeout=8)
            for line in logs.splitlines():
                key = (cont, hash(line))
                if key in self._seen:
                    continue
                for c, rx, mk in _POT_EVENTS:
                    if c != cont:
                        continue
                    m = rx.search(line)
                    if m:
                        self._seen.add(key)
                        ts = line.split(" ", 1)[0][11:19] \
                            if line[:4].isdigit() else ""
                        events.append((ts, *mk(m)))
                        break
        if len(self._seen) > 4096:
            self._seen = set(list(self._seen)[-2048:])

        def apply():
            self._busy = False
            for name, pip in self.pips.items():
                pip.set_up(states.get(name, False))
            for ev in events:
                self._feed.append(ev)
                self._hits += 1
            up = sum(1 for v in states.values() if v)
            feed = list(self._feed)
            for i, lbl in enumerate(self.feed_rows):
                j = len(feed) - 1 - i
                if j >= 0:
                    ts, pot, msg = feed[j]
                    lbl.set_markup(
                        f"<span foreground='{PALETTE['red']}'>▸</span> "
                        f"<span foreground='{PALETTE['dim']}'>{ts}</span> "
                        f"<span foreground='{PALETTE['gold']}'>{pot}</span> "
                        f"<span foreground='{PALETTE['text']}'>"
                        f"{GLib.markup_escape_text(msg)}</span>")
                else:
                    lbl.set_markup(
                        f"<span foreground='{PALETTE['dim']}'>▸ waiting for "
                        f"prey…</span>")
            self.set_footer(
                f"{up}/{len(POT_CONTAINERS)} CONTAINERS UP · "
                f"{self._hits} EVENTS THIS SESSION · DOCKER 5S")
            return False
        GLib.idle_add(apply)
