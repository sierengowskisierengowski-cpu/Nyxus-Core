#!/usr/bin/env python3
"""
NYXUS Cheatsheet — live keybind reference, parsed from hyprland.conf.

Reads ~/.config/hypr/hyprland.conf, extracts every `bind = ...` line and
groups them by the surrounding `# ── SECTION ────` comment headers. Shows
a DARK MIRROR popup with searchable keybinds. Esc closes. Always reflects
the current config — no duplication, no drift.

Bind in hyprland.conf:
    bind = SUPER, slash, exec, python3 ~/.nyxus/nyxus_cheatsheet.py
"""
from __future__ import annotations
import gi, os, sys, re
from pathlib import Path

# ── NYXUS palette (single source of truth) ───────────────────────────
try:
    from nyxus_palette import (
        WHITE_OFF, GREY_LIGHT, GREY_MID, GREY_TERTIARY,
        GLASS_DARK, GLASS_DEEPER, GLASS_DEEPEST,
        HAIRLINE_WHITE,
        RADIUS_CARD, RADIUS_PILL, RADIUS_INPUT,
        FONT_UI, FONT_MONO, FONT_DISPLAY,
        format_css,
    )
except Exception:
    WHITE_OFF='#e8edf5'; GREY_LIGHT='#c8ccd6'
    GREY_MID='#9aa0ad'; GREY_TERTIARY='#6a6e78'
    GLASS_DARK='rgba(8, 12, 20, 0.55)'
    GLASS_DEEPER='rgba(15, 20, 32, 0.72)'
    GLASS_DEEPEST='rgba(5, 7, 12, 0.92)'
    HAIRLINE_WHITE='rgba(255, 255, 255, 0.10)'
    RADIUS_CARD=14; RADIUS_PILL=12; RADIUS_INPUT=10
    FONT_UI='Inter'; FONT_MONO='JetBrains Mono'; FONT_DISPLAY='Inter Display'
    def format_css(t):
        _d = {
            'WHITE_OFF': WHITE_OFF, 'GREY_LIGHT': GREY_LIGHT,
            'GREY_MID': GREY_MID, 'GREY_TERTIARY': GREY_TERTIARY,
            'GLASS_DARK': GLASS_DARK, 'GLASS_DEEPER': GLASS_DEEPER,
            'GLASS_DEEPEST': GLASS_DEEPEST,
            'HAIRLINE_WHITE': HAIRLINE_WHITE,
            'RADIUS_CARD': RADIUS_CARD, 'RADIUS_PILL': RADIUS_PILL,
            'RADIUS_INPUT': RADIUS_INPUT,
            'FONT_UI': FONT_UI, 'FONT_MONO': FONT_MONO,
            'FONT_DISPLAY': FONT_DISPLAY,
        }
        return t.format_map(_d)

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk, GLib

sys.path.insert(0, str(Path.home() / ".local" / "bin"))
try:
    from nyxus_chrome import install_chrome  # type: ignore
except Exception:
    def install_chrome(win, key="_cheatsheet"): return None

WIN_W, WIN_H = 880, 720

CONF_CANDIDATES = [
    Path.home() / ".config" / "hypr" / "hyprland.conf",
    Path("/etc/skel/.config/hypr/hyprland.conf"),
]

SECTION_RE = re.compile(r"^#\s*──\s*(.+?)\s*─+")
# Hyprland bind variants: bind, bindm (mouse), bindl (locked), binde (repeat),
# bindr (release), bindn (no-mods), bindt (transparent), and combinations
# like `bindle`, `bindrn`, etc. Match `bind` followed by zero or more of
# the flag letters [lmernt].
BIND_RE    = re.compile(r"^\s*(bind[lmernt]*)\s*=\s*(.+)$")


def parse_keybinds(conf_path: Path):
    """Return list of (section, mods, key, action) tuples."""
    sections: list[tuple[str, list[tuple[str, str, str]]]] = []
    current_section = "GENERAL"
    current_binds: list[tuple[str, str, str]] = []
    try:
        text = conf_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return [("ERROR", [("", "", f"could not read {conf_path}")])]

    for raw in text.splitlines():
        m_sec = SECTION_RE.match(raw)
        if m_sec:
            label = m_sec.group(1).strip()
            label = re.sub(r"\s+", " ", label).rstrip("─ ").strip()
            if current_binds:
                sections.append((current_section, current_binds))
                current_binds = []
            current_section = label.upper()
            continue
        m_bind = BIND_RE.match(raw)
        if not m_bind:
            continue
        body = m_bind.group(2)
        parts = [p.strip() for p in body.split(",", 3)]
        if len(parts) < 3:
            continue
        mods = parts[0] or "—"
        key = parts[1] or "—"
        action = ", ".join(parts[2:]).strip()
        action = re.sub(r"^exec,\s*", "", action)
        current_binds.append((mods, key, action))
    if current_binds:
        sections.append((current_section, current_binds))
    return sections


def find_conf() -> Path | None:
    for p in CONF_CANDIDATES:
        if p.exists():
            return p
    return None


CSS = format_css("""
* {{
    font-family: '{FONT_UI}', 'Inter', sans-serif;
    color: {WHITE_OFF};
}}
window {{
    background: transparent;
}}
.cs-root {{
    background: {GLASS_DARK};
    border: 1px solid {HAIRLINE_WHITE};
    border-radius: {RADIUS_CARD}px;
    padding: 22px 24px 20px 24px;
}}
.cs-title {{
    font-family: '{FONT_DISPLAY}', '{FONT_UI}', sans-serif;
    font-size: 22px;
    font-weight: 700;
    letter-spacing: 1.2px;
    color: {WHITE_OFF};
    text-shadow: 0 0 8px rgba(255,255,255,0.85),
                 0 0 18px rgba(255,255,255,0.45);
}}
.cs-subtitle {{
    font-family: '{FONT_MONO}', monospace;
    font-size: 10px;
    color: {GREY_TERTIARY};
    letter-spacing: 1.4px;
    margin-top: 2px;
}}
entry.cs-search {{
    background: {GLASS_DEEPER};
    border: 1px solid {HAIRLINE_WHITE};
    border-radius: {RADIUS_INPUT}px;
    padding: 8px 12px;
    color: {WHITE_OFF};
    font-size: 13px;
    margin: 12px 0 8px 0;
}}
entry.cs-search:focus {{
    background: {GLASS_DEEPEST};
    border-color: {WHITE_OFF};
}}
.cs-section {{
    font-family: '{FONT_MONO}', monospace;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 2px;
    color: {GREY_LIGHT};
    margin: 14px 4px 6px 4px;
}}
.cs-row {{
    background: {GLASS_DEEPER};
    border-radius: {RADIUS_PILL}px;
    padding: 6px 10px;
    margin: 2px 0;
}}
.cs-row:hover {{
    background: {GLASS_DEEPEST};
}}
.cs-keys {{
    font-family: '{FONT_MONO}', monospace;
    font-size: 12px;
    font-weight: 700;
    color: {WHITE_OFF};
}}
.cs-action {{
    font-family: '{FONT_UI}', sans-serif;
    font-size: 12px;
    color: {GREY_LIGHT};
}}
scrollbar {{ background: transparent; }}
scrollbar slider {{
    background: rgba(255,255,255,0.18);
    border-radius: 4px;
    min-width: 4px;
    min-height: 24px;
}}
""")


class Cheatsheet(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app)
        self.set_title("NYXUS · Keybind Cheatsheet")
        self.set_default_size(WIN_W, WIN_H)
        self.set_decorated(False)
        try:
            install_chrome(self, key="_cheatsheet")
        except Exception:
            pass

        provider = Gtk.CssProvider()
        provider.load_from_data(CSS.encode("utf-8"))
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.add_css_class("cs-root")
        root.set_margin_start(12); root.set_margin_end(12)
        root.set_margin_top(12);   root.set_margin_bottom(12)
        self.set_child(root)

        title = Gtk.Label(label="NYXUS KEYBINDS", xalign=0)
        title.add_css_class("cs-title")
        root.append(title)
        sub = Gtk.Label(
            label="LIVE · PARSED FROM ~/.config/hypr/hyprland.conf",
            xalign=0)
        sub.add_css_class("cs-subtitle")
        root.append(sub)

        self._search = Gtk.Entry(placeholder_text="filter…")
        self._search.add_css_class("cs-search")
        self._search.connect("changed", self._on_search)
        root.append(self._search)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_hexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        root.append(scroll)

        self._list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        scroll.set_child(self._list_box)

        conf = find_conf()
        if conf is None:
            err = Gtk.Label(label="no hyprland.conf found", xalign=0)
            err.add_css_class("cs-action")
            self._list_box.append(err)
            self._sections = []
        else:
            self._sections = parse_keybinds(conf)
            self._render(self._sections)

        # Esc closes
        ev = Gtk.EventControllerKey()
        ev.connect("key-pressed", self._on_key)
        self.add_controller(ev)

    def _on_key(self, _ctrl, keyval, _kc, _state):
        if keyval == Gdk.KEY_Escape:
            self.close()
            return True
        return False

    def _on_search(self, entry):
        q = entry.get_text().strip().lower()
        if not q:
            self._render(self._sections)
            return
        filtered: list[tuple[str, list[tuple[str, str, str]]]] = []
        for sec, binds in self._sections:
            kept = [
                b for b in binds
                if q in b[0].lower() or q in b[1].lower() or q in b[2].lower()
                   or q in sec.lower()
            ]
            if kept:
                filtered.append((sec, kept))
        self._render(filtered)

    def _render(self, sections):
        # clear
        child = self._list_box.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self._list_box.remove(child)
            child = nxt
        # rebuild
        for sec, binds in sections:
            sec_lbl = Gtk.Label(label=sec, xalign=0)
            sec_lbl.add_css_class("cs-section")
            self._list_box.append(sec_lbl)
            for mods, key, action in binds:
                row = Gtk.Box(
                    orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
                row.add_css_class("cs-row")
                k_str = self._fmt_keys(mods, key)
                k_lbl = Gtk.Label(label=k_str, xalign=0)
                k_lbl.add_css_class("cs-keys")
                k_lbl.set_size_request(220, -1)
                row.append(k_lbl)
                a_lbl = Gtk.Label(label=self._shorten(action), xalign=0)
                a_lbl.add_css_class("cs-action")
                a_lbl.set_hexpand(True)
                a_lbl.set_ellipsize(3)  # PANGO_ELLIPSIZE_END
                row.append(a_lbl)
                self._list_box.append(row)

    @staticmethod
    def _fmt_keys(mods: str, key: str) -> str:
        m = mods.replace("$mod", "Super").strip()
        m = re.sub(r"\s+", " ", m)
        parts = []
        for tok in m.split():
            if tok and tok not in parts:
                parts.append(tok)
        if key and key != "—":
            parts.append(key)
        return " + ".join(parts) if parts else "—"

    @staticmethod
    def _shorten(action: str) -> str:
        a = action.strip()
        a = re.sub(r"^python3\s+~/\.nyxus/nyxus_(\w+)\.py.*$",
                   r"NYXUS \1", a)
        a = re.sub(r"^python3\s+~/\.local/bin/nyxus_(\w+)\.py.*$",
                   r"NYXUS \1", a)
        if len(a) > 90:
            a = a[:87] + "…"
        return a


def main():
    app = Gtk.Application(application_id="io.nyxus.cheatsheet")
    def on_activate(a):
        win = Cheatsheet(a)
        win.present()
    app.connect("activate", on_activate)
    app.run([])


if __name__ == "__main__":
    main()
