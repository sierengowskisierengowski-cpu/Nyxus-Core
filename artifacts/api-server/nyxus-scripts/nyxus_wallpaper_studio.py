#!/usr/bin/env python3
"""
NYXUS Wallpaper Studio (GTK4)

Dedicated wallpaper app with:
- left category browser
- center thumbnail grid
- right preview + controls
- live wallpaper presets (swww transitions)
- day-part scheduling (systemd --user timer)
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import gi
from PIL import Image, ImageEnhance, ImageFilter

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk


HOME = Path.home()
CFG_DIR = HOME / ".config" / "nyxus"
CACHE_DIR = HOME / ".cache" / "nyxus" / "wallpaper-studio"
CFG_PATH = CFG_DIR / "wallpaper.json"
CATS_PATH = CFG_DIR / "wallpaper-categories.json"
WALLS_ROOT = Path("/usr/share/backgrounds/nyxus")
SCHED_SCRIPT = HOME / ".local" / "share" / "nyxus" / "wallpaper-studio-scheduler.sh"
SCHED_UNIT_DIR = HOME / ".config" / "systemd" / "user"
SCHED_SERVICE = SCHED_UNIT_DIR / "nyxus-wallpaper-studio.service"
SCHED_TIMER = SCHED_UNIT_DIR / "nyxus-wallpaper-studio.timer"


DEFAULT_CATEGORIES: Dict[str, List[str]] = {
    "All": ["*"],
    "Dark & Moody": ["dark-moody"],
    "Cosmic & Psychedelic": ["cosmic-psychedelic"],
    "Eyes": ["eyes"],
    "Nature & Landscapes": ["nature-landscapes"],
    "Abstract & Geometric": ["abstract-geometric"],
    "Urban & Atmospheric": ["urban-atmospheric"],
    "Art & Portraits": ["art-portraits"],
    "Live Wallpapers": ["live-wallpapers"],
}

LIVE_PRESETS = {
    "Particle Drift": ("outer", 1.8),
    "Rain Overlay": ("wipe", 1.5),
    "Code Rain": ("random", 1.5),
    "Slow Zoom": ("grow", 2.2),
    "Aurora Shimmer": ("any", 1.6),
}

SLOTS = ("morning", "afternoon", "evening", "night")
FIT_MODES = ("Fill", "Fit", "Stretch", "Center", "Tile")


def _run(cmd: List[str], timeout: int = 10) -> tuple[int, str, str]:
    try:
        p = subprocess.run(
            cmd,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        return p.returncode, p.stdout or "", p.stderr or ""
    except Exception as e:
        return 1, "", str(e)


def _safe_write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def _load_json(path: Path, fallback: dict) -> dict:
    if not path.exists():
        return fallback
    try:
        val = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(val, dict):
            return val
    except Exception:
        pass
    return fallback


def _collect_images(root: Path) -> List[Path]:
    if not root.exists():
        return []
    exts = {".png", ".jpg", ".jpeg", ".webp"}
    out: List[Path] = []
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in exts:
            out.append(p)
    return sorted(out)


@dataclass
class TargetOutput:
    label: str
    output: Optional[str] = None


class WallpaperStudio(Adw.Application):
    def __init__(self) -> None:
        super().__init__(application_id="io.nyxus.wallpaperstudio")
        self.cfg = self._load_cfg()
        self.cat_map = self._load_categories()
        self.current_category = "All"
        self.selected_wallpaper: Optional[Path] = None
        self.wallpapers: List[Path] = []
        self.visible_wallpapers: List[Path] = []
        self.tile_btns: Dict[str, Gtk.Button] = {}
        self.outputs: List[TargetOutput] = [TargetOutput("All Monitors", None)]
        self.preview_pic: Optional[Gtk.Picture] = None
        self.grid_flow: Optional[Gtk.FlowBox] = None
        self.monitor_combo: Optional[Gtk.DropDown] = None
        self.monitor_model: Optional[Gtk.StringList] = None
        self.fit_combo: Optional[Gtk.DropDown] = None
        self.fit_model: Optional[Gtk.StringList] = None
        self.live_combo: Optional[Gtk.DropDown] = None
        self.live_model: Optional[Gtk.StringList] = None
        self.schedule_rows: Dict[str, Gtk.DropDown] = {}
        self.schedule_models: Dict[str, Gtk.StringList] = {}

    def _load_cfg(self) -> dict:
        defaults = {
            "wallpaper": "",
            "favorites": [],
            "monitor_target": "All Monitors",
            "brightness": 1.0,
            "saturation": 1.0,
            "contrast": 1.0,
            "tint_enabled": False,
            "tint_color": "#7B5EA7",
            "blur": 0.0,
            "fit_mode": "Fill",
            "live_preset": "Particle Drift",
            "schedule": {k: "" for k in SLOTS},
            "shuffle_enabled": False,
            "shuffle_interval_minutes": 30,
        }
        cur = _load_json(CFG_PATH, defaults.copy())
        merged = defaults.copy()
        merged.update(cur)
        if not isinstance(merged.get("schedule"), dict):
            merged["schedule"] = {k: "" for k in SLOTS}
        return merged

    def _save_cfg(self) -> None:
        _safe_write_json(CFG_PATH, self.cfg)

    def _load_categories(self) -> Dict[str, List[str]]:
        base = {"categories": DEFAULT_CATEGORIES}
        data = _load_json(CATS_PATH, base)
        cats = data.get("categories", DEFAULT_CATEGORIES)
        if not isinstance(cats, dict):
            cats = DEFAULT_CATEGORIES
        norm: Dict[str, List[str]] = {}
        for k, v in cats.items():
            if isinstance(k, str) and isinstance(v, list):
                norm[k] = [str(x) for x in v if str(x).strip()]
        for k, v in DEFAULT_CATEGORIES.items():
            norm.setdefault(k, v)
        _safe_write_json(CATS_PATH, {"categories": norm})
        return norm

    def do_activate(self) -> None:
        self.outputs = self._detect_outputs()
        self.wallpapers = self._scan_wallpapers()
        self.visible_wallpapers = self._filter_wallpapers(self.current_category)
        self._build_window()

    def _detect_outputs(self) -> List[TargetOutput]:
        out = [TargetOutput("All Monitors", None)]
        rc, stdout, _ = _run(["swww", "query"], timeout=3) if shutil.which("swww") else (1, "", "")
        if rc == 0:
            names: List[str] = []
            for ln in stdout.splitlines():
                ln = ln.strip()
                if not ln:
                    continue
                name = ln.split(":")[0].strip()
                if name:
                    names.append(name)
            for i, name in enumerate(names, start=1):
                out.append(TargetOutput(f"Monitor {i}", name))
        else:
            out.extend([TargetOutput("Monitor 1", "1"), TargetOutput("Monitor 2", "2")])
        return out

    def _scan_wallpapers(self) -> List[Path]:
        if WALLS_ROOT.exists():
            return _collect_images(WALLS_ROOT)
        return []

    def _filter_wallpapers(self, category: str) -> List[Path]:
        if category == "All":
            return list(self.wallpapers)
        folders = self.cat_map.get(category, [])
        if not folders:
            return []
        wanted = {f.lower() for f in folders}
        out: List[Path] = []
        for p in self.wallpapers:
            rel = p.relative_to(WALLS_ROOT)
            folder = rel.parts[0].lower() if len(rel.parts) > 1 else ""
            if "*" in wanted or folder in wanted:
                out.append(p)
        return out

    def _build_window(self) -> None:
        win = Adw.ApplicationWindow(application=self)
        win.set_title("NYXUS Wallpaper Studio")
        win.set_default_size(1460, 900)

        css = Gtk.CssProvider()
        css.load_from_data(
            b"""
            .nyx-tile { border: 1px solid rgba(255,255,255,0.10); border-radius: 10px; padding: 4px; }
            .nyx-tile:hover { border-color: rgba(255,255,255,0.28); }
            .nyx-tile.selected { border: 2px solid #7B5EA7; }
            .nyx-sidebar { padding: 8px; }
            """
        )
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        root = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        root.set_margin_top(10)
        root.set_margin_bottom(10)
        root.set_margin_start(10)
        root.set_margin_end(10)
        win.set_content(root)

        root.append(self._build_left_sidebar())
        root.append(self._build_center_grid())
        root.append(self._build_right_panel())

        self._refresh_grid()
        self._refresh_preview()
        win.present()

    def _build_left_sidebar(self) -> Gtk.Widget:
        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        panel.set_size_request(240, -1)
        panel.add_css_class("nyx-sidebar")

        title = Gtk.Label(label="Categories")
        title.set_xalign(0.0)
        title.add_css_class("title-3")
        panel.append(title)

        listbox = Gtk.ListBox()
        listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        for cat in self.cat_map.keys():
            row = Gtk.ListBoxRow()
            lbl = Gtk.Label(label=cat)
            lbl.set_xalign(0.0)
            lbl.set_margin_top(8)
            lbl.set_margin_bottom(8)
            lbl.set_margin_start(8)
            lbl.set_margin_end(8)
            row.set_child(lbl)
            row._cat_name = cat  # type: ignore[attr-defined]
            listbox.append(row)
            if cat == self.current_category:
                listbox.select_row(row)

        def _on_select(_lb: Gtk.ListBox, row: Optional[Gtk.ListBoxRow]) -> None:
            if row is None:
                return
            self.current_category = getattr(row, "_cat_name", "All")
            self.visible_wallpapers = self._filter_wallpapers(self.current_category)
            self._refresh_grid()

        listbox.connect("row-selected", _on_select)
        panel.append(listbox)
        return panel

    def _build_center_grid(self) -> Gtk.Widget:
        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        panel.set_hexpand(True)

        lbl = Gtk.Label(label="Wallpaper Library")
        lbl.set_xalign(0.0)
        lbl.add_css_class("title-3")
        panel.append(lbl)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        flow = Gtk.FlowBox()
        flow.set_selection_mode(Gtk.SelectionMode.NONE)
        flow.set_column_spacing(10)
        flow.set_row_spacing(10)
        flow.set_max_children_per_line(4)
        flow.set_min_children_per_line(3)
        flow.set_homogeneous(True)
        flow.set_margin_top(8)
        flow.set_margin_bottom(8)
        flow.set_margin_start(8)
        flow.set_margin_end(8)
        self.grid_flow = flow
        scroll.set_child(flow)
        panel.append(scroll)
        return panel

    def _build_right_panel(self) -> Gtk.Widget:
        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        panel.set_size_request(460, -1)

        lbl = Gtk.Label(label="Preview & Controls")
        lbl.set_xalign(0.0)
        lbl.add_css_class("title-3")
        panel.append(lbl)

        frame = Gtk.Frame()
        frame.set_hexpand(True)
        frame.set_vexpand(False)
        pic = Gtk.Picture()
        pic.set_content_fit(Gtk.ContentFit.COVER)
        pic.set_size_request(430, 240)
        frame.set_child(pic)
        self.preview_pic = pic
        panel.append(frame)

        stack = Gtk.Stack()
        switcher = Gtk.StackSwitcher(stack=stack)
        panel.append(switcher)
        panel.append(stack)

        stack.add_titled(self._build_adjustments_page(), "adjustments", "Adjustments")
        stack.add_titled(self._build_live_page(), "live", "Live Wallpapers")
        stack.add_titled(self._build_schedule_page(), "schedule", "Scheduling")
        return panel

    def _build_adjustments_page(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)

        self.monitor_model = Gtk.StringList()
        for tgt in self.outputs:
            self.monitor_model.append(tgt.label)
        self.monitor_combo = Gtk.DropDown(model=self.monitor_model)
        self.monitor_combo.set_selected(self._label_index(self.monitor_model, self.cfg.get("monitor_target", "All Monitors")))
        self.monitor_combo.connect("notify::selected", lambda *_: self._on_monitor_changed())
        box.append(self._labeled_row("Apply to", self.monitor_combo))

        b = self._slider("Brightness", self.cfg.get("brightness", 1.0), 0.2, 2.0, lambda v: self._set_cfg("brightness", v))
        s = self._slider("Saturation", self.cfg.get("saturation", 1.0), 0.2, 2.0, lambda v: self._set_cfg("saturation", v))
        c = self._slider("Contrast", self.cfg.get("contrast", 1.0), 0.2, 2.0, lambda v: self._set_cfg("contrast", v))
        blur = self._slider("Blur Amount", self.cfg.get("blur", 0.0), 0.0, 20.0, lambda v: self._set_cfg("blur", v))
        box.append(b)
        box.append(s)
        box.append(c)
        box.append(blur)

        tint_toggle = Gtk.Switch(active=bool(self.cfg.get("tint_enabled", False)))
        tint_toggle.connect("notify::active", lambda sw, _ps: self._set_cfg("tint_enabled", sw.get_active()))
        box.append(self._labeled_row("Color Tint", tint_toggle))

        if hasattr(Gtk, "ColorButton"):
            color_btn = Gtk.ColorButton()
            rgba = Gdk.RGBA()
            rgba.parse(self.cfg.get("tint_color", "#7B5EA7"))
            color_btn.set_rgba(rgba)
            color_btn.connect("color-set", self._on_tint_color)
            box.append(self._labeled_row("Tint Color", color_btn))

        self.fit_model = Gtk.StringList.new(FIT_MODES)
        self.fit_combo = Gtk.DropDown(model=self.fit_model)
        self.fit_combo.set_selected(self._label_index(self.fit_model, self.cfg.get("fit_mode", "Fill")))
        self.fit_combo.connect("notify::selected", lambda *_: self._on_fit_mode_changed())
        box.append(self._labeled_row("Fit Mode", self.fit_combo))

        star = Gtk.ToggleButton(label="★ Favorite")
        star.set_active(self._is_favorite(self.cfg.get("wallpaper", "")))
        star.connect("toggled", self._on_favorite_toggled)
        box.append(star)

        apply_btn = Gtk.Button(label="Apply")
        apply_btn.add_css_class("suggested-action")
        apply_btn.connect("clicked", lambda *_: self._apply_selected())
        box.append(apply_btn)
        return box

    def _build_live_page(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.live_model = Gtk.StringList.new(list(LIVE_PRESETS.keys()))
        self.live_combo = Gtk.DropDown(model=self.live_model)
        self.live_combo.set_selected(self._label_index(self.live_model, self.cfg.get("live_preset", "Particle Drift")))
        self.live_combo.connect("notify::selected", lambda *_: self._on_live_preset_changed())
        box.append(self._labeled_row("Effect", self.live_combo))
        hint = Gtk.Label(
            label="Uses swww transition presets:\nParticle Drift, Rain Overlay, Code Rain, Slow Zoom, Aurora Shimmer"
        )
        hint.set_xalign(0.0)
        hint.set_wrap(True)
        box.append(hint)
        btn = Gtk.Button(label="Apply Live Effect")
        btn.connect("clicked", lambda *_: self._apply_selected(use_live=True))
        box.append(btn)
        return box

    def _build_schedule_page(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        for slot in SLOTS:
            model = Gtk.StringList()
            model.append("(Keep current)")
            for p in self.wallpapers:
                model.append(str(p))
            dd = Gtk.DropDown(model=model)
            cur = self.cfg.get("schedule", {}).get(slot, "")
            dd.set_selected(self._label_index(model, cur) if cur else 0)
            self.schedule_rows[slot] = dd
            self.schedule_models[slot] = model
            box.append(self._labeled_row(slot.capitalize(), dd))

        shuffle_sw = Gtk.Switch(active=bool(self.cfg.get("shuffle_enabled", False)))
        shuffle_sw.connect("notify::active", lambda sw, _ps: self._set_cfg("shuffle_enabled", sw.get_active()))
        box.append(self._labeled_row("Shuffle mode", shuffle_sw))

        interval_model = Gtk.StringList.new(["15", "30", "60", "120"])
        interval_dd = Gtk.DropDown(model=interval_model)
        interval_dd.set_selected(self._label_index(interval_model, str(self.cfg.get("shuffle_interval_minutes", 30))))
        interval_dd.connect("notify::selected", lambda *_: self._on_interval_changed(interval_model, interval_dd))
        box.append(self._labeled_row("Shuffle interval (minutes)", interval_dd))

        save_btn = Gtk.Button(label="Save Scheduling")
        save_btn.add_css_class("suggested-action")
        save_btn.connect("clicked", lambda *_: self._save_schedule())
        box.append(save_btn)
        return box

    def _refresh_grid(self) -> None:
        if not self.grid_flow:
            return
        child = self.grid_flow.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self.grid_flow.remove(child)
            child = nxt
        self.tile_btns.clear()
        current = str(self.cfg.get("wallpaper", ""))
        for wp in self.visible_wallpapers:
            btn = Gtk.Button()
            btn.add_css_class("nyx-tile")
            btn.set_tooltip_text(wp.name)
            if str(wp) == current:
                btn.add_css_class("selected")
            pic = Gtk.Picture.new_for_filename(str(wp))
            pic.set_content_fit(Gtk.ContentFit.COVER)
            pic.set_size_request(220, 130)
            btn.set_child(pic)
            btn.connect("clicked", self._on_tile_clicked, wp)
            self.grid_flow.append(btn)
            self.tile_btns[str(wp)] = btn
        if self.visible_wallpapers and not self.selected_wallpaper:
            self.selected_wallpaper = self.visible_wallpapers[0]
        self._refresh_preview()

    def _refresh_preview(self) -> None:
        if not self.preview_pic:
            return
        if self.selected_wallpaper and self.selected_wallpaper.exists():
            self.preview_pic.set_file(Gio.File.new_for_path(str(self.selected_wallpaper)))

    def _on_tile_clicked(self, _btn: Gtk.Button, wp: Path) -> None:
        self.selected_wallpaper = wp
        self._refresh_preview()

    def _label_index(self, model: Gtk.StringList, val: str) -> int:
        n = model.get_n_items()
        for i in range(n):
            if model.get_string(i) == val:
                return i
        return 0

    def _labeled_row(self, title: str, widget: Gtk.Widget) -> Gtk.Widget:
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lab = Gtk.Label(label=title)
        lab.set_xalign(0.0)
        lab.set_hexpand(True)
        row.append(lab)
        row.append(widget)
        return row

    def _slider(self, title: str, value: float, lo: float, hi: float, on_change) -> Gtk.Widget:
        adj = Gtk.Adjustment(value=float(value), lower=lo, upper=hi, step_increment=0.05)
        scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=adj)
        scale.set_digits(2)
        scale.set_draw_value(True)
        scale.connect("value-changed", lambda s: on_change(float(s.get_value())))
        return self._labeled_row(title, scale)

    def _set_cfg(self, key: str, value) -> None:
        self.cfg[key] = value
        self._save_cfg()

    def _on_monitor_changed(self) -> None:
        if not self.monitor_combo or not self.monitor_model:
            return
        idx = self.monitor_combo.get_selected()
        label = self.monitor_model.get_string(idx) if idx >= 0 else "All Monitors"
        self._set_cfg("monitor_target", label)

    def _on_fit_mode_changed(self) -> None:
        if not self.fit_combo or not self.fit_model:
            return
        idx = self.fit_combo.get_selected()
        val = self.fit_model.get_string(idx) if idx >= 0 else "Fill"
        self._set_cfg("fit_mode", val)

    def _on_live_preset_changed(self) -> None:
        if not self.live_combo or not self.live_model:
            return
        idx = self.live_combo.get_selected()
        val = self.live_model.get_string(idx) if idx >= 0 else "Particle Drift"
        self._set_cfg("live_preset", val)

    def _on_tint_color(self, btn) -> None:
        rgba = btn.get_rgba()
        color = "#{:02X}{:02X}{:02X}".format(
            int(rgba.red * 255), int(rgba.green * 255), int(rgba.blue * 255)
        )
        self._set_cfg("tint_color", color)

    def _is_favorite(self, path: str) -> bool:
        return path in set(self.cfg.get("favorites", []))

    def _on_favorite_toggled(self, btn: Gtk.ToggleButton) -> None:
        if not self.selected_wallpaper:
            return
        p = str(self.selected_wallpaper)
        favs = set(self.cfg.get("favorites", []))
        if btn.get_active():
            favs.add(p)
        else:
            favs.discard(p)
        self.cfg["favorites"] = sorted(favs)
        self._save_cfg()

    def _processed_path(self, src: Path) -> Path:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        key = json.dumps(
            {
                "src": str(src),
                "b": self.cfg.get("brightness", 1.0),
                "s": self.cfg.get("saturation", 1.0),
                "c": self.cfg.get("contrast", 1.0),
                "t": self.cfg.get("tint_enabled", False),
                "tc": self.cfg.get("tint_color", "#7B5EA7"),
                "bl": self.cfg.get("blur", 0.0),
            },
            sort_keys=True,
        )
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
        return CACHE_DIR / f"processed-{digest}.png"

    def _apply_adjustments(self, src: Path) -> Path:
        out = self._processed_path(src)
        if out.exists():
            return out
        img = Image.open(src).convert("RGBA")
        img = ImageEnhance.Brightness(img).enhance(float(self.cfg.get("brightness", 1.0)))
        img = ImageEnhance.Color(img).enhance(float(self.cfg.get("saturation", 1.0)))
        img = ImageEnhance.Contrast(img).enhance(float(self.cfg.get("contrast", 1.0)))
        if self.cfg.get("tint_enabled", False):
            tint = self.cfg.get("tint_color", "#7B5EA7").lstrip("#")
            if len(tint) == 6:
                r = int(tint[0:2], 16)
                g = int(tint[2:4], 16)
                b = int(tint[4:6], 16)
                overlay = Image.new("RGBA", img.size, (r, g, b, 56))
                img = Image.alpha_composite(img, overlay)
        blur = float(self.cfg.get("blur", 0.0))
        if blur > 0:
            img = img.filter(ImageFilter.GaussianBlur(radius=blur))
        out.parent.mkdir(parents=True, exist_ok=True)
        img.save(out, format="PNG")
        return out

    def _target_output_name(self) -> Optional[str]:
        label = self.cfg.get("monitor_target", "All Monitors")
        for tgt in self.outputs:
            if tgt.label == label:
                return tgt.output
        return None

    def _apply_selected(self, use_live: bool = False) -> None:
        if not self.selected_wallpaper or not self.selected_wallpaper.exists():
            return
        src = self.selected_wallpaper
        apply_img = self._apply_adjustments(src)
        if shutil.which("swww"):
            preset_name = self.cfg.get("live_preset", "Particle Drift")
            tr_type, tr_duration = LIVE_PRESETS.get(preset_name, ("any", 1.2))
            if not use_live:
                tr_type, tr_duration = ("any", 1.0)
            cmd = [
                "swww",
                "img",
                str(apply_img),
                "--transition-type",
                tr_type,
                "--transition-duration",
                str(tr_duration),
            ]
            out_name = self._target_output_name()
            if out_name:
                cmd.extend(["-o", out_name])
            _run(cmd, timeout=10)
        elif shutil.which("nyxus-set-wallpaper.sh"):
            _run(["nyxus-set-wallpaper.sh", str(apply_img)], timeout=12)
        self.cfg["wallpaper"] = str(src)
        self._save_cfg()
        self._refresh_grid()

    def _on_interval_changed(self, model: Gtk.StringList, dd: Gtk.DropDown) -> None:
        idx = dd.get_selected()
        val = model.get_string(idx) if idx >= 0 else "30"
        self._set_cfg("shuffle_interval_minutes", int(val))

    def _save_schedule(self) -> None:
        sched = self.cfg.get("schedule", {})
        for slot, dd in self.schedule_rows.items():
            model = self.schedule_models[slot]
            idx = dd.get_selected()
            val = model.get_string(idx) if idx >= 0 else "(Keep current)"
            sched[slot] = "" if val == "(Keep current)" else val
        self.cfg["schedule"] = sched
        self._save_cfg()
        self._write_scheduler_units()

    def _write_scheduler_units(self) -> None:
        SCHED_SCRIPT.parent.mkdir(parents=True, exist_ok=True)
        SCHED_UNIT_DIR.mkdir(parents=True, exist_ok=True)
        script = f"""#!/usr/bin/env bash
set -euo pipefail
CFG="{CFG_PATH}"
if [[ ! -f "$CFG" ]]; then exit 0; fi
readarray -t vals < <(python3 - <<'PYTHON_SCRIPT'
import json,datetime,random,sys,pathlib
p=pathlib.Path("{CFG_PATH}")
cfg=json.loads(p.read_text(encoding="utf-8"))
hour=datetime.datetime.now().hour
if 5 <= hour < 12:
    slot = "morning"
elif 12 <= hour < 17:
    slot = "afternoon"
elif 17 <= hour < 21:
    slot = "evening"
else:
    slot = "night"
sched=cfg.get("schedule",{{}})
shuffle=bool(cfg.get("shuffle_enabled",False))
target=sched.get(slot,"")
walls=[x for x in sched.values() if isinstance(x,str) and x]
if shuffle and walls:
    target=random.choice(walls)
print(target)
print(cfg.get("monitor_target","All Monitors"))
PYTHON_SCRIPT
)
IMG="${{vals[0]:-}}"
OUT="${{vals[1]:-All Monitors}}"
[[ -n "$IMG" && -f "$IMG" ]] || exit 0
if command -v swww >/dev/null 2>&1; then
  if [[ "$OUT" == "All Monitors" ]]; then
    swww img "$IMG" --transition-type any --transition-duration 1.0 >/dev/null 2>&1 || true
  else
    swww img "$IMG" --transition-type any --transition-duration 1.0 -o "$OUT" >/dev/null 2>&1 || true
  fi
elif command -v nyxus-set-wallpaper.sh >/dev/null 2>&1; then
  nyxus-set-wallpaper.sh "$IMG" >/dev/null 2>&1 || true
fi
"""
        SCHED_SCRIPT.write_text(script, encoding="utf-8")
        SCHED_SCRIPT.chmod(0o755)

        service = f"""[Unit]
Description=NYXUS Wallpaper Studio schedule service
[Service]
Type=oneshot
ExecStart={SCHED_SCRIPT}
"""
        interval = int(self.cfg.get("shuffle_interval_minutes", 30))
        timer = f"""[Unit]
Description=NYXUS Wallpaper Studio schedule timer
[Timer]
OnBootSec=2min
OnUnitActiveSec={interval}min
Persistent=true
[Install]
WantedBy=timers.target
"""
        SCHED_SERVICE.write_text(service, encoding="utf-8")
        SCHED_TIMER.write_text(timer, encoding="utf-8")
        _run(["systemctl", "--user", "daemon-reload"], timeout=5)
        _run(["systemctl", "--user", "enable", "--now", "nyxus-wallpaper-studio.timer"], timeout=8)


def main() -> int:
    app = WallpaperStudio()
    return int(app.run([]))


if __name__ == "__main__":
    raise SystemExit(main())
