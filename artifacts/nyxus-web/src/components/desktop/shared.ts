// ============================================
// NYXUS — shared desktop primitives
// Palette, app registry, hooks used by every desktop component.
// ============================================
import { useState, useEffect } from "react";

export const BASE = "/api/download/nyxus";

// ── PALETTE (matches waybar-style.css and the actual Hyprland build) ─────
export const C = {
  pink:    "#ff00ff",
  cyan:    "#22d3ee",
  purple:  "#cc00ff",
  gold:    "#ffff00",
  indigo:  "#8800ff",
  green:   "#39ff14",
  orange:  "#ff5500",
  blue:    "#0088ff",
  red:     "#ff3344",
  white:   "#ffffff",
  text:    "#e8e0f5",
  dim:     "#9b8db8",
  panelBg: "rgba(4,2,10,0.86)",
  void:    "#080808",
};

// neon palette cycled across workspace circles + launcher icons
export const NEONS = [C.pink, C.cyan, C.gold, C.green, C.purple, C.orange, C.blue, C.indigo, C.red];

// ── APP REGISTRY ─────────────────────────────────────────────────────────
export type AppKind = "iframe" | "mockup";
export type AppDef = {
  id: string;
  name: string;
  glyph: string;
  color: string;
  kind: AppKind;
  src?: string;
  tagline?: string;
  desc?: string;
  install?: string;
  download?: string;
  modules?: string[];
};

export const APPS: AppDef[] = [
  { id: "notepad",  name: "Notepad",  glyph: "✑", color: C.purple, kind: "iframe", src: "/nyxus-notepad/" },
  { id: "stickies", name: "Stickies", glyph: "▢", color: C.gold,   kind: "iframe", src: "/nyxus-stickies/" },
  { id: "sysmon",   name: "SysMon",   glyph: "◉", color: C.green,  kind: "iframe", src: "/nyxus-sysmon/" },
  { id: "widgets",  name: "Widgets",  glyph: "◍", color: C.cyan,   kind: "iframe", src: "/nyxus-widgets/" },
  {
    id: "intel", name: "INTEL", glyph: "◉", color: C.purple, kind: "mockup",
    tagline: "OSINT INVESTIGATION WORKSTATION",
    desc: "Email · Phone · IP · Domain · Crypto · Photo · Public Records. Real APIs (HIBP, Shodan, VirusTotal, AbuseIPDB, IPinfo, blockchain.info, Etherscan, FAA, FCC, SEC, FEC, USPTO, OpenSanctions). AES-256-GCM encrypted case storage with passwordless device-key auth.",
    install: "nyxus_intel_install.sh", download: "nyxus-intel.tgz",
    modules: ["Email Intel", "Phone Intel", "IP Intel", "Domain Intel", "Crypto Intel", "Photo EXIF", "Public Records", "Case Library"],
  },
  {
    id: "phantom", name: "Phantom", glyph: "◈", color: C.blue, kind: "mockup",
    tagline: "STEALTH SECURITY DAEMON",
    desc: "Always-on threat monitor + automated response daemon. Forensics module captures evidence, threats engine fingerprints attackers, response engine isolates compromised processes. Runs as a systemd service.",
    download: "nyxus-phantom.tgz",
    modules: ["Monitor", "Response", "Forensics", "Threat Engine", "systemd"],
  },
  {
    id: "shield", name: "Shield", glyph: "⛨", color: C.green, kind: "mockup",
    tagline: "NETWORK SECURITY SCANNER",
    desc: "Active vulnerability + network exposure scanner. Local scan (open ports, services), network scan (subnet sweep, fingerprinting), persistent SQLite DB of findings. NYXUS-themed GTK UI.",
    install: "nyxus_security_install.sh", download: "nyxus-shield.tgz",
    modules: ["Local Scan", "Network Sweep", "Service Probe", "Findings DB", "Reports"],
  },
  {
    id: "godsapp", name: "GodsApp", glyph: "✦", color: C.gold, kind: "mockup",
    tagline: "9-MODULE SECURITY SUPER TOOL",
    desc: "All-in-one offensive/defensive workstation. udev rules for live device events. Each module is a standalone tab with its own engine, UI, and persistence.",
    install: "nyxus_godsapp_install.sh", download: "nyxus-godsapp.tgz",
    modules: ["m01 Network", "m02 Ports", "m03 Packets", "m04 WiFi", "m05 Vulns", "m06 Traffic", "m07 Attack Surface", "m08 OSINT", "m09 Passwords"],
  },
  {
    id: "sage", name: "Sage", glyph: "✧", color: C.pink, kind: "mockup",
    tagline: "RULES + KNOWLEDGE ENGINE",
    desc: "Tabbed Adwaita UI for system rules, audit trails, and knowledge base. CLI companion for headless audits. Pluggable rules engine — add your own checks as Python modules.",
    install: "nyxus_sage_install.sh", download: "nyxus-sage.tgz",
    modules: ["Rules", "Audit", "Knowledge", "CLI", "UI", "Tabs"],
  },
  {
    id: "panel", name: "Panel", glyph: "▦", color: C.purple, kind: "mockup",
    tagline: "TOPBAR + SETTINGS FLYOUT",
    desc: "The Panel — right-side flyout with weather, news ticker, system widgets, and the unified Settings window (Appearance / Profile / Notifications / News Sources / Filters / Browser / Cache / About).",
    install: "nyxus_panel_install.sh", download: "nyxus-panel.tgz",
    modules: ["Appearance", "Profile", "Notifications", "News Sources", "Filters", "Browser", "Cache", "About"],
  },
  {
    id: "start", name: "Start Menu", glyph: "◐", color: C.cyan, kind: "mockup",
    tagline: "START MENU + BOTTOM BAR",
    desc: "The Start menu (Apps page + Store page, page-switched layout) and the four custom Waybar bottom-bar buttons: Start, The Panel, Notifications, Settings. Idempotent installer that won't double-add.",
    install: "nyxus_start_install.sh", download: "nyxus-start.tgz",
    modules: ["Apps Page", "Store Page", "Bottom Bar", "Power Menu"],
  },
  {
    id: "studio", name: "Creative Studio", glyph: "✎", color: C.orange, kind: "mockup",
    tagline: "9-MODULE CREATIVE SUITE",
    desc: "Multi-module creative workstation. Cross-module wired with shared engine, UI, audio engine, video engine, 3d engine, and document references.",
    install: "nyxus_studio_install.sh", download: "nyxus-studio.tgz",
    modules: ["m01 Paint", "m02 Vector", "m03 3D", "m04 Video", "m05 Animate", "m06 Photo", "m07 Layout", "m08 Type", "m09 Voice"],
  },
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
  const [idx, setIdx] = useState(() => Math.floor(Math.random() * 15));
  useEffect(() => {
    const i = setInterval(() => setIdx(p => (p + 1) % 15), intervalMs);
    return () => clearInterval(i);
  }, [intervalMs]);
  const file = `nyxus-bg-${String(idx + 1).padStart(2, "0")}.png`;
  return { idx, file, url: `${BASE}/${file}` };
}
