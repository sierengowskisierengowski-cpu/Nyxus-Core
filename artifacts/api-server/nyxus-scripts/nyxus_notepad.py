#!/usr/bin/env python3
# ╔══════════════════════════════════════════════════════════════════════╗
# ║  NYXUS Notepad — GTK4 + libadwaita markdown notepad                 ║
# ║  Editor + live preview · file ops · recent files · auto-save        ║
# ║  © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED       ║
# ╚══════════════════════════════════════════════════════════════════════╝

__nyxid__ = "4e59582d4a35572d323032362d53494552454e474f57534b492d4c4f434b4544"

def _nyx_integrity():
    try:
        _s = open(__file__, encoding="utf-8").read()
        assert "SIERENGOWSKI" in _s, "NYXUS: tamper detected"
    except (OSError, AssertionError) as _e:
        import sys as _sys; print(f"NYXUS SECURITY: {_e}", file=_sys.stderr)

# ── NYXUS palette (single source of truth · rev r13) ────────────────
try:
    from nyxus_palette import (
        WHITE_PURE, WHITE_OFF, GREY_LIGHT, GREY_MID, GREY_TERTIARY,
        INK_FADED, INK_BLACK,
        GLASS_DARK, GLASS_DEEPER, GLASS_DEEPEST,
        HAIRLINE_WHITE, HAIRLINE_INK,
        RADIUS_CARD, RADIUS_PILL, RADIUS_INPUT,
        FONT_UI, FONT_MONO, FONT_DISPLAY,
        format_css, assert_no_forbidden,
    )
except Exception:
    WHITE_PURE='#ffffff'; WHITE_OFF='#e8edf5'; GREY_LIGHT='#c8ccd6'
    GREY_MID='#9aa0ad'; GREY_TERTIARY='#6a6e78'
    INK_FADED='#0a0a0a'; INK_BLACK='#000000'
    GLASS_DARK='rgba(8, 12, 20, 0.55)'
    GLASS_DEEPER='rgba(15, 20, 32, 0.72)'
    GLASS_DEEPEST='rgba(5, 7, 12, 0.92)'
    HAIRLINE_WHITE='rgba(255, 255, 255, 0.10)'
    HAIRLINE_INK='rgba(0, 0, 0, 0.45)'
    RADIUS_CARD=14; RADIUS_PILL=12; RADIUS_INPUT=10
    FONT_UI='Inter'; FONT_MONO='JetBrains Mono'; FONT_DISPLAY='Inter Display'
    def format_css(t):
        _d = {
            'WHITE_PURE': WHITE_PURE, 'WHITE_OFF': WHITE_OFF,
            'GREY_LIGHT': GREY_LIGHT, 'GREY_MID': GREY_MID,
            'GREY_TERTIARY': GREY_TERTIARY,
            'INK_FADED': INK_FADED, 'INK_BLACK': INK_BLACK,
            'GLASS_DARK': GLASS_DARK, 'GLASS_DEEPER': GLASS_DEEPER,
            'GLASS_DEEPEST': GLASS_DEEPEST,
            'HAIRLINE_WHITE': HAIRLINE_WHITE, 'HAIRLINE_INK': HAIRLINE_INK,
            'RADIUS_CARD': RADIUS_CARD, 'RADIUS_PILL': RADIUS_PILL,
            'RADIUS_INPUT': RADIUS_INPUT,
            'FONT_UI': FONT_UI, 'FONT_MONO': FONT_MONO,
            'FONT_DISPLAY': FONT_DISPLAY,
        }
        return t.format_map(_d)
    def assert_no_forbidden(*a, **k): pass

_nyx_integrity()

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Gdk, GLib, Gio, Adw, Pango

import os, sys, json, re, html, traceback
from datetime import datetime
from pathlib import Path

# ── Optional shared chrome (rainbow titles + graffiti walls) ─────────────
def _nyxus_load_chrome():
    try:
        from nyxus_chrome import install_chrome
        return install_chrome
    except ImportError:
        return None
_nyx_install_chrome = _nyxus_load_chrome()

CONFIG_DIR = Path.home() / ".config" / "nyxus-notepad"
RECENT_FILE = CONFIG_DIR / "recent.json"
STATE_FILE  = CONFIG_DIR / "state.json"
MAX_RECENT  = 12
AUTOSAVE_MS = 2000

CSS = format_css("""
* {{ font-family: 'Inter Display', 'Inter', 'Sans'; }}
window {{ background-color: #0a0a0a; color: rgba(232,224,245,0.92); }}

.editor-pane textview text {{
    background-color: rgba(0, 0, 0, 0.55);
    color: rgba(232, 237, 245, 0.96);
    font-family: 'JetBrains Mono', monospace;
    font-size: 14px;
    padding: 16px;
    caret-color: {WHITE_OFF};
}}
.editor-pane textview {{ background-color: transparent; }}

.preview-pane textview text {{
    background-color: rgba(8, 12, 20, 0.55);
    color: rgba(232, 237, 245, 0.92);
    font-family: 'Inter Display', 'Inter', sans-serif;
    font-size: 14px;
    padding: 22px 28px;
}}
.preview-pane textview {{ background-color: transparent; }}

.statusbar {{
    background-color: {INK_BLACK};
    color: rgba(255, 255, 255, 0.65);
    border-top: 1px solid rgba(255, 255, 255, 0.06);
    padding: 4px 14px;
    font-size: 12px;
    font-family: 'JetBrains Mono', monospace;
}}
.statusbar .dirty-dot {{
    color: #f0a060;
    font-weight: bold;
}}
.statusbar .clean-dot {{
    color: #90b890;
}}

.recent-row {{
    padding: 8px 14px;
}}
.recent-row .title {{ font-weight: bold; color: {WHITE_OFF}; }}
.recent-row .path  {{ color: {GREY_TERTIARY}; font-size: 11px; }}

.empty-state {{
    color: {GREY_TERTIARY};
    font-size: 16px;
    padding: 60px;
}}
""")


# ── Markdown → Pango markup (lightweight subset) ──────────────────────────

_RE_HEADER  = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_RE_HRULE   = re.compile(r"^\s*([-*_])\1{2,}\s*$")
_RE_ULIST   = re.compile(r"^(\s*)[-*+]\s+(.+)$")
_RE_OLIST   = re.compile(r"^(\s*)(\d+)\.\s+(.+)$")
_RE_QUOTE   = re.compile(r"^>\s?(.*)$")
_RE_FENCE   = re.compile(r"^```(.*)$")

def _inline(text: str) -> str:
    """Convert markdown inline syntax to Pango markup. Order matters."""
    s = html.escape(text, quote=False)
    # code spans first (so they don't get further processed)
    parts = []
    last = 0
    for m in re.finditer(r"`([^`]+)`", s):
        parts.append(s[last:m.start()])
        parts.append(f"<tt>{m.group(1)}</tt>")
        last = m.end()
    parts.append(s[last:])
    s = "".join(parts)
    # links [text](url)
    s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)",
               lambda m: f'<u><span foreground="#9ad6ff">{m.group(1)}</span></u>', s)
    # bold ** **
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"__(.+?)__",     r"<b>\1</b>", s)
    # italic * *  /  _ _   (avoid eating list markers — already consumed)
    s = re.sub(r"(?<![\*\w])\*([^\*\n]+?)\*(?!\*)", r"<i>\1</i>", s)
    s = re.sub(r"(?<![_\w])_([^_\n]+?)_(?!_)",      r"<i>\1</i>", s)
    # strikethrough
    s = re.sub(r"~~(.+?)~~", r"<s>\1</s>", s)
    return s

_HEADER_SIZES = {1: "xx-large", 2: "x-large", 3: "large",
                 4: "medium",   5: "small",   6: "small"}

def md_to_pango(src: str) -> str:
    """Render a (small) subset of markdown to Pango markup."""
    out = []
    in_fence = False
    fence_buf: list[str] = []
    for raw in src.splitlines():
        if in_fence:
            if _RE_FENCE.match(raw):
                code = "\n".join(fence_buf)
                out.append(f'<span background="#0d1320" foreground="#c8ccd6">'
                           f'<tt>{html.escape(code)}</tt></span>')
                fence_buf = []
                in_fence = False
            else:
                fence_buf.append(raw)
            continue
        if _RE_FENCE.match(raw):
            in_fence = True
            continue
        if not raw.strip():
            out.append("")
            continue
        if _RE_HRULE.match(raw):
            out.append('<span foreground="#3a3f4a">────────────────────────</span>')
            continue
        m = _RE_HEADER.match(raw)
        if m:
            lvl  = len(m.group(1))
            text = _inline(m.group(2))
            size = _HEADER_SIZES.get(lvl, "medium")
            out.append(f'<span size="{size}" weight="bold" '
                       f'foreground="#ffffff">{text}</span>')
            continue
        m = _RE_QUOTE.match(raw)
        if m:
            out.append(f'<span foreground="#9aa0ad"><i>▏ {_inline(m.group(1))}</i></span>')
            continue
        m = _RE_ULIST.match(raw)
        if m:
            indent = "    " * (len(m.group(1)) // 2)
            out.append(f'{indent}<span foreground="#c8ccd6">• </span>{_inline(m.group(2))}')
            continue
        m = _RE_OLIST.match(raw)
        if m:
            indent = "    " * (len(m.group(1)) // 2)
            out.append(f'{indent}<span foreground="#c8ccd6">{m.group(2)}. </span>{_inline(m.group(3))}')
            continue
        out.append(_inline(raw))
    if in_fence and fence_buf:
        code = "\n".join(fence_buf)
        out.append(f'<tt>{html.escape(code)}</tt>')
    return "\n".join(out)


# ── Recent files persistence ──────────────────────────────────────────────

def _ensure_dir():
    try: CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    except Exception: pass

def load_recent() -> list[str]:
    _ensure_dir()
    try:
        with open(RECENT_FILE) as f:
            data = json.load(f)
        if isinstance(data, list):
            return [str(x) for x in data if isinstance(x, (str, os.PathLike))][:MAX_RECENT]
    except Exception: pass
    return []

def save_recent(paths: list[str]) -> None:
    _ensure_dir()
    try:
        with open(RECENT_FILE, "w") as f:
            json.dump(paths[:MAX_RECENT], f, indent=2)
    except Exception: pass

def push_recent(path: str) -> list[str]:
    paths = [p for p in load_recent() if p != path]
    paths.insert(0, path)
    paths = paths[:MAX_RECENT]
    save_recent(paths)
    return paths

def load_state() -> dict:
    _ensure_dir()
    try:
        with open(STATE_FILE) as f: return json.load(f) or {}
    except Exception: return {}

def save_state(state: dict) -> None:
    _ensure_dir()
    try:
        with open(STATE_FILE, "w") as f: json.dump(state, f, indent=2)
    except Exception: pass


# ── Main application ──────────────────────────────────────────────────────

class NyxusNotepad(Adw.Application):
    def __init__(self):
        super().__init__(application_id="io.nyxus.notepad",
                         flags=Gio.ApplicationFlags.NON_UNIQUE)
        try: Adw.init()
        except Exception: pass
        self._current_path: str | None = None
        self._dirty: bool = False
        self._preview_visible: bool = True
        self._autosave_handle: int | None = None

    def do_activate(self):
        try:
            self._build_ui()
        except Exception:
            log = "/tmp/nyxus-notepad.log"
            try:
                with open(log, "a") as f:
                    f.write("activate crash:\n")
                    traceback.print_exc(file=f)
            except Exception: pass
            print(f"NYXUS Notepad crashed — see {log}")

    # ── UI ───────────────────────────────────────────────────────────────
    def _build_ui(self):
        try:
            sm = Adw.StyleManager.get_default()
            sm.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        except Exception: pass

        prov = Gtk.CssProvider()
        try: prov.load_from_string(CSS)
        except Exception:
            try: prov.load_from_data(CSS.encode())
            except Exception: pass
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), prov,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self.win = Adw.ApplicationWindow(application=self, title="NYXUS Notepad")
        self.win.set_default_size(1200, 780)
        if _nyx_install_chrome:
            try: _nyx_install_chrome(self.win, page_key="_notepad")
            except Exception: pass

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.win.set_content(root)

        # Header bar
        hdr = Adw.HeaderBar()
        self._title_lbl = Gtk.Label(label="Untitled")
        self._title_lbl.add_css_class("title-3")
        hdr.set_title_widget(self._title_lbl)

        # Left side: new / open
        btn_new = Gtk.Button.new_from_icon_name("document-new-symbolic")
        btn_new.set_tooltip_text("New (Ctrl+N)")
        btn_new.connect("clicked", lambda *_: self.action_new())
        hdr.pack_start(btn_new)

        btn_open = Gtk.Button.new_from_icon_name("document-open-symbolic")
        btn_open.set_tooltip_text("Open (Ctrl+O)")
        btn_open.connect("clicked", lambda *_: self.action_open())
        hdr.pack_start(btn_open)

        btn_recent = Gtk.MenuButton()
        btn_recent.set_icon_name("document-open-recent-symbolic")
        btn_recent.set_tooltip_text("Recent files")
        self._recent_menu = Gio.Menu()
        btn_recent.set_menu_model(self._recent_menu)
        hdr.pack_start(btn_recent)

        # Right side: preview toggle, save, save-as menu
        self._preview_btn = Gtk.ToggleButton()
        self._preview_btn.set_icon_name("view-reveal-symbolic")
        self._preview_btn.set_tooltip_text("Toggle preview pane (Ctrl+P)")
        self._preview_btn.set_active(True)
        self._preview_btn.connect("toggled", self._on_preview_toggled)
        hdr.pack_end(self._preview_btn)

        btn_save = Gtk.Button.new_from_icon_name("document-save-symbolic")
        btn_save.set_tooltip_text("Save (Ctrl+S)")
        btn_save.connect("clicked", lambda *_: self.action_save())
        hdr.pack_end(btn_save)

        btn_save_as = Gtk.Button.new_from_icon_name("document-save-as-symbolic")
        btn_save_as.set_tooltip_text("Save As (Ctrl+Shift+S)")
        btn_save_as.connect("clicked", lambda *_: self.action_save_as())
        hdr.pack_end(btn_save_as)

        root.append(hdr)

        # Body: split editor + preview
        self._paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self._paned.set_vexpand(True)
        self._paned.set_hexpand(True)
        self._paned.set_wide_handle(True)
        self._paned.set_position(620)
        root.append(self._paned)

        # Editor pane
        ed_scroll = Gtk.ScrolledWindow()
        ed_scroll.set_hexpand(True); ed_scroll.set_vexpand(True)
        ed_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        ed_scroll.add_css_class("editor-pane")
        self._editor = Gtk.TextView()
        self._editor.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self._editor.set_monospace(True)
        self._editor.set_top_margin(8)
        self._editor.set_bottom_margin(8)
        self._buf = self._editor.get_buffer()
        self._buf.connect("changed", self._on_buf_changed)
        ed_scroll.set_child(self._editor)
        self._paned.set_start_child(ed_scroll)
        self._paned.set_resize_start_child(True)
        self._paned.set_shrink_start_child(False)

        # Preview pane
        self._pv_scroll = Gtk.ScrolledWindow()
        self._pv_scroll.set_hexpand(True); self._pv_scroll.set_vexpand(True)
        self._pv_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self._pv_scroll.add_css_class("preview-pane")
        self._preview = Gtk.TextView()
        self._preview.set_editable(False)
        self._preview.set_cursor_visible(False)
        self._preview.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self._preview.set_top_margin(8)
        self._preview.set_bottom_margin(8)
        self._preview_buf = self._preview.get_buffer()
        self._pv_scroll.set_child(self._preview)
        self._paned.set_end_child(self._pv_scroll)
        self._paned.set_resize_end_child(True)
        self._paned.set_shrink_end_child(False)

        # Status bar
        sb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        sb.add_css_class("statusbar")
        self._status_path = Gtk.Label(label="No file"); self._status_path.set_xalign(0.0)
        self._status_path.set_hexpand(True)
        self._status_dirty = Gtk.Label(label=""); self._status_dirty.add_css_class("clean-dot")
        self._status_count = Gtk.Label(label="0 words · 0 chars")
        self._status_pos   = Gtk.Label(label="L1:C1")
        for w in (self._status_path, self._status_dirty,
                  self._status_count, self._status_pos):
            sb.append(w)
        root.append(sb)

        # Cursor position tracking
        self._buf.connect("notify::cursor-position", lambda *_: self._update_status())
        self._buf.connect("changed", lambda *_: self._update_status())

        # Keyboard shortcuts
        self._install_shortcuts()

        # Restore recent menu + last-opened state
        self._refresh_recent_menu()
        self._restore_state()

        self._update_title()
        self._update_status()
        self._render_preview()

        # Save state on close
        self.win.connect("close-request", self._on_close_request)
        self.win.present()

    def _install_shortcuts(self):
        sc = Gtk.ShortcutController()
        sc.set_scope(Gtk.ShortcutScope.GLOBAL)
        def add(combo, fn):
            sh = Gtk.Shortcut.new(
                Gtk.ShortcutTrigger.parse_string(combo),
                Gtk.CallbackAction.new(lambda *_: (fn() or True)))
            sc.add_shortcut(sh)
        add("<Control>n",       self.action_new)
        add("<Control>o",       self.action_open)
        add("<Control>s",       self.action_save)
        add("<Control><Shift>s", self.action_save_as)
        add("<Control>p",       self._toggle_preview_kbd)
        self.win.add_controller(sc)

    def _toggle_preview_kbd(self):
        self._preview_btn.set_active(not self._preview_btn.get_active())

    def _on_preview_toggled(self, btn):
        self._preview_visible = btn.get_active()
        self._pv_scroll.set_visible(self._preview_visible)
        if self._preview_visible:
            self._render_preview()

    # ── Buffer + preview ─────────────────────────────────────────────────
    def _on_buf_changed(self, *_):
        if not self._dirty:
            self._dirty = True
            self._update_title()
            self._update_status()
        # debounced preview render
        if hasattr(self, "_render_handle") and self._render_handle:
            try: GLib.source_remove(self._render_handle)
            except Exception: pass
        self._render_handle = GLib.timeout_add(180, self._render_preview_tick)
        # debounced autosave (only if a path is bound)
        if self._autosave_handle:
            try: GLib.source_remove(self._autosave_handle)
            except Exception: pass
        if self._current_path:
            self._autosave_handle = GLib.timeout_add(AUTOSAVE_MS, self._autosave_tick)

    def _render_preview_tick(self):
        self._render_handle = None
        self._render_preview()
        return GLib.SOURCE_REMOVE

    def _autosave_tick(self):
        self._autosave_handle = None
        if self._current_path and self._dirty:
            self._save_to(self._current_path, mark_recent=False, autosave=True)
        return GLib.SOURCE_REMOVE

    def _render_preview(self):
        if not self._preview_visible:
            return
        text = self._get_text()
        try:
            markup = md_to_pango(text)
        except Exception:
            markup = html.escape(text)
        self._preview_buf.set_text("", -1)
        if not text.strip():
            self._preview_buf.insert_markup(
                self._preview_buf.get_end_iter(),
                f'<span foreground="#5a5e68" size="large">'
                f'  Start typing to see the preview…</span>', -1)
            return
        try:
            self._preview_buf.insert_markup(
                self._preview_buf.get_end_iter(), markup, -1)
        except Exception:
            self._preview_buf.set_text(text, -1)

    def _get_text(self) -> str:
        return self._buf.get_text(self._buf.get_start_iter(),
                                  self._buf.get_end_iter(), False)

    # ── File actions ─────────────────────────────────────────────────────
    def action_new(self):
        self._maybe_confirm_discard(lambda: self._reset_to_blank())

    def _reset_to_blank(self):
        self._buf.set_text("", -1)
        self._current_path = None
        self._dirty = False
        self._update_title()
        self._update_status()
        self._render_preview()

    def action_open(self):
        dlg = Gtk.FileDialog.new()
        dlg.set_title("Open file")
        f = Gtk.FileFilter()
        f.set_name("Markdown / text")
        for pat in ("*.md", "*.markdown", "*.txt", "*.rst", "*.org", "*.log"):
            f.add_pattern(pat)
        all_f = Gtk.FileFilter(); all_f.set_name("All files"); all_f.add_pattern("*")
        store = Gio.ListStore.new(Gtk.FileFilter)
        store.append(f); store.append(all_f)
        dlg.set_filters(store)
        dlg.set_default_filter(f)
        def cb(dialog, res):
            try:
                file = dialog.open_finish(res)
                if file: self._open_path(file.get_path())
            except GLib.Error: pass
        dlg.open(self.win, None, cb)

    def _open_path(self, path: str):
        try:
            with open(path, encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            self._show_error(f"Could not open {path}", str(e))
            return
        self._buf.set_text(content, -1)
        self._current_path = path
        self._dirty = False
        push_recent(path)
        self._refresh_recent_menu()
        self._update_title()
        self._update_status()
        self._render_preview()

    def action_save(self):
        if self._current_path:
            self._save_to(self._current_path)
        else:
            self.action_save_as()

    def action_save_as(self):
        dlg = Gtk.FileDialog.new()
        dlg.set_title("Save as")
        if self._current_path:
            try: dlg.set_initial_name(os.path.basename(self._current_path))
            except Exception: pass
        else:
            dlg.set_initial_name("untitled.md")
        def cb(dialog, res):
            try:
                file = dialog.save_finish(res)
                if file: self._save_to(file.get_path())
            except GLib.Error: pass
        dlg.save(self.win, None, cb)

    def _save_to(self, path: str, mark_recent: bool = True, autosave: bool = False):
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self._get_text())
        except Exception as e:
            self._show_error(f"Could not save {path}", str(e))
            return
        self._current_path = path
        self._dirty = False
        if mark_recent:
            push_recent(path)
            self._refresh_recent_menu()
        self._update_title()
        # status hint for autosave
        suffix = " · autosaved" if autosave else " · saved"
        self._status_path.set_text(self._display_path(path) + suffix)
        GLib.timeout_add(1500, lambda: (self._update_status() or False))

    def _display_path(self, path: str) -> str:
        try:
            home = str(Path.home())
            if path.startswith(home):
                return "~" + path[len(home):]
        except Exception: pass
        return path

    def _show_error(self, heading: str, body: str):
        try:
            dlg = Adw.MessageDialog.new(self.win, heading, body)
            dlg.add_response("ok", "OK")
            dlg.set_default_response("ok")
            dlg.set_close_response("ok")
            dlg.present()
        except Exception:
            print(f"NYXUS Notepad: {heading}: {body}", file=sys.stderr)

    def _maybe_confirm_discard(self, cont):
        if not self._dirty:
            cont(); return
        try:
            dlg = Adw.MessageDialog.new(
                self.win, "Discard unsaved changes?",
                "You have unsaved changes that will be lost.")
            dlg.add_response("cancel", "Cancel")
            dlg.add_response("discard", "Discard")
            dlg.set_response_appearance("discard", Adw.ResponseAppearance.DESTRUCTIVE)
            dlg.set_default_response("cancel")
            dlg.set_close_response("cancel")
            def on_resp(d, response_id):
                if response_id == "discard":
                    cont()
            dlg.connect("response", on_resp)
            dlg.present()
        except Exception:
            cont()

    def _on_close_request(self, *_):
        # Save app state (current path, window size) for next launch.
        try:
            state = {
                "last_path": self._current_path or "",
                "preview_visible": self._preview_visible,
                "paned_pos": self._paned.get_position(),
            }
            save_state(state)
        except Exception: pass
        if not self._dirty:
            return False  # allow close
        # Confirm discard, then explicitly close.
        def discard():
            try: self.win.destroy()
            except Exception: pass
        self._maybe_confirm_discard(discard)
        return True  # block default close until confirmed

    def _restore_state(self):
        st = load_state()
        try:
            if st.get("paned_pos"):
                self._paned.set_position(int(st["paned_pos"]))
        except Exception: pass
        try:
            pv = st.get("preview_visible", True)
            self._preview_btn.set_active(bool(pv))
        except Exception: pass
        last = st.get("last_path") or ""
        if last and os.path.isfile(last):
            try: self._open_path(last)
            except Exception: pass

    # ── Recent menu ──────────────────────────────────────────────────────
    def _refresh_recent_menu(self):
        self._recent_menu.remove_all()
        recent = load_recent()
        # Per §9 we never leave the menu blank — always offer at least one item.
        if not recent:
            item = Gio.MenuItem.new("No recent files", "app.noop")
            self._recent_menu.append_item(item)
            self._ensure_action("noop", lambda *_: None, enabled=False)
            return
        for i, path in enumerate(recent):
            label = self._display_path(path)
            action_id = f"open-recent-{i}"
            self._ensure_action(action_id,
                                lambda *_a, p=path: self._open_path(p))
            item = Gio.MenuItem.new(label, f"app.{action_id}")
            self._recent_menu.append_item(item)
        # Trailing clear option
        self._ensure_action("clear-recent", lambda *_: self._clear_recent())
        self._recent_menu.append_item(
            Gio.MenuItem.new("Clear recent", "app.clear-recent"))

    def _ensure_action(self, name: str, cb, enabled: bool = True):
        existing = self.lookup_action(name)
        if existing is None:
            act = Gio.SimpleAction.new(name, None)
            act.connect("activate", cb)
            act.set_enabled(enabled)
            self.add_action(act)
        else:
            try: existing.set_enabled(enabled)
            except Exception: pass

    def _clear_recent(self):
        save_recent([])
        self._refresh_recent_menu()

    # ── Title + status ───────────────────────────────────────────────────
    def _update_title(self):
        name = (os.path.basename(self._current_path)
                if self._current_path else "Untitled")
        marker = " •" if self._dirty else ""
        self._title_lbl.set_text(f"{name}{marker}")
        try:
            self.win.set_title(f"{name}{marker} — NYXUS Notepad")
        except Exception: pass

    def _update_status(self):
        # Path + dirty dot
        if self._current_path:
            self._status_path.set_text(self._display_path(self._current_path))
        else:
            self._status_path.set_text("No file (unsaved)")
        if self._dirty:
            self._status_dirty.set_text("●")
            self._status_dirty.remove_css_class("clean-dot")
            self._status_dirty.add_css_class("dirty-dot")
        else:
            self._status_dirty.set_text("○")
            self._status_dirty.remove_css_class("dirty-dot")
            self._status_dirty.add_css_class("clean-dot")
        # Cursor position
        try:
            ins = self._buf.get_iter_at_mark(self._buf.get_insert())
            line = ins.get_line() + 1
            col  = ins.get_line_offset() + 1
            self._status_pos.set_text(f"L{line}:C{col}")
        except Exception: pass
        # Word/char count
        try:
            text = self._get_text()
            words = len(re.findall(r"\S+", text))
            chars = len(text)
            self._status_count.set_text(f"{words} words · {chars} chars")
        except Exception: pass


# ── main ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        NyxusNotepad().run(None)
    except Exception:
        log = "/tmp/nyxus-notepad.log"
        try:
            with open(log, "w") as f: traceback.print_exc(file=f)
        except Exception: pass
        print(f"NYXUS Notepad crashed — see {log}")
        sys.exit(1)

# ── palette guard (rev r13) ───────────────────────────────────────────────
try: assert_no_forbidden(CSS, __file__)
except Exception as _e: import sys; sys.stderr.write(str(_e) + chr(10))
