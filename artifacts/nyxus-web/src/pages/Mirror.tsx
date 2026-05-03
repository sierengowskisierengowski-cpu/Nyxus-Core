// ============================================
// NYXUS — nyx-2026.05.02-x86_64.iso
// Copyright © 2026 Joseph Sierengowski
// All Rights Reserved
// NYX-J5W-2026-SIERENGOWSKI-LOCKED
// ============================================
//
// /mirror — exact visual mirror of the NYXUS Hyprland desktop.
// Thin neon-outlined frames (pink top/bottom/left, gold right), colored
// workspace circles, app launcher squares on the right edge, and a
// wallpaper-only desktop. Click any launcher icon to open that app
// in a window. Web mockups (Notepad, Stickies, SysMon, Widgets) load
// as live iframes; the 8 tarball apps open NYXUS-themed previews.

import { useState, useEffect, ReactNode } from "react";
import HomeDashboard from "./HomeDashboard";

const BASE = "/api/download/nyxus";

// ── PALETTE (matches waybar-style.css and the actual Hyprland build) ─────
const C = {
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
const NEONS = [C.pink, C.cyan, C.gold, C.green, C.purple, C.orange, C.blue, C.indigo, C.red];

// ── APP REGISTRY ─────────────────────────────────────────────────────────
type AppKind = "iframe" | "mockup";
type AppDef = {
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

const APPS: AppDef[] = [
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
    install: "nyxus-phantom.tgz", download: "nyxus-phantom.tgz",
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
function useTime() {
  const [t, setT] = useState(new Date());
  useEffect(() => {
    const i = setInterval(() => setT(new Date()), 1000);
    return () => clearInterval(i);
  }, []);
  return t;
}

function useWallpaperRotation(intervalMs = 15000) {
  const [idx, setIdx] = useState(() => Math.floor(Math.random() * 15));
  useEffect(() => {
    const i = setInterval(() => setIdx(p => (p + 1) % 15), intervalMs);
    return () => clearInterval(i);
  }, [intervalMs]);
  const file = `nyxus-bg-${String(idx + 1).padStart(2, "0")}.png`;
  return { idx, file, url: `${BASE}/${file}` };
}

// ── STAT CHIP (top bar left) ─────────────────────────────────────────────
function Stat({ glyph, value, color }: { glyph: string; value: string; color: string }) {
  return (
    <span style={{
      display: "inline-flex",
      alignItems: "center",
      gap: 4,
      color,
      fontSize: "0.62rem",
      fontFamily: '"JetBrains Mono", monospace',
      letterSpacing: "0.05em",
      textShadow: `0 0 4px ${color}88`,
      whiteSpace: "nowrap",
    }}>
      <span style={{ fontSize: "0.7rem" }}>{glyph}</span>
      <span style={{ color: C.text }}>{value}</span>
    </span>
  );
}

// ── TOP BAR ──────────────────────────────────────────────────────────────
function TopBar({ time }: { time: Date }) {
  const hh = String(time.getHours()).padStart(2, "0");
  const mm = String(time.getMinutes()).padStart(2, "0");
  const ss = String(time.getSeconds()).padStart(2, "0");
  const date = time.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });

  return (
    <div style={{
      position: "fixed",
      top: 6, left: 6, right: 6,
      height: 22,
      background: C.panelBg,
      border: `1px solid ${C.pink}`,
      borderRadius: 4,
      boxShadow: `0 0 10px ${C.pink}66, 0 0 20px ${C.pink}33, inset 0 0 10px rgba(255,0,255,0.06)`,
      display: "flex",
      alignItems: "center",
      padding: "0 8px",
      fontFamily: '"JetBrains Mono", monospace',
      zIndex: 50,
      userSelect: "none",
      backdropFilter: "blur(6px)",
    }}>
      <div style={{ flex: 1, display: "flex", alignItems: "center", gap: 12, overflow: "hidden" }}>
        <Stat glyph="◉" value="CPU 15%"      color={C.purple} />
        <Stat glyph="▲" value="TEMP 84°C"    color={C.orange} />
        <Stat glyph="↓" value="0KB/s"        color={C.green} />
        <Stat glyph="↑" value="0KB/s"        color={C.green} />
        <Stat glyph="⊘" value="NO-WIFI"      color={C.red} />
        <Stat glyph="▣" value="92%"          color={C.gold} />
        <Stat glyph="◧" value="DISK 35%"     color={C.cyan} />
      </div>
      <div style={{ flex: "0 0 auto", padding: "0 1.2rem", fontWeight: 800, letterSpacing: "0.18em", fontSize: "0.7rem" }}>
        <span style={{ color: C.pink   }}>N</span>
        <span style={{ color: C.orange }}> Y</span>
        <span style={{ color: C.gold   }}> X</span>
        <span style={{ color: C.green  }}> U</span>
        <span style={{ color: C.blue   }}> S</span>
      </div>
      <div style={{ flex: 1, display: "flex", justifyContent: "flex-end", alignItems: "center", gap: 10, color: C.text, fontSize: "0.62rem" }}>
        <span style={{ color: C.dim }}>{date}</span>
        <span style={{ color: C.cyan, fontSize: "0.65rem" }}>▢</span>
        <span style={{ fontWeight: 700, color: C.text }}>{hh}:{mm}:{ss}</span>
      </div>
    </div>
  );
}

// ── LEFT BAR (workspaces + power) ────────────────────────────────────────
function LeftBar({ activeWs, onSelect }: { activeWs: number; onSelect: (n: number) => void }) {
  return (
    <div style={{
      position: "fixed",
      top: 32, left: 6, bottom: 32,
      width: 32,
      background: C.panelBg,
      border: `1px solid ${C.pink}`,
      borderRadius: 4,
      boxShadow: `0 0 10px ${C.pink}66, 0 0 20px ${C.pink}33`,
      backdropFilter: "blur(6px)",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      padding: "8px 0",
      gap: 7,
      zIndex: 50,
      userSelect: "none",
    }}>
      {Array.from({ length: 9 }).map((_, i) => {
        const n = i + 1;
        const color = NEONS[i];
        const active = n === activeWs;
        return (
          <button
            key={n}
            onClick={() => onSelect(n)}
            title={`Workspace ${n}`}
            style={{
              width: 20, height: 20,
              borderRadius: "50%",
              background: active
                ? `radial-gradient(circle at 35% 35%, ${color}, ${color}66 70%, transparent)`
                : `radial-gradient(circle at 35% 35%, ${color}cc, ${color}44 70%, transparent)`,
              border: `1.5px solid ${color}`,
              boxShadow: active
                ? `0 0 12px ${color}, 0 0 24px ${color}88, inset 0 0 4px rgba(255,255,255,0.4)`
                : `0 0 6px ${color}88, inset 0 0 3px rgba(255,255,255,0.2)`,
              color: "#0a0612",
              fontSize: "0.6rem",
              fontWeight: 900,
              fontFamily: '"JetBrains Mono", monospace',
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              padding: 0,
              transition: "all 0.15s",
            }}
          >
            {n}
          </button>
        );
      })}
      <div style={{ flex: 1 }} />
      <button
        title="Power"
        style={{
          width: 22, height: 22,
          borderRadius: 4,
          background: `${C.red}22`,
          border: `1px solid ${C.red}`,
          color: C.red,
          fontSize: "0.85rem",
          cursor: "pointer",
          textShadow: `0 0 6px ${C.red}`,
          padding: 0,
          display: "flex", alignItems: "center", justifyContent: "center",
        }}
      >⏻</button>
    </div>
  );
}

// ── RIGHT BAR (app launcher) ─────────────────────────────────────────────
function RightBar({ onLaunch, openId }: { onLaunch: (a: AppDef) => void; openId: string | null }) {
  return (
    <div style={{
      position: "fixed",
      top: 32, right: 6, bottom: 32,
      width: 36,
      background: C.panelBg,
      border: `1px solid ${C.gold}`,
      borderRadius: 4,
      boxShadow: `0 0 10px ${C.gold}66, 0 0 20px ${C.gold}33`,
      backdropFilter: "blur(6px)",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      padding: "6px 0",
      gap: 5,
      zIndex: 50,
      userSelect: "none",
      overflowY: "auto",
    }}>
      {APPS.map(a => {
        const active = a.id === openId;
        return (
          <button
            key={a.id}
            onClick={() => onLaunch(a)}
            title={a.name}
            style={{
              width: 26, height: 26,
              borderRadius: 4,
              background: `linear-gradient(145deg, ${a.color}cc 0%, ${a.color}66 60%, ${a.color}22 100%)`,
              border: active ? `2px solid ${C.white}` : `1.5px solid ${a.color}`,
              boxShadow: active
                ? `0 0 14px ${a.color}, 0 0 26px ${a.color}88, inset 0 0 4px rgba(255,255,255,0.5)`
                : `0 0 6px ${a.color}99, inset 0 0 3px rgba(255,255,255,0.25)`,
              color: "#0a0612",
              fontSize: "0.85rem",
              fontWeight: 900,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              padding: 0,
              transition: "all 0.15s",
              textShadow: "0 1px 2px rgba(255,255,255,0.4)",
            }}
            onMouseEnter={e => {
              e.currentTarget.style.transform = "scale(1.1)";
            }}
            onMouseLeave={e => {
              e.currentTarget.style.transform = "scale(1)";
            }}
          >
            {a.glyph}
          </button>
        );
      })}
    </div>
  );
}

// ── BOTTOM BAR (Start | workspace pager | gear time Panel Notifications) ─
function BottomBar({ activeWs, onSelectWs, onStart, onHome, onSettings, onPanel, onNotif, time }: {
  activeWs: number;
  onSelectWs: (n: number) => void;
  onStart: () => void;
  onHome: () => void;
  onSettings: () => void;
  onPanel: () => void;
  onNotif: () => void;
  time: Date;
}) {
  const hh = String(time.getHours()).padStart(2, "0");
  const mm = String(time.getMinutes()).padStart(2, "0");
  const ss = String(time.getSeconds()).padStart(2, "0");
  return (
    <div style={{
      position: "fixed",
      bottom: 6, left: 6, right: 6,
      height: 24,
      background: C.panelBg,
      border: `1px solid ${C.pink}`,
      borderRadius: 4,
      boxShadow: `0 0 10px ${C.pink}66, 0 0 20px ${C.pink}33`,
      backdropFilter: "blur(6px)",
      display: "flex",
      alignItems: "center",
      padding: "0 8px",
      gap: 8,
      zIndex: 50,
      userSelect: "none",
      fontFamily: '"JetBrains Mono", monospace',
    }}>
      {/* Start button */}
      <button
        onClick={onStart}
        style={{
          background: "transparent",
          border: "none",
          color: C.cyan,
          fontSize: "0.72rem",
          letterSpacing: "0.06em",
          fontWeight: 700,
          cursor: "pointer",
          padding: "1px 8px",
          textShadow: `0 0 6px ${C.cyan}88`,
          fontFamily: "'Caveat', cursive",
        }}
        onMouseEnter={e => { e.currentTarget.style.color = C.pink; }}
        onMouseLeave={e => { e.currentTarget.style.color = C.cyan; }}
      >
        Start
      </button>

      {/* Home button (workspace 0 — dashboard) */}
      <button
        onClick={onHome}
        title="Home dashboard (workspace 0)"
        style={{
          background: activeWs === 0 ? `${C.pink}22` : "transparent",
          border: activeWs === 0 ? `1px solid ${C.pink}88` : "1px solid transparent",
          color: activeWs === 0 ? C.pink : C.gold,
          fontSize: "0.72rem",
          letterSpacing: "0.04em",
          fontWeight: 700,
          cursor: "pointer",
          padding: "0px 8px",
          textShadow: `0 0 6px ${activeWs === 0 ? C.pink : C.gold}88`,
          fontFamily: "'Caveat', cursive",
          borderRadius: 3,
          display: "flex",
          alignItems: "center",
          gap: 4,
        }}
        onMouseEnter={e => { if (activeWs !== 0) e.currentTarget.style.color = C.pink; }}
        onMouseLeave={e => { if (activeWs !== 0) e.currentTarget.style.color = C.gold; }}
      >
        <span style={{ fontSize: "0.8rem", lineHeight: 1 }}>⌂</span> Home
      </button>

      {/* center: workspace pager */}
      <div style={{ flex: 1, display: "flex", justifyContent: "center", alignItems: "center", gap: 6 }}>
        {Array.from({ length: 6 }).map((_, i) => {
          const n = i + 1;
          const color = NEONS[i];
          const active = n === activeWs;
          return (
            <button
              key={n}
              onClick={() => onSelectWs(n)}
              title={`Workspace ${n}`}
              style={{
                width: 16, height: 16,
                borderRadius: "50%",
                background: active
                  ? `radial-gradient(circle at 35% 35%, ${color}, ${color}66 70%)`
                  : `radial-gradient(circle at 35% 35%, ${color}aa, ${color}33 70%)`,
                border: `1.2px solid ${color}`,
                boxShadow: active
                  ? `0 0 8px ${color}, 0 0 16px ${color}88`
                  : `0 0 4px ${color}66`,
                color: "#0a0612",
                fontSize: "0.5rem",
                fontWeight: 900,
                cursor: "pointer",
                padding: 0,
                display: "flex", alignItems: "center", justifyContent: "center",
              }}
            >
              {n}
            </button>
          );
        })}
      </div>

      {/* right cluster: gear time | The Panel | Notifications */}
      <button
        onClick={onSettings}
        title="Settings"
        style={{
          background: "transparent", border: "none",
          color: C.gold, fontSize: "0.85rem",
          cursor: "pointer", padding: "0 4px",
          textShadow: `0 0 6px ${C.gold}88`,
        }}
      >⚙&#xFE0E;</button>
      <span style={{ color: C.text, fontSize: "0.65rem", fontWeight: 700, letterSpacing: "0.04em" }}>
        {hh}:{mm}:{ss}
      </span>
      <button
        onClick={onPanel}
        style={{
          background: "transparent", border: "none",
          color: C.purple, fontSize: "0.72rem",
          letterSpacing: "0.04em", fontWeight: 700, cursor: "pointer",
          padding: "1px 8px", textShadow: `0 0 6px ${C.purple}88`,
          fontFamily: "'Caveat', cursive",
        }}
        onMouseEnter={e => { e.currentTarget.style.color = C.pink; }}
        onMouseLeave={e => { e.currentTarget.style.color = C.purple; }}
      >
        The Panel
      </button>
      <button
        onClick={onNotif}
        style={{
          background: "transparent", border: "none",
          color: C.green, fontSize: "0.72rem",
          letterSpacing: "0.04em", fontWeight: 700, cursor: "pointer",
          padding: "1px 8px", textShadow: `0 0 6px ${C.green}88`,
          fontFamily: "'Caveat', cursive",
        }}
        onMouseEnter={e => { e.currentTarget.style.color = C.cyan; }}
        onMouseLeave={e => { e.currentTarget.style.color = C.green; }}
      >
        Notifications
      </button>
    </div>
  );
}

// ── WINDOW SHELL ─────────────────────────────────────────────────────────
function Window({ a, onClose, children }: { a: AppDef; onClose: () => void; children: ReactNode }) {
  return (
    <div style={{
      position: "fixed",
      top: 40, bottom: 40, left: 50, right: 56,
      maxWidth: 1180,
      margin: "0 auto",
      background: "rgba(8,6,16,0.96)",
      border: `1px solid ${a.color}`,
      borderTop: `2px solid ${a.color}`,
      borderRadius: 6,
      boxShadow: `0 0 40px ${a.color}66, 0 0 100px rgba(0,0,0,0.85), inset 0 0 80px rgba(0,0,0,0.4)`,
      display: "flex",
      flexDirection: "column",
      overflow: "hidden",
      zIndex: 100,
      backdropFilter: "blur(4px)",
    }}>
      <div style={{
        flex: "0 0 auto",
        height: 28,
        background: `linear-gradient(180deg, ${a.color}22 0%, rgba(0,0,0,0.55) 100%)`,
        borderBottom: `1px solid ${a.color}55`,
        display: "flex",
        alignItems: "center",
        padding: "0 0.6rem",
        gap: 10,
        userSelect: "none",
      }}>
        <div style={{ display: "flex", gap: 5 }}>
          {[C.green, C.gold, C.red].map(c => (
            <span key={c} style={{ width: 9, height: 9, borderRadius: "50%", background: c, opacity: 0.7, boxShadow: `0 0 4px ${c}` }} />
          ))}
        </div>
        <span style={{ color: a.color, fontSize: "0.85rem", textShadow: `0 0 8px ${a.color}` }}>{a.glyph}</span>
        <span style={{
          color: a.color,
          fontSize: "0.85rem",
          fontFamily: "'Caveat', cursive",
          letterSpacing: "0.04em",
          fontWeight: 700,
          textShadow: `0 0 6px ${a.color}55`,
        }}>
          {a.name}
        </span>
        <span style={{ color: C.dim, fontSize: "0.55rem", letterSpacing: "0.18em", opacity: 0.6 }}>
          NYXUS · WINDOW
        </span>
        <div style={{ flex: 1 }} />
        <button
          onClick={onClose}
          style={{
            background: "transparent",
            border: `1px solid ${C.red}66`,
            color: C.red,
            fontSize: "0.6rem",
            cursor: "pointer",
            borderRadius: 2,
            padding: "2px 8px",
            letterSpacing: "0.15em",
          }}
          onMouseEnter={e => { e.currentTarget.style.background = `${C.red}22`; }}
          onMouseLeave={e => { e.currentTarget.style.background = "transparent"; }}
        >
          ✕ CLOSE
        </button>
      </div>
      <div style={{ flex: 1, overflow: "auto", background: C.void }}>
        {children}
      </div>
    </div>
  );
}

// ── MOCKUP BODY (for tarball apps) ───────────────────────────────────────
function MockupBody({ a }: { a: AppDef }) {
  const curl = `curl -fsSL "${window.location.origin}${BASE}/${a.install}" | bash`;
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(curl);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };
  return (
    <div style={{
      display: "grid",
      gridTemplateColumns: "180px 1fr",
      height: "100%",
      minHeight: 320,
      fontFamily: '"JetBrains Mono", monospace',
      color: C.text,
    }}>
      <div style={{
        background: "rgba(12,8,22,0.95)",
        borderRight: `1px solid ${a.color}33`,
        padding: "1rem 0.6rem",
        display: "flex", flexDirection: "column", gap: 4,
      }}>
        <div style={{ fontSize: "0.55rem", color: `${a.color}aa`, letterSpacing: "0.22em", padding: "0.3rem 0.5rem", marginBottom: 6 }}>
          MODULES
        </div>
        {a.modules?.map((m, i) => (
          <div key={m} style={{
            fontSize: "0.7rem",
            color: i === 0 ? a.color : C.dim,
            background: i === 0 ? `${a.color}1a` : "transparent",
            border: i === 0 ? `1px solid ${a.color}55` : "1px solid transparent",
            borderLeft: i === 0 ? `3px solid ${a.color}` : "3px solid transparent",
            padding: "0.4rem 0.6rem",
            borderRadius: 2,
            textShadow: i === 0 ? `0 0 5px ${a.color}88` : "none",
            fontFamily: "'Caveat', cursive",
          }}>
            ◈ {m}
          </div>
        ))}
        <div style={{ flex: 1 }} />
        <div style={{ fontSize: "0.5rem", color: "#444", letterSpacing: "0.18em", padding: "0.4rem 0.5rem" }}>
          NYX-J5W-2026
        </div>
      </div>

      <div style={{ padding: "1.2rem 1.5rem", display: "flex", flexDirection: "column", gap: "1rem", overflow: "auto" }}>
        <div>
          <div style={{ fontSize: "0.55rem", color: `${a.color}aa`, letterSpacing: "0.22em", marginBottom: 4 }}>
            {a.tagline}
          </div>
          <div style={{
            fontSize: "1.7rem",
            color: a.color,
            fontWeight: 800,
            letterSpacing: "0.04em",
            textShadow: `0 0 14px ${a.color}66`,
            fontFamily: "'Caveat', cursive",
          }}>
            NYXUS {a.name}
          </div>
        </div>

        <p style={{ margin: 0, fontSize: "0.78rem", color: C.dim, lineHeight: 1.7, maxWidth: 720 }}>
          {a.desc}
        </p>

        <div style={{
          flex: 1,
          minHeight: 140,
          border: `2px dashed ${a.color}44`,
          borderRadius: 4,
          padding: "1rem",
          background: `radial-gradient(ellipse at center, ${a.color}08 0%, transparent 70%)`,
          display: "flex", flexDirection: "column",
          alignItems: "center", justifyContent: "center", gap: 8,
        }}>
          <div style={{ fontSize: "2.4rem", color: a.color, textShadow: `0 0 24px ${a.color}` }}>{a.glyph}</div>
          <div style={{ fontSize: "0.65rem", color: a.color, letterSpacing: "0.2em", opacity: 0.7 }}>
            GTK4 PYTHON · NATIVE LINUX APP
          </div>
          <div style={{ fontSize: "0.6rem", color: C.dim, letterSpacing: "0.05em", maxWidth: 420, textAlign: "center" }}>
            Runs natively on the NYXUS desktop. Install on your Hyprland system with the curl command below — this preview is a reference of what's shipped.
          </div>
        </div>

        <div style={{
          background: "rgba(0,0,0,0.65)",
          border: `1px solid ${a.color}33`,
          borderRadius: 3,
          padding: "0.65rem 0.85rem",
          display: "flex", alignItems: "center", gap: 8,
        }}>
          <code style={{ flex: 1, fontSize: "0.7rem", color: C.text, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            <span style={{ color: "#444" }}>$</span> curl -fsSL "<span style={{ color: a.color }}>$BASE/{a.install}</span>" | bash
          </code>
          <button
            onClick={copy}
            style={{
              background: copied ? `${a.color}33` : "transparent",
              border: `1px solid ${copied ? a.color : "#333"}`,
              color: copied ? a.color : C.dim,
              padding: "3px 10px",
              borderRadius: 2,
              fontSize: "0.6rem",
              cursor: "pointer",
              letterSpacing: "0.05em",
            }}
          >
            {copied ? "COPIED" : "COPY"}
          </button>
        </div>

        <div style={{ display: "flex", gap: 8 }}>
          <a
            href={`${BASE}/${a.download}`} download={a.download}
            style={{
              flex: 1, textAlign: "center", padding: "0.5rem",
              background: `${a.color}14`, border: `1px solid ${a.color}66`,
              color: a.color, textDecoration: "none",
              fontSize: "0.65rem", letterSpacing: "0.15em",
              borderRadius: 2, fontWeight: 700,
              textShadow: `0 0 6px ${a.color}88`,
            }}
          >
            ▼ DOWNLOAD {a.download}
          </a>
          <a
            href={`${BASE}/${a.install}`} download={a.install}
            style={{
              flex: 1, textAlign: "center", padding: "0.5rem",
              background: "transparent", border: `1px solid ${a.color}33`,
              color: `${a.color}cc`, textDecoration: "none",
              fontSize: "0.65rem", letterSpacing: "0.15em",
              borderRadius: 2, fontWeight: 700,
            }}
          >
            ▼ INSTALL.SH
          </a>
        </div>
      </div>
    </div>
  );
}

// ── PANEL FLYOUT ─────────────────────────────────────────────────────────
function PanelFlyout({ open, onClose }: { open: boolean; onClose: () => void }) {
  const time = useTime();
  if (!open) return null;
  return (
    <div style={{
      position: "fixed",
      top: 32, bottom: 32, right: 46,
      width: 320,
      background: "rgba(8,6,16,0.96)",
      border: `1px solid ${C.purple}66`,
      borderTop: `2px solid ${C.purple}`,
      borderRadius: 6,
      boxShadow: `0 0 40px ${C.purple}66`,
      backdropFilter: "blur(6px)",
      padding: "1rem 1.1rem",
      display: "flex", flexDirection: "column", gap: "0.85rem",
      zIndex: 80,
      fontFamily: '"JetBrains Mono", monospace',
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <div>
          <div style={{ fontSize: "0.5rem", color: `${C.purple}aa`, letterSpacing: "0.22em" }}>NYXUS · PANEL</div>
          <div style={{ fontSize: "1.1rem", color: C.purple, fontFamily: "'Caveat', cursive", textShadow: `0 0 10px ${C.purple}55` }}>The Panel</div>
        </div>
        <button onClick={onClose} style={{ background: "transparent", border: `1px solid ${C.red}66`, color: C.red, padding: "2px 8px", fontSize: "0.6rem", cursor: "pointer", borderRadius: 2 }}>✕</button>
      </div>

      <div style={{ border: `1px solid ${C.gold}44`, borderLeft: `3px solid ${C.gold}`, borderRadius: 3, padding: "0.75rem 0.85rem", background: "rgba(255,255,0,0.04)" }}>
        <div style={{ fontSize: "0.55rem", color: `${C.gold}aa`, letterSpacing: "0.18em" }}>WEATHER</div>
        <div style={{ display: "flex", alignItems: "baseline", gap: 8, marginTop: 4 }}>
          <div style={{ fontSize: "1.6rem", color: C.gold, textShadow: `0 0 12px ${C.gold}66`, fontFamily: "'Caveat', cursive" }}>72°F</div>
          <div style={{ fontSize: "0.65rem", color: C.dim }}>Clear · Light breeze</div>
        </div>
      </div>

      <div style={{ border: `1px solid ${C.cyan}44`, borderLeft: `3px solid ${C.cyan}`, borderRadius: 3, padding: "0.75rem 0.85rem", background: "rgba(34,211,238,0.04)" }}>
        <div style={{ fontSize: "0.55rem", color: `${C.cyan}aa`, letterSpacing: "0.18em" }}>NEWS</div>
        <div style={{ fontSize: "0.7rem", color: C.text, marginTop: 4, lineHeight: 1.5 }}>
          NYXUS v2.0 ships with 8 tarball apps and 4-bar Waybar
        </div>
      </div>

      <div style={{ border: `1px solid ${C.purple}44`, borderLeft: `3px solid ${C.purple}`, borderRadius: 3, padding: "0.75rem 0.85rem", background: "rgba(204,0,255,0.04)" }}>
        <div style={{ fontSize: "0.55rem", color: `${C.purple}aa`, letterSpacing: "0.18em" }}>CLOCK</div>
        <div style={{ fontSize: "1.4rem", color: C.purple, textShadow: `0 0 12px ${C.purple}66`, fontFamily: "'Caveat', cursive", marginTop: 2 }}>
          {String(time.getHours()).padStart(2, "0")}:{String(time.getMinutes()).padStart(2, "0")}
        </div>
        <div style={{ fontSize: "0.6rem", color: C.dim }}>{time.toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric", year: "numeric" })}</div>
      </div>

      <div style={{ flex: 1 }} />
      <div style={{ fontSize: "0.5rem", color: "#444", letterSpacing: "0.2em", textAlign: "center" }}>
        © 2026 JOSEPH SIERENGOWSKI
      </div>
    </div>
  );
}

// ── START MENU ───────────────────────────────────────────────────────────
function StartMenu({ open, onClose, onLaunch }: { open: boolean; onClose: () => void; onLaunch: (a: AppDef) => void }) {
  if (!open) return null;
  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.7)",
        backdropFilter: "blur(6px)",
        zIndex: 90,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "60px 40px",
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          width: "100%", maxWidth: 820, maxHeight: "100%",
          background: "rgba(8,6,16,0.97)",
          border: `1px solid ${C.cyan}66`,
          borderTop: `2px solid ${C.cyan}`,
          borderRadius: 8,
          boxShadow: `0 0 60px ${C.cyan}55`,
          padding: "1.5rem 1.75rem",
          display: "flex", flexDirection: "column", gap: "1rem",
          fontFamily: '"JetBrains Mono", monospace',
          overflow: "auto",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
          <div>
            <div style={{ fontSize: "0.55rem", color: `${C.cyan}aa`, letterSpacing: "0.22em" }}>NYXUS · START</div>
            <div style={{ fontSize: "1.4rem", color: C.cyan, fontFamily: "'Caveat', cursive", textShadow: `0 0 10px ${C.cyan}55` }}>All apps</div>
          </div>
          <button onClick={onClose} style={{ background: "transparent", border: `1px solid ${C.red}66`, color: C.red, padding: "3px 10px", fontSize: "0.65rem", cursor: "pointer", borderRadius: 2, letterSpacing: "0.15em" }}>✕ CLOSE</button>
        </div>

        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(120px, 1fr))",
          gap: 10,
        }}>
          {APPS.map(a => (
            <button
              key={a.id}
              onClick={() => { onLaunch(a); onClose(); }}
              style={{
                display: "flex", flexDirection: "column",
                alignItems: "center", gap: 6,
                padding: "0.8rem 0.6rem",
                background: "rgba(0,0,0,0.4)",
                border: `1px solid ${a.color}44`,
                borderTop: `2px solid ${a.color}`,
                borderRadius: 4,
                cursor: "pointer",
                color: a.color,
                transition: "all 0.15s",
              }}
              onMouseEnter={e => { e.currentTarget.style.background = `${a.color}1a`; }}
              onMouseLeave={e => { e.currentTarget.style.background = "rgba(0,0,0,0.4)"; }}
            >
              <div style={{ fontSize: "1.6rem", color: a.color, textShadow: `0 0 12px ${a.color}` }}>{a.glyph}</div>
              <div style={{ fontSize: "0.85rem", fontFamily: "'Caveat', cursive", letterSpacing: "0.04em", color: a.color }}>
                {a.name}
              </div>
              <div style={{ fontSize: "0.45rem", color: C.dim, letterSpacing: "0.1em" }}>
                {a.kind === "iframe" ? "LIVE" : "MOCKUP"}
              </div>
            </button>
          ))}
        </div>

        <div style={{ borderTop: `1px solid ${C.cyan}22`, paddingTop: "0.75rem", display: "flex", justifyContent: "space-between", fontSize: "0.55rem", color: "#555", letterSpacing: "0.18em" }}>
          <span>{APPS.length} APPS</span>
          <span>NYX-J5W-2026-SIERENGOWSKI-LOCKED</span>
        </div>
      </div>
    </div>
  );
}

// ── NOTIFICATIONS ────────────────────────────────────────────────────────
function Notifications({ open, onClose }: { open: boolean; onClose: () => void }) {
  if (!open) return null;
  const items = [
    { glyph: "◉", color: C.purple, title: "INTEL",    body: "Investigation auto-saved (3 findings)." },
    { glyph: "⛨", color: C.green,  title: "Shield",   body: "Local scan complete — 0 open ports outside policy." },
    { glyph: "◈", color: C.blue,   title: "Phantom",  body: "Daemon armed. 0 threats since boot." },
    { glyph: "✦", color: C.gold,   title: "GodsApp",  body: "WiFi audit module ready." },
    { glyph: "✑", color: C.purple, title: "Notepad",  body: "5 notes synced to ~/.nyxus/notepad.json." },
  ];
  return (
    <div onClick={onClose} style={{ position: "fixed", inset: 0, zIndex: 85 }}>
      <div
        onClick={e => e.stopPropagation()}
        style={{
          position: "absolute",
          bottom: 36, right: 14,
          width: 320,
          background: "rgba(8,6,16,0.96)",
          border: `1px solid ${C.green}66`,
          borderTop: `2px solid ${C.green}`,
          borderRadius: 6,
          padding: "0.9rem 1rem",
          display: "flex", flexDirection: "column", gap: 6,
          fontFamily: '"JetBrains Mono", monospace',
          boxShadow: `0 0 28px ${C.green}55`,
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 4 }}>
          <div style={{ fontSize: "0.55rem", color: `${C.green}aa`, letterSpacing: "0.22em" }}>NYXUS · NOTIFICATIONS</div>
          <button onClick={onClose} style={{ background: "transparent", border: `1px solid ${C.red}66`, color: C.red, padding: "1px 7px", fontSize: "0.55rem", cursor: "pointer", borderRadius: 2 }}>✕</button>
        </div>
        {items.map((n, i) => (
          <div key={i} style={{
            border: `1px solid ${n.color}33`,
            borderLeft: `3px solid ${n.color}`,
            background: `${n.color}0a`,
            padding: "0.5rem 0.65rem",
            borderRadius: 3,
            display: "flex", gap: 8, alignItems: "flex-start",
          }}>
            <span style={{ color: n.color, fontSize: "0.85rem", textShadow: `0 0 6px ${n.color}88` }}>{n.glyph}</span>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: "0.85rem", color: n.color, fontFamily: "'Caveat', cursive", letterSpacing: "0.04em" }}>{n.title}</div>
              <div style={{ fontSize: "0.6rem", color: C.dim, lineHeight: 1.5, marginTop: 1 }}>{n.body}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── SETTINGS WINDOW ──────────────────────────────────────────────────────
function SettingsWindow({ open, onClose }: { open: boolean; onClose: () => void }) {
  const sections = [
    { id: "appearance",    label: "Appearance",    color: C.purple, glyph: "◐" },
    { id: "profile",       label: "Profile",       color: C.cyan,   glyph: "✦" },
    { id: "notifications", label: "Notifications", color: C.gold,   glyph: "✉" },
    { id: "news",          label: "News Sources",  color: C.orange, glyph: "▦" },
    { id: "filters",       label: "Filters",       color: C.green,  glyph: "⊘" },
    { id: "browser",       label: "Browser",       color: C.indigo, glyph: "◍" },
    { id: "cache",         label: "Cache",         color: C.pink,   glyph: "◧" },
    { id: "about",         label: "About",         color: C.gold,   glyph: "ⓘ" },
  ];
  const [active, setActive] = useState("appearance");
  if (!open) return null;
  const sec = sections.find(s => s.id === active)!;
  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed", inset: 0,
        background: "rgba(0,0,0,0.65)",
        backdropFilter: "blur(4px)",
        zIndex: 90,
        display: "flex", alignItems: "center", justifyContent: "center",
        padding: 50,
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          width: "100%", maxWidth: 720,
          height: "100%", maxHeight: 480,
          background: "rgba(8,6,16,0.97)",
          border: `1px solid ${sec.color}66`,
          borderTop: `2px solid ${sec.color}`,
          borderRadius: 6,
          boxShadow: `0 0 50px ${sec.color}44`,
          display: "grid",
          gridTemplateColumns: "180px 1fr",
          fontFamily: '"JetBrains Mono", monospace',
          overflow: "hidden",
        }}
      >
        <div style={{ background: "rgba(12,8,22,0.85)", borderRight: `1px solid ${sec.color}22`, padding: "0.85rem 0.5rem" }}>
          <div style={{ fontSize: "0.55rem", color: `${sec.color}99`, letterSpacing: "0.22em", padding: "0.3rem 0.5rem", marginBottom: 4 }}>SETTINGS</div>
          {sections.map(s => {
            const isActive = s.id === active;
            return (
              <button
                key={s.id}
                onClick={() => setActive(s.id)}
                style={{
                  width: "100%", textAlign: "left",
                  background: isActive ? `${s.color}1a` : "transparent",
                  border: isActive ? `1px solid ${s.color}55` : "1px solid transparent",
                  borderLeft: isActive ? `3px solid ${s.color}` : "3px solid transparent",
                  color: isActive ? s.color : C.dim,
                  padding: "0.4rem 0.55rem",
                  borderRadius: 2,
                  cursor: "pointer",
                  fontSize: "0.85rem",
                  fontFamily: "'Caveat', cursive",
                  letterSpacing: "0.04em",
                  marginBottom: 2,
                  display: "flex", alignItems: "center", gap: 6,
                  textShadow: isActive ? `0 0 5px ${s.color}88` : "none",
                }}
              >
                <span>{s.glyph}</span>
                <span>{s.label}</span>
              </button>
            );
          })}
        </div>
        <div style={{ padding: "1rem 1.25rem", display: "flex", flexDirection: "column", gap: "0.85rem", overflow: "auto" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
            <div>
              <div style={{ fontSize: "0.55rem", color: `${sec.color}99`, letterSpacing: "0.22em" }}>SECTION</div>
              <div style={{ fontSize: "1.5rem", color: sec.color, fontFamily: "'Caveat', cursive", textShadow: `0 0 10px ${sec.color}55` }}>{sec.label}</div>
            </div>
            <button onClick={onClose} style={{ background: "transparent", border: `1px solid ${C.red}66`, color: C.red, padding: "3px 10px", fontSize: "0.6rem", cursor: "pointer", borderRadius: 2, letterSpacing: "0.15em" }}>✕ CLOSE</button>
          </div>
          <div style={{ flex: 1, border: `2px dashed ${sec.color}44`, borderRadius: 4, padding: "1rem", background: `radial-gradient(ellipse at center, ${sec.color}08 0%, transparent 70%)`, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 8 }}>
            <div style={{ fontSize: "2.4rem", color: sec.color, textShadow: `0 0 24px ${sec.color}` }}>{sec.glyph}</div>
            <div style={{ fontSize: "0.65rem", color: sec.color, letterSpacing: "0.2em" }}>{sec.label.toUpperCase()} PANE</div>
            <div style={{ fontSize: "0.6rem", color: C.dim, textAlign: "center", maxWidth: 360, lineHeight: 1.6 }}>
              Mirror of the NYXUS Panel · Settings sidebar nav. Same layout as the GTK4 Settings window shipped in <code style={{ color: sec.color }}>nyxus-panel.tgz</code>.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── MAIN PAGE ────────────────────────────────────────────────────────────
export default function Mirror() {
  const time = useTime();
  const wp = useWallpaperRotation(15000);

  const [activeWs, setActiveWs] = useState(0);
  const [openApp, setOpenApp] = useState<AppDef | null>(null);
  const [showStart, setShowStart] = useState(false);
  const [showPanel, setShowPanel] = useState(false);
  const [showNotif, setShowNotif] = useState(false);
  const [showSettings, setShowSettings] = useState(false);

  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setOpenApp(null);
        setShowStart(false);
        setShowPanel(false);
        setShowNotif(false);
        setShowSettings(false);
      }
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, []);

  return (
    <div style={{
      position: "fixed",
      inset: 0,
      overflow: "hidden",
      background: C.void,
      fontFamily: '"JetBrains Mono", monospace',
    }}>
      {/* Caveat font import (UI signature font) */}
      <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Caveat:wght@400;700&family=JetBrains+Mono:wght@400;700&display=swap" />

      {/* full-bleed wallpaper */}
      <div style={{
        position: "absolute",
        inset: 0,
        backgroundImage: `url(${wp.url})`,
        backgroundSize: "cover",
        backgroundPosition: "center",
        transition: "background-image 1.5s ease-in-out",
      }} />

      {/* dark vignette */}
      <div style={{
        position: "absolute", inset: 0,
        background: "radial-gradient(ellipse at center, rgba(0,0,0,0.18) 0%, rgba(0,0,0,0.42) 100%)",
        pointerEvents: "none",
      }} />

      {/* Bars (neon-outlined floating frames) */}
      <TopBar time={time} />
      <LeftBar  activeWs={activeWs} onSelect={setActiveWs} />
      <RightBar onLaunch={(a) => setOpenApp(a)} openId={openApp?.id ?? null} />
      <BottomBar
        activeWs={activeWs}
        onSelectWs={setActiveWs}
        time={time}
        onHome     ={() => { setActiveWs(0); setShowStart(false); setShowPanel(false); setShowNotif(false); setShowSettings(false); }}
        onStart    ={() => { setShowStart(s => !s);    setShowPanel(false); setShowNotif(false); setShowSettings(false); }}
        onPanel    ={() => { setShowPanel(s => !s);    setShowStart(false); setShowNotif(false); setShowSettings(false); }}
        onNotif    ={() => { setShowNotif(s => !s);    setShowStart(false); setShowPanel(false); setShowSettings(false); }}
        onSettings ={() => { setShowSettings(s => !s); setShowStart(false); setShowPanel(false); setShowNotif(false); }}
      />

      {/* HOME DASHBOARD (workspace 0) — sits inside the desktop area between bars */}
      {activeWs === 0 && (
        <div style={{
          position: "absolute",
          top: 32,
          left: 46,
          right: 50,
          bottom: 32,
          zIndex: 40,
          overflow: "hidden",
        }}>
          <HomeDashboard />
        </div>
      )}

      {/* Wallpaper + back-to-portal labels (tiny, corner) */}
      <div style={{
        position: "absolute",
        top: 34, left: 46,
        background: "rgba(8,6,16,0.7)",
        border: "1px solid #1a1a1a",
        color: C.dim,
        fontSize: "0.5rem",
        padding: "2px 7px",
        letterSpacing: "0.18em",
        borderRadius: 2,
        fontFamily: '"JetBrains Mono", monospace',
        zIndex: 60,
      }}>
        WALLPAPER {String(wp.idx + 1).padStart(2, "0")}/15
      </div>
      <a
        href="#/"
        style={{
          position: "absolute",
          top: 34, right: 50,
          background: "rgba(8,6,16,0.7)",
          border: `1px solid ${C.purple}66`,
          color: C.purple,
          fontSize: "0.55rem",
          padding: "2px 8px",
          textDecoration: "none",
          letterSpacing: "0.18em",
          borderRadius: 2,
          fontFamily: '"JetBrains Mono", monospace',
          textShadow: `0 0 6px ${C.purple}88`,
          zIndex: 60,
        }}
      >
        ◀ BACK TO PORTAL
      </a>

      {/* Flyouts */}
      <PanelFlyout open={showPanel} onClose={() => setShowPanel(false)} />
      <Notifications open={showNotif} onClose={() => setShowNotif(false)} />
      <StartMenu open={showStart} onClose={() => setShowStart(false)} onLaunch={(a) => setOpenApp(a)} />
      <SettingsWindow open={showSettings} onClose={() => setShowSettings(false)} />

      {/* App window */}
      {openApp && (
        <Window a={openApp} onClose={() => setOpenApp(null)}>
          {openApp.kind === "iframe" ? (
            <iframe
              title={openApp.name}
              src={openApp.src}
              style={{ width: "100%", height: "100%", border: "none", background: C.void }}
            />
          ) : (
            <MockupBody a={openApp} />
          )}
        </Window>
      )}
    </div>
  );
}
