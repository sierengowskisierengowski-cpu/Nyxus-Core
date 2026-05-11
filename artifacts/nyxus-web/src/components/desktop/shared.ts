// ============================================
// NYXUS — shared desktop primitives
// DARK MIRROR rev r16 (LOCKED) — monochrome only.
// White / off-white / black / dark glass. No neon. No per-app colors.
// Mirrors the actual installed Hyprland system: 26 real apps (3 live iframes
// for the apps that ship a web mirror + 11 tarballs + 12 system Python apps).
// Every entry below corresponds to a real installable file in nyxus-scripts/.
// ============================================
import { useState, useEffect } from "react";

export const BASE = "/api/download/nyxus";

// ── DARK MIRROR PALETTE (matches nyxus_chrome.py + nyxus-palette.css) ────
export const C = {
  // surfaces
  void:         "#000000",
  glassDark:    "rgba(8,12,20,0.55)",     // panels, cards, frames, headerbars
  glassDeeper:  "rgba(15,20,32,0.72)",    // inputs, hovered cards
  glassDeepest: "rgba(5,7,12,0.92)",      // tooltips, popovers, dropdowns
  panelBg:      "rgba(8,12,20,0.55)",     // alias for back-compat

  // hairline + rim
  hairline:     "rgba(255,255,255,0.10)", // 1px white border
  hairlineHi:   "rgba(255,255,255,0.18)", // hover border
  rimDark:      "rgba(0,0,0,0.55)",       // outer drop

  // text
  textPrimary:   "#e8edf5",  // off-white primary
  textSecondary: "#c8ccd6",  // light grey
  textTertiary:  "#6a6e78",  // dim grey
  white:         "#ffffff",  // hover halos + selected pip ONLY
  text:          "#e8edf5",  // alias
  dim:           "#6a6e78",  // alias

  // workspace identity stripes — ONLY allowed color, ONLY on bottom waybar
  ws: ["#ec4899", "#ea7e3c", "#d4a73a", "#6aa872", "#5a8aab", "#8a6aaa", "#ec4899", "#ea7e3c", "#d4a73a"],
};

// Back-compat NEONS export — now monochrome (used by LeftBar workspace pips)
export const NEONS = ["#e8edf5", "#c8ccd6", "#e8edf5", "#c8ccd6", "#e8edf5", "#c8ccd6", "#e8edf5", "#c8ccd6", "#e8edf5"];

// ── APP REGISTRY — all 26 real apps from nyxus-scripts/ ──────────────────
export type AppKind = "iframe" | "mockup";
export type AppDef = {
  id: string;
  name: string;
  glyph: string;
  color: string;          // kept for type-compat — always C.textPrimary now
  kind: AppKind;
  src?: string;
  tagline?: string;
  desc?: string;
  install?: string;
  download?: string;
  modules?: string[];
  category?: "live" | "tarball" | "system";
};

const T = C.textPrimary; // every app uses the same off-white

export const APPS: AppDef[] = [
  // ── LIVE IFRAMES (3) — apps that ship a web mirror alongside the GTK4 app ─
  { id: "notepad",  name: "Notepad",  glyph: "✑", color: T, kind: "iframe", src: "/nyxus-notepad/",  category: "live",
    tagline: "PLAINTEXT EDITOR · GTK4",
    desc: "Frictionless plaintext notebook with autosave to ~/.nyxus/notepad.json. DARK MIRROR chrome." },
  { id: "stickies", name: "Stickies", glyph: "▢", color: T, kind: "iframe", src: "/nyxus-stickies/", category: "live",
    tagline: "STICKY NOTES · GTK4",
    desc: "Pin-to-desktop sticky notes. Layer-shell anchored, auto-persist." },
  { id: "sysmon",   name: "SysMon",   glyph: "◉", color: T, kind: "iframe", src: "/nyxus-sysmon/",   category: "live",
    tagline: "SYSTEM MONITOR · GTK4",
    desc: "Live CPU / memory / network / disk dashboard with dark glass chrome." },

  // ── TARBALL APPS (11) — installed via install.sh ───────────────────
  { id: "godsapp", name: "GodsApp", glyph: "✦", color: T, kind: "mockup", category: "tarball",
    tagline: "9-MODULE SECURITY SUPER TOOL",
    desc: "All-in-one offensive/defensive workstation. udev rules for live device events. Each module is a standalone tab.",
    install: "nyxus_godsapp_install.sh", download: "nyxus-godsapp.tgz",
    modules: ["m01 Network", "m02 Ports", "m03 Packets", "m04 WiFi", "m05 Vulns", "m06 Traffic", "m07 Attack Surface", "m08 OSINT", "m09 Passwords"] },
  { id: "home", name: "Home", glyph: "⌂", color: T, kind: "mockup", category: "tarball",
    tagline: "HOME DASHBOARD",
    desc: "The main dashboard — system glance, recent apps, weather, calendar, news ticker.",
    install: "nyxus_home_install.sh", download: "nyxus-home.tgz",
    modules: ["Glance", "Recent", "Weather", "Calendar", "News"] },
  { id: "intel", name: "INTEL", glyph: "◉", color: T, kind: "mockup", category: "tarball",
    tagline: "OSINT INVESTIGATION WORKSTATION",
    desc: "Email · Phone · IP · Domain · Crypto · Photo · Public Records. Real APIs (HIBP, Shodan, VirusTotal, AbuseIPDB, IPinfo, blockchain.info, Etherscan, FAA, FCC, SEC, FEC, USPTO, OpenSanctions). AES-256-GCM encrypted case storage.",
    install: "nyxus_intel_install.sh", download: "nyxus-intel.tgz",
    modules: ["Email Intel", "Phone Intel", "IP Intel", "Domain Intel", "Crypto Intel", "Photo EXIF", "Public Records", "Case Library"] },
  { id: "passwords", name: "Passwords", glyph: "🔑", color: T, kind: "mockup", category: "tarball",
    tagline: "PASSWORD VAULT · AES-256",
    desc: "Local-first encrypted password vault. AES-256-GCM, Argon2id derivation, autotype helper, browser bridge.",
    install: "nyxus_passwords_install.sh", download: "nyxus-passwords.tgz",
    modules: ["Vault", "Generator", "Autotype", "Bridge", "Audit"] },
  { id: "phantom", name: "Phantom", glyph: "◈", color: T, kind: "mockup", category: "tarball",
    tagline: "STEALTH SECURITY DAEMON",
    desc: "Always-on threat monitor + automated response daemon. Forensics module captures evidence, threats engine fingerprints attackers, response engine isolates compromised processes. Runs as a systemd service.",
    install: "nyxus-phantom.tgz", download: "nyxus-phantom.tgz",
    modules: ["Monitor", "Response", "Forensics", "Threat Engine", "systemd"] },
  { id: "sage", name: "Sage", glyph: "✧", color: T, kind: "mockup", category: "tarball",
    tagline: "RULES + KNOWLEDGE ENGINE",
    desc: "Tabbed Adwaita UI for system rules, audit trails, and knowledge base. CLI companion for headless audits. Pluggable rules engine.",
    install: "nyxus_sage_install.sh", download: "nyxus-sage.tgz",
    modules: ["Rules", "Audit", "Knowledge", "CLI", "UI", "Tabs"] },
  { id: "shield", name: "Shield", glyph: "⛨", color: T, kind: "mockup", category: "tarball",
    tagline: "NETWORK SECURITY SCANNER",
    desc: "Active vulnerability + network exposure scanner. Local scan (open ports, services), network scan (subnet sweep, fingerprinting), persistent SQLite DB.",
    install: "nyxus_security_install.sh", download: "nyxus-shield.tgz",
    modules: ["Local Scan", "Network Sweep", "Service Probe", "Findings DB", "Reports"] },
  { id: "start", name: "Start Menu", glyph: "◐", color: T, kind: "mockup", category: "tarball",
    tagline: "START MENU + BOTTOM BAR",
    desc: "The Start menu (Apps + Store, page-switched layout) and the four custom Waybar buttons: Start, Panel, Notifications, Settings.",
    install: "nyxus_start_install.sh", download: "nyxus-start.tgz",
    modules: ["Apps Page", "Store Page", "Bottom Bar", "Power Menu"] },
  { id: "studio", name: "Creative Studio", glyph: "✎", color: T, kind: "mockup", category: "tarball",
    tagline: "9-MODULE CREATIVE SUITE",
    desc: "Multi-module creative workstation. Cross-module wired with shared engine, UI, audio engine, video engine, 3d engine, and document references.",
    install: "nyxus_studio_install.sh", download: "nyxus-studio.tgz",
    modules: ["m01 Paint", "m02 Vector", "m03 3D", "m04 Video", "m05 Animate", "m06 Photo", "m07 Layout", "m08 Type", "m09 Voice"] },
  { id: "weather", name: "Weather", glyph: "☁", color: T, kind: "mockup", category: "tarball",
    tagline: "WEATHER · GTK4",
    desc: "Local + extended forecast, radar, severe alerts. Sources: NWS, OpenWeatherMap, Met.no.",
    install: "nyxus_weather_install.sh", download: "nyxus-weather.tgz",
    modules: ["Now", "Hourly", "10-Day", "Radar", "Alerts"] },
  { id: "panel", name: "The Panel", glyph: "▦", color: T, kind: "mockup", category: "tarball",
    tagline: "TOPBAR + SETTINGS FLYOUT",
    desc: "Right-side flyout with weather, news ticker, system widgets, and the unified Settings window.",
    install: "nyxus_panel_install.sh", download: "nyxus-panel.tgz",
    modules: ["Appearance", "Profile", "Notifications", "News Sources", "Filters", "Browser", "Cache", "About"] },

  // ── SYSTEM UTILITIES — Python / .desktop entries on the live OS ─────
  // NOTE (rev r6-eww, 2026-05-11): Calendar, Clock, Powermenu, Quicksettings
  // REMOVED from the system-utilities list — all four are now native EWW
  // surfaces. Calendar + Clock live inside the EWW dashboard (Super+`),
  // Powermenu is `eww open --toggle powermenu` (Super+Esc), Quicksettings
  // is the same dashboard. The 5th retired app, Cheatsheet, was already not
  // in this list.
  { id: "control", name: "Control", glyph: "◑", color: T, kind: "mockup", category: "system",
    tagline: "CONTROL CENTER",
    desc: "Quick toggles — wifi, bluetooth, audio, brightness, dnd, idle inhibit.",
    install: "nyxus_control.py" },
  { id: "doctor", name: "Doctor", glyph: "✚", color: T, kind: "mockup", category: "system",
    tagline: "SYSTEM HEALTH AUDIT",
    desc: "Health audit tool — checks chrome bootstrap, palette integrity, app installs, fog daemon, waybar state.",
    install: "nyxus_doctor.py" },
  { id: "launcher", name: "Launcher", glyph: "▣", color: T, kind: "mockup", category: "system",
    tagline: "APP LAUNCHER",
    desc: "Fuzzy launcher (Super-key). Layer-shell overlay, fzf-like ranking.",
    install: "nyxus_launcher.py" },
  { id: "notes", name: "Notes", glyph: "✑", color: T, kind: "mockup", category: "system",
    tagline: "QUICK NOTES",
    desc: "One-shot quick note capture. Different from the full Notepad app.",
    install: "nyxus_notes.py" },
  { id: "screensaver", name: "Screensaver", glyph: "◌", color: T, kind: "mockup", category: "system",
    tagline: "SCREENSAVER + LOCK",
    desc: "Idle-triggered screensaver with the cosmic ink-swirl wallpaper. Doubles as the lockscreen.",
    install: "nyxus_screensaver.py" },
  { id: "screenshot", name: "Screenshot", glyph: "◰", color: T, kind: "mockup", category: "system",
    tagline: "SCREENSHOT TOOL",
    desc: "Region / window / fullscreen capture. PNG to ~/Pictures, optional clipboard, optional annotate.",
    install: "nyxus_screenshot.py" },
  { id: "settings", name: "Settings", glyph: "⚙", color: T, kind: "mockup", category: "system",
    tagline: "SYSTEM SETTINGS",
    desc: "The unified settings window — Appearance / Profile / Notifications / News / Filters / Browser / Cache / About.",
    install: "nyxus_settings.py" },
  { id: "terminal", name: "Terminal", glyph: "▶", color: T, kind: "mockup", category: "system",
    tagline: "TERMINAL · BARE VTE",
    desc: "Bare VTE widget on dark glass. No window chrome — Hyprland's rim-light gradient is the sole frame.",
    install: "nyxus_terminal.py" },
];

// ── HOOKS ────────────────────────────────────────────────────────────────
export function useTime() {
  const [t, setT] = useState(new Date());
  useEffect(() => {
    const i = setInterval(() => setT(new Date()), 1000);
    return () => clearInterval(i);
  }, []);
  return t;
}

export function useWallpaperRotation(intervalMs = 15000) {
  const [idx, setIdx] = useState(() => Math.floor(Math.random() * 16));
  useEffect(() => {
    const i = setInterval(() => setIdx(p => (p + 1) % 16), intervalMs);
    return () => clearInterval(i);
  }, [intervalMs]);
  const file = `nyxus-bg-${String(idx + 1).padStart(2, "0")}.png`;
  return { idx, file, url: `${BASE}/${file}` };
}

// ── SHARED STYLE FRAGMENTS ───────────────────────────────────────────────
export const FRAME = {
  background: C.glassDark,
  border: `1px solid ${C.hairline}`,
  borderRadius: 14,
  backdropFilter: "blur(14px) saturate(1.1)",
  WebkitBackdropFilter: "blur(14px) saturate(1.1)",
} as const;
