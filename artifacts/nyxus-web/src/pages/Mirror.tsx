// ============================================
// NYXUS — nyx-2026.05.02-x86_64.iso
// Copyright © 2026 Joseph Sierengowski
// All Rights Reserved
// NYX-J5W-2026-SIERENGOWSKI-LOCKED
// ============================================
//
// /mirror — exact visual mirror of the NYXUS Hyprland desktop.
// 4-bar Waybar (top pink, bottom cyan, left purple, right gold),
// rotating wallpaper, clickable app icons that open windows.
// Web-app mockups (Notepad, Stickies, SysMon, Widgets) load as
// live iframes. Tarball apps (INTEL, Phantom, Shield, GodsApp,
// Sage, Panel, Start, Studio) open NYXUS-themed window previews.

import { useState, useEffect, useRef, ReactNode } from "react";

const BASE = "/api/download/nyxus";

// ── PALETTE (matches waybar-style.css and the Hyprland build) ────────────
const C = {
  pink:   "#ff00ff",
  cyan:   "#22d3ee",
  purple: "#cc00ff",
  gold:   "#ffff00",
  indigo: "#8800ff",
  green:  "#39ff14",
  orange: "#ff5500",
  blue:   "#0088ff",
  red:    "#ff3344",
  text:   "#e8e0f5",
  dim:    "#b8a8d0",
  bg:     "rgba(16, 12, 28, 0.91)",
  void:   "#080808",
};

// ── APP REGISTRY ────────────────────────────────────────────────────────────
type AppKind = "iframe" | "mockup";
type AppDef = {
  id: string;
  name: string;
  glyph: string;
  color: string;
  kind: AppKind;
  // iframe apps
  src?: string;
  // mockup apps
  tagline?: string;
  desc?: string;
  install?: string;
  download?: string;
  modules?: string[];
};

const APPS: AppDef[] = [
  // ── live web mockup iframes ──────────────────────────────────────────────
  {
    id: "notepad",
    name: "Notepad",
    glyph: "✑",
    color: C.purple,
    kind: "iframe",
    src: "/nyxus-notepad/",
  },
  {
    id: "stickies",
    name: "Stickies",
    glyph: "▢",
    color: C.gold,
    kind: "iframe",
    src: "/nyxus-stickies/",
  },
  {
    id: "sysmon",
    name: "SysMon",
    glyph: "◉",
    color: C.green,
    kind: "iframe",
    src: "/nyxus-sysmon/",
  },
  {
    id: "widgets",
    name: "Widgets",
    glyph: "◍",
    color: C.cyan,
    kind: "iframe",
    src: "/nyxus-widgets/",
  },
  // ── 8 tarball apps as styled previews ────────────────────────────────────
  {
    id: "intel",
    name: "INTEL",
    glyph: "◉",
    color: C.purple,
    kind: "mockup",
    tagline: "OSINT INVESTIGATION WORKSTATION",
    desc: "Email · Phone · IP · Domain · Crypto · Photo · Public Records. Real APIs (HIBP, Shodan, VirusTotal, AbuseIPDB, IPinfo, blockchain.info, Etherscan, FAA, FCC, SEC, FEC, USPTO, OpenSanctions). AES-256-GCM encrypted case storage with passwordless device-key auth.",
    install: "nyxus_intel_install.sh",
    download: "nyxus-intel.tgz",
    modules: ["Email Intel", "Phone Intel", "IP Intel", "Domain Intel", "Crypto Intel", "Photo EXIF", "Public Records", "Case Library"],
  },
  {
    id: "phantom",
    name: "Phantom",
    glyph: "◈",
    color: C.blue,
    kind: "mockup",
    tagline: "STEALTH SECURITY DAEMON",
    desc: "Always-on threat monitor + automated response daemon. Forensics module captures evidence, threats engine fingerprints attackers, response engine isolates compromised processes. Runs as a systemd service.",
    install: "nyxus-phantom.tgz",
    download: "nyxus-phantom.tgz",
    modules: ["Monitor", "Response", "Forensics", "Threat Engine", "systemd"],
  },
  {
    id: "shield",
    name: "Shield",
    glyph: "⛨",
    color: C.green,
    kind: "mockup",
    tagline: "NETWORK SECURITY SCANNER",
    desc: "Active vulnerability + network exposure scanner. Local scan (open ports, services), network scan (subnet sweep, fingerprinting), persistent SQLite DB of findings. NYXUS-themed GTK UI.",
    install: "nyxus_security_install.sh",
    download: "nyxus-shield.tgz",
    modules: ["Local Scan", "Network Sweep", "Service Probe", "Findings DB", "Reports"],
  },
  {
    id: "godsapp",
    name: "GodsApp",
    glyph: "✦",
    color: C.gold,
    kind: "mockup",
    tagline: "9-MODULE SECURITY SUPER TOOL",
    desc: "All-in-one offensive/defensive workstation. udev rules for live device events. Each module is a standalone tab with its own engine, UI, and persistence.",
    install: "nyxus_godsapp_install.sh",
    download: "nyxus-godsapp.tgz",
    modules: ["m01 Network", "m02 Ports", "m03 Packets", "m04 WiFi", "m05 Vulns", "m06 Traffic", "m07 Attack Surface", "m08 OSINT", "m09 Passwords"],
  },
  {
    id: "sage",
    name: "Sage",
    glyph: "✧",
    color: C.pink,
    kind: "mockup",
    tagline: "RULES + KNOWLEDGE ENGINE",
    desc: "Tabbed Adwaita UI for system rules, audit trails, and knowledge base. CLI companion for headless audits. Pluggable rules engine — add your own checks as Python modules.",
    install: "nyxus_sage_install.sh",
    download: "nyxus-sage.tgz",
    modules: ["Rules", "Audit", "Knowledge", "CLI", "UI", "Tabs"],
  },
  {
    id: "panel",
    name: "Panel",
    glyph: "▦",
    color: C.purple,
    kind: "mockup",
    tagline: "TOPBAR + SETTINGS FLYOUT",
    desc: "The Panel — right-side flyout with weather, news ticker, system widgets, and the unified Settings window (Appearance / Profile / Notifications / News Sources / Filters / Browser / Cache / About).",
    install: "nyxus_panel_install.sh",
    download: "nyxus-panel.tgz",
    modules: ["Appearance", "Profile", "Notifications", "News Sources", "Filters", "Browser", "Cache", "About"],
  },
  {
    id: "start",
    name: "Start Menu",
    glyph: "◐",
    color: C.cyan,
    kind: "mockup",
    tagline: "START MENU + BOTTOM BAR",
    desc: "The Start menu (Apps page + Store page, page-switched layout) and the four custom Waybar bottom-bar buttons: Start, The Panel, Notifications, Settings. Idempotent installer that won't double-add.",
    install: "nyxus_start_install.sh",
    download: "nyxus-start.tgz",
    modules: ["Apps Page", "Store Page", "Bottom Bar", "Power Menu"],
  },
  {
    id: "studio",
    name: "Creative Studio",
    glyph: "✎",
    color: C.orange,
    kind: "mockup",
    tagline: "9-MODULE CREATIVE SUITE",
    desc: "Multi-module creative workstation. Cross-module wired with shared engine, UI, audio engine, video engine, 3d engine, and document references.",
    install: "nyxus_studio_install.sh",
    download: "nyxus-studio.tgz",
    modules: ["m01 Paint", "m02 Vector", "m03 3D", "m04 Video", "m05 Animate", "m06 Photo", "m07 Layout", "m08 Type", "m09 Voice"],
  },
];

// ── HOOKS ──────────────────────────────────────────────────────────────────
function useTime() {
  const [time, setTime] = useState(new Date());
  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);
  return time;
}

function useWallpaperRotation(intervalMs = 12000) {
  const [idx, setIdx] = useState(() => Math.floor(Math.random() * 15));
  useEffect(() => {
    const t = setInterval(() => setIdx(i => (i + 1) % 15), intervalMs);
    return () => clearInterval(t);
  }, [intervalMs]);
  const file = `nyxus-bg-${String(idx + 1).padStart(2, "0")}.png`;
  return { idx, file, url: `${BASE}/${file}` };
}

// ── BARS ───────────────────────────────────────────────────────────────────
function TopBar({ time }: { time: Date }) {
  const [tickerIdx, setTickerIdx] = useState(0);
  const ticker = [
    "NYXUS OS v2.0  ·  SILENT  ·  DARK  ·  PURELY FUNCTIONAL",
    "© 2026 JOSEPH SIERENGOWSKI  ·  NYX-J5W-2026-SIERENGOWSKI-LOCKED",
    "AES-256-GCM ARMED  ·  TAMPER MANIFEST OK  ·  SYSTEM OPERATIONAL",
    "8 TARBALL APPS  ·  8 DESKTOP WIDGETS  ·  4 BOOT COMPONENTS  ·  15 WALLPAPERS",
  ];
  useEffect(() => {
    const t = setInterval(() => setTickerIdx(i => (i + 1) % ticker.length), 4000);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const hh = String(time.getHours()).padStart(2, "0");
  const mm = String(time.getMinutes()).padStart(2, "0");
  const ss = String(time.getSeconds()).padStart(2, "0");
  const date = time.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });

  return (
    <div style={{
      position: "fixed",
      top: 0, left: 0, right: 0,
      height: 28,
      background: C.bg,
      borderBottom: `2px solid ${C.pink}`,
      boxShadow: `0 0 18px ${C.pink}55, inset 0 -1px 0 rgba(255,0,255,0.18)`,
      backdropFilter: "blur(8px)",
      display: "flex",
      alignItems: "center",
      padding: "0 0.5rem",
      fontSize: "0.62rem",
      fontFamily: '"JetBrains Mono", monospace',
      color: C.text,
      letterSpacing: "0.04em",
      zIndex: 50,
      userSelect: "none",
    }}>
      <div style={{ flex: 1, color: C.dim, fontSize: "0.6rem", overflow: "hidden", whiteSpace: "nowrap", textOverflow: "ellipsis" }}>
        ▸ {ticker[tickerIdx]}
      </div>
      <div style={{ flex: "0 0 auto", padding: "0 1rem", fontWeight: 700, letterSpacing: "0.08em" }}>
        <span style={{ color: C.pink }}>N</span>
        <span style={{ color: C.orange }}> Y</span>
        <span style={{ color: C.gold }}> X</span>
        <span style={{ color: C.green }}> U</span>
        <span style={{ color: C.blue }}> S</span>
      </div>
      <div style={{ flex: 1, display: "flex", justifyContent: "flex-end", alignItems: "center", gap: "0.85rem", color: C.dim }}>
        <span style={{ color: C.purple }}>  42%</span>
        <span style={{ color: C.indigo }}>  56%</span>
        <span style={{ color: C.green }}>  61°C</span>
        <span style={{ color: C.gold }}>  180.2 KB/s</span>
        <span style={{ color: C.text, fontWeight: 700 }}>{hh}:{mm}:{ss}</span>
        <span style={{ color: C.dim, fontSize: "0.55rem" }}>{date}</span>
      </div>
    </div>
  );
}

function LeftBar({ activeWs, onSelect }: { activeWs: number; onSelect: (n: number) => void }) {
  return (
    <div style={{
      position: "fixed",
      top: 28, bottom: 28, left: 0,
      width: 32,
      background: C.bg,
      borderRight: `2px solid ${C.purple}`,
      boxShadow: `0 0 18px ${C.purple}55, inset -1px 0 0 rgba(204,0,255,0.18)`,
      backdropFilter: "blur(8px)",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      gap: 6,
      padding: "10px 0",
      zIndex: 50,
      userSelect: "none",
      fontFamily: '"JetBrains Mono", monospace',
    }}>
      {Array.from({ length: 9 }).map((_, i) => {
        const n = i + 1;
        const active = n === activeWs;
        return (
          <button
            key={n}
            onClick={() => onSelect(n)}
            style={{
              width: 22, height: 22,
              border: `1px solid ${active ? C.purple : "rgba(204,0,255,0.2)"}`,
              background: active ? `${C.purple}33` : "transparent",
              color: active ? C.purple : C.dim,
              fontSize: "0.62rem",
              fontWeight: active ? 700 : 400,
              cursor: "pointer",
              borderRadius: 3,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              textShadow: active ? `0 0 6px ${C.purple}` : "none",
            }}
            title={`Workspace ${n}`}
          >
            {n}
          </button>
        );
      })}
      <div style={{ flex: 1 }} />
      <div style={{ fontSize: "0.5rem", color: C.purple, writingMode: "vertical-rl", letterSpacing: "0.25em", opacity: 0.5 }}>
        HYPRLAND
      </div>
    </div>
  );
}

function RightBar() {
  const items = [
    { glyph: "▮▮▮", label: "VOL 73", color: C.gold },
    { glyph: "◢", label: "WIFI", color: C.gold },
    { glyph: "✦", label: "BT", color: C.gold },
    { glyph: "◐", label: "BRIGHT 80%", color: C.gold },
    { glyph: "☼", label: "DAY", color: C.orange },
    { glyph: "⊘", label: "DND", color: C.dim },
    { glyph: "▣", label: "BAT 92%", color: C.green },
  ];
  return (
    <div style={{
      position: "fixed",
      top: 28, bottom: 28, right: 0,
      width: 32,
      background: C.bg,
      borderLeft: `2px solid ${C.gold}`,
      boxShadow: `0 0 18px ${C.gold}55, inset 1px 0 0 rgba(255,255,0,0.18)`,
      backdropFilter: "blur(8px)",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      gap: 12,
      padding: "10px 0",
      zIndex: 50,
      userSelect: "none",
      fontFamily: '"JetBrains Mono", monospace',
    }}>
      {items.map((it, i) => (
        <div key={i} title={it.label} style={{
          color: it.color,
          fontSize: "0.7rem",
          textShadow: `0 0 6px ${it.color}`,
          cursor: "default",
        }}>
          {it.glyph}
        </div>
      ))}
      <div style={{ flex: 1 }} />
      <div style={{ fontSize: "0.5rem", color: C.gold, writingMode: "vertical-rl", letterSpacing: "0.25em", opacity: 0.5 }}>
        TRAY
      </div>
    </div>
  );
}

function BottomBar({ onStart, onPanel, onNotif, onSettings }: {
  onStart: () => void;
  onPanel: () => void;
  onNotif: () => void;
  onSettings: () => void;
}) {
  const buttons = [
    { label: "START",         glyph: "◐", action: onStart    },
    { label: "PANEL",         glyph: "▦", action: onPanel    },
    { label: "NOTIFICATIONS", glyph: "✉", action: onNotif    },
    { label: "SETTINGS",      glyph: "⚙", action: onSettings },
  ];
  return (
    <div style={{
      position: "fixed",
      bottom: 0, left: 0, right: 0,
      height: 28,
      background: C.bg,
      borderTop: `2px solid ${C.cyan}`,
      boxShadow: `0 0 18px ${C.cyan}55, inset 0 1px 0 rgba(34,211,238,0.18)`,
      backdropFilter: "blur(8px)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      gap: 4,
      zIndex: 50,
      userSelect: "none",
      fontFamily: '"JetBrains Mono", monospace',
    }}>
      {buttons.map(b => (
        <button
          key={b.label}
          onClick={b.action}
          style={{
            background: "transparent",
            border: `1px solid ${C.cyan}55`,
            color: C.cyan,
            fontSize: "0.6rem",
            letterSpacing: "0.15em",
            padding: "3px 12px",
            borderRadius: 3,
            cursor: "pointer",
            transition: "all 0.15s",
            textShadow: `0 0 6px ${C.cyan}88`,
            display: "flex",
            alignItems: "center",
            gap: 5,
          }}
          onMouseEnter={e => {
            e.currentTarget.style.background = `${C.cyan}22`;
            e.currentTarget.style.borderColor = C.cyan;
          }}
          onMouseLeave={e => {
            e.currentTarget.style.background = "transparent";
            e.currentTarget.style.borderColor = `${C.cyan}55`;
          }}
        >
          <span>{b.glyph}</span>
          <span>{b.label}</span>
        </button>
      ))}
    </div>
  );
}

// ── DESKTOP ICON ───────────────────────────────────────────────────────────
function DesktopIcon({ a, onOpen }: { a: AppDef; onOpen: () => void }) {
  return (
    <button
      onClick={onOpen}
      onDoubleClick={onOpen}
      style={{
        background: "transparent",
        border: "1px solid transparent",
        cursor: "pointer",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 4,
        padding: "8px 6px",
        width: 84,
        borderRadius: 4,
        transition: "all 0.15s",
        userSelect: "none",
      }}
      onMouseEnter={e => {
        e.currentTarget.style.background = `${a.color}14`;
        e.currentTarget.style.borderColor = `${a.color}55`;
      }}
      onMouseLeave={e => {
        e.currentTarget.style.background = "transparent";
        e.currentTarget.style.borderColor = "transparent";
      }}
    >
      <div style={{
        width: 48, height: 48,
        borderRadius: 8,
        background: `linear-gradient(145deg, ${a.color}28, ${C.void})`,
        border: `1px solid ${a.color}88`,
        boxShadow: `0 0 16px ${a.color}55, inset 0 0 12px rgba(0,0,0,0.6)`,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: "1.5rem",
        color: a.color,
        textShadow: `0 0 12px ${a.color}`,
      }}>
        {a.glyph}
      </div>
      <div style={{
        fontSize: "0.62rem",
        color: C.text,
        fontFamily: "'Caveat', cursive",
        textShadow: "0 1px 4px rgba(0,0,0,0.95), 0 0 6px rgba(0,0,0,0.85)",
        letterSpacing: "0.02em",
        textAlign: "center",
        lineHeight: 1.1,
      }}>
        {a.name}
      </div>
    </button>
  );
}

// ── WINDOW SHELL ───────────────────────────────────────────────────────────
function Window({ a, onClose, children }: { a: AppDef; onClose: () => void; children: ReactNode }) {
  return (
    <div style={{
      position: "fixed",
      top: 50, bottom: 38, left: 44, right: 44,
      maxWidth: 1180,
      margin: "0 auto",
      background: "rgba(8,6,16,0.96)",
      border: `1px solid ${a.color}88`,
      borderTop: `2px solid ${a.color}`,
      borderRadius: 6,
      boxShadow: `0 0 60px ${a.color}55, 0 0 120px rgba(0,0,0,0.8), inset 0 0 100px rgba(0,0,0,0.4)`,
      display: "flex",
      flexDirection: "column",
      overflow: "hidden",
      zIndex: 100,
      backdropFilter: "blur(4px)",
    }}>
      {/* title bar */}
      <div style={{
        flex: "0 0 auto",
        height: 30,
        background: `linear-gradient(180deg, ${a.color}22 0%, rgba(0,0,0,0.5) 100%)`,
        borderBottom: `1px solid ${a.color}44`,
        display: "flex",
        alignItems: "center",
        padding: "0 0.6rem",
        gap: 10,
        userSelect: "none",
      }}>
        <div style={{ display: "flex", gap: 5 }}>
          {[C.green, C.gold, C.red].map(c => (
            <span key={c} style={{ width: 10, height: 10, borderRadius: "50%", background: c, opacity: 0.7, boxShadow: `0 0 6px ${c}` }} />
          ))}
        </div>
        <span style={{ color: a.color, fontSize: "0.85rem", textShadow: `0 0 8px ${a.color}` }}>{a.glyph}</span>
        <span style={{
          color: a.color,
          fontSize: "0.78rem",
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
            fontSize: "0.65rem",
            cursor: "pointer",
            borderRadius: 2,
            padding: "2px 9px",
            letterSpacing: "0.15em",
            transition: "all 0.15s",
          }}
          onMouseEnter={e => { e.currentTarget.style.background = `${C.red}22`; }}
          onMouseLeave={e => { e.currentTarget.style.background = "transparent"; }}
        >
          ✕ CLOSE
        </button>
      </div>
      {/* body */}
      <div style={{ flex: 1, overflow: "auto", background: C.void }}>
        {children}
      </div>
    </div>
  );
}

// ── MOCKUP BODY for tarball apps ───────────────────────────────────────────
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
      {/* sidebar nav (faux) */}
      <div style={{
        background: "rgba(12,8,22,0.95)",
        borderRight: `1px solid ${a.color}33`,
        padding: "1rem 0.6rem",
        display: "flex",
        flexDirection: "column",
        gap: 4,
      }}>
        <div style={{ fontSize: "0.55rem", color: `${a.color}aa`, letterSpacing: "0.22em", padding: "0.3rem 0.5rem", marginBottom: 6 }}>
          MODULES
        </div>
        {a.modules?.map((m, i) => (
          <div key={m} style={{
            fontSize: "0.65rem",
            color: i === 0 ? a.color : C.dim,
            background: i === 0 ? `${a.color}1a` : "transparent",
            border: i === 0 ? `1px solid ${a.color}55` : "1px solid transparent",
            borderLeft: i === 0 ? `3px solid ${a.color}` : "3px solid transparent",
            padding: "0.4rem 0.6rem",
            borderRadius: 2,
            cursor: "default",
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

      {/* main pane */}
      <div style={{
        padding: "1.2rem 1.5rem",
        display: "flex",
        flexDirection: "column",
        gap: "1rem",
        overflow: "auto",
      }}>
        <div>
          <div style={{ fontSize: "0.55rem", color: `${a.color}aa`, letterSpacing: "0.22em", marginBottom: 4 }}>
            {a.tagline}
          </div>
          <div style={{
            fontSize: "1.6rem",
            color: a.color,
            fontWeight: 800,
            letterSpacing: "0.04em",
            textShadow: `0 0 14px ${a.color}66`,
            fontFamily: "'Caveat', cursive",
          }}>
            NYXUS {a.name}
          </div>
        </div>

        <p style={{
          margin: 0,
          fontSize: "0.78rem",
          color: C.dim,
          lineHeight: 1.7,
          maxWidth: 720,
        }}>
          {a.desc}
        </p>

        {/* sketch panel (faux content area) */}
        <div style={{
          flex: 1,
          minHeight: 140,
          border: `2px dashed ${a.color}44`,
          borderRadius: 4,
          padding: "1rem",
          background: `radial-gradient(ellipse at center, ${a.color}08 0%, transparent 70%)`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexDirection: "column",
          gap: 8,
        }}>
          <div style={{ fontSize: "2.4rem", color: a.color, textShadow: `0 0 24px ${a.color}` }}>{a.glyph}</div>
          <div style={{ fontSize: "0.65rem", color: a.color, letterSpacing: "0.2em", opacity: 0.7 }}>
            GTK4 PYTHON · NATIVE LINUX APP
          </div>
          <div style={{ fontSize: "0.55rem", color: C.dim, letterSpacing: "0.1em", maxWidth: 420, textAlign: "center" }}>
            This app runs natively on the NYXUS desktop. Install it on your Hyprland system with the curl command below — the web mockup is a reference of what's shipped.
          </div>
        </div>

        {/* install + download */}
        <div style={{
          background: "rgba(0,0,0,0.65)",
          border: `1px solid ${a.color}33`,
          borderRadius: 3,
          padding: "0.65rem 0.85rem",
          display: "flex",
          alignItems: "center",
          gap: 8,
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
            href={`${BASE}/${a.download}`}
            download={a.download}
            style={{
              flex: 1,
              textAlign: "center",
              padding: "0.5rem",
              background: `${a.color}14`,
              border: `1px solid ${a.color}66`,
              color: a.color,
              textDecoration: "none",
              fontSize: "0.65rem",
              letterSpacing: "0.15em",
              borderRadius: 2,
              fontWeight: 700,
              textShadow: `0 0 6px ${a.color}88`,
            }}
          >
            ▼ DOWNLOAD {a.download}
          </a>
          <a
            href={`${BASE}/${a.install}`}
            download={a.install}
            style={{
              flex: 1,
              textAlign: "center",
              padding: "0.5rem",
              background: "transparent",
              border: `1px solid ${a.color}33`,
              color: `${a.color}cc`,
              textDecoration: "none",
              fontSize: "0.65rem",
              letterSpacing: "0.15em",
              borderRadius: 2,
              fontWeight: 700,
            }}
          >
            ▼ INSTALL.SH
          </a>
        </div>
      </div>
    </div>
  );
}

// ── PANEL (right flyout) ───────────────────────────────────────────────────
function PanelFlyout({ open, onClose }: { open: boolean; onClose: () => void }) {
  const time = useTime();
  if (!open) return null;
  return (
    <div style={{
      position: "fixed",
      top: 30, bottom: 30, right: 32,
      width: 320,
      background: "rgba(8,6,16,0.96)",
      border: `1px solid ${C.purple}66`,
      borderTop: `2px solid ${C.purple}`,
      borderRadius: 6,
      boxShadow: `0 0 40px ${C.purple}66`,
      backdropFilter: "blur(6px)",
      padding: "1rem 1.1rem",
      display: "flex",
      flexDirection: "column",
      gap: "0.85rem",
      zIndex: 80,
      fontFamily: '"JetBrains Mono", monospace',
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <div>
          <div style={{ fontSize: "0.5rem", color: `${C.purple}aa`, letterSpacing: "0.22em" }}>NYXUS · PANEL</div>
          <div style={{ fontSize: "1rem", color: C.purple, fontFamily: "'Caveat', cursive", textShadow: `0 0 10px ${C.purple}55` }}>The Panel</div>
        </div>
        <button onClick={onClose} style={{ background: "transparent", border: `1px solid ${C.red}66`, color: C.red, padding: "2px 8px", fontSize: "0.6rem", cursor: "pointer", borderRadius: 2 }}>✕</button>
      </div>

      {/* weather card */}
      <div style={{ border: `1px solid ${C.gold}44`, borderLeft: `3px solid ${C.gold}`, borderRadius: 3, padding: "0.75rem 0.85rem", background: "rgba(255,255,0,0.04)" }}>
        <div style={{ fontSize: "0.55rem", color: `${C.gold}aa`, letterSpacing: "0.18em" }}>WEATHER</div>
        <div style={{ display: "flex", alignItems: "baseline", gap: 8, marginTop: 4 }}>
          <div style={{ fontSize: "1.6rem", color: C.gold, textShadow: `0 0 12px ${C.gold}66`, fontFamily: "'Caveat', cursive" }}>72°F</div>
          <div style={{ fontSize: "0.65rem", color: C.dim }}>Clear · Light breeze</div>
        </div>
      </div>

      {/* news ticker */}
      <div style={{ border: `1px solid ${C.cyan}44`, borderLeft: `3px solid ${C.cyan}`, borderRadius: 3, padding: "0.75rem 0.85rem", background: "rgba(34,211,238,0.04)" }}>
        <div style={{ fontSize: "0.55rem", color: `${C.cyan}aa`, letterSpacing: "0.18em" }}>NEWS</div>
        <div style={{ fontSize: "0.7rem", color: C.text, marginTop: 4, lineHeight: 1.5 }}>
          NYXUS v2.0 ships with 8 tarball apps and 4-bar Waybar
        </div>
      </div>

      {/* clock */}
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

// ── START MENU ─────────────────────────────────────────────────────────────
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
          width: "100%",
          maxWidth: 820,
          maxHeight: "100%",
          background: "rgba(8,6,16,0.97)",
          border: `1px solid ${C.cyan}66`,
          borderTop: `2px solid ${C.cyan}`,
          borderRadius: 8,
          boxShadow: `0 0 60px ${C.cyan}55`,
          padding: "1.5rem 1.75rem",
          display: "flex",
          flexDirection: "column",
          gap: "1rem",
          fontFamily: '"JetBrains Mono", monospace',
          overflow: "auto",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
          <div>
            <div style={{ fontSize: "0.55rem", color: `${C.cyan}aa`, letterSpacing: "0.22em" }}>NYXUS · START</div>
            <div style={{ fontSize: "1.25rem", color: C.cyan, fontFamily: "'Caveat', cursive", textShadow: `0 0 10px ${C.cyan}55` }}>All apps</div>
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
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: 6,
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
              <div style={{
                fontSize: "1.6rem",
                color: a.color,
                textShadow: `0 0 12px ${a.color}`,
              }}>
                {a.glyph}
              </div>
              <div style={{ fontSize: "0.7rem", fontFamily: "'Caveat', cursive", letterSpacing: "0.04em", color: a.color }}>
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

// ── NOTIFICATIONS ──────────────────────────────────────────────────────────
function Notifications({ open, onClose }: { open: boolean; onClose: () => void }) {
  if (!open) return null;
  const items = [
    { glyph: "◉", color: C.purple, title: "INTEL", body: "Investigation auto-saved (3 findings)." },
    { glyph: "⛨", color: C.green,  title: "Shield", body: "Local scan complete — 0 open ports outside policy." },
    { glyph: "◈", color: C.blue,   title: "Phantom", body: "Daemon armed. 0 threats since boot." },
    { glyph: "✦", color: C.gold,   title: "GodsApp", body: "WiFi audit module ready." },
    { glyph: "✑", color: C.purple, title: "Notepad", body: "5 notes synced to ~/.nyxus/notepad.json." },
  ];
  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed",
        top: 32, right: 38,
        zIndex: 85,
        background: "transparent",
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          width: 320,
          background: "rgba(8,6,16,0.96)",
          border: `1px solid ${C.cyan}66`,
          borderTop: `2px solid ${C.cyan}`,
          borderRadius: 6,
          padding: "0.9rem 1rem",
          display: "flex",
          flexDirection: "column",
          gap: 6,
          fontFamily: '"JetBrains Mono", monospace',
          boxShadow: `0 0 28px ${C.cyan}55`,
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 4 }}>
          <div style={{ fontSize: "0.55rem", color: `${C.cyan}aa`, letterSpacing: "0.22em" }}>NYXUS · NOTIFICATIONS</div>
          <button onClick={onClose} style={{ background: "transparent", border: `1px solid ${C.red}66`, color: C.red, padding: "1px 7px", fontSize: "0.55rem", cursor: "pointer", borderRadius: 2 }}>✕</button>
        </div>
        {items.map((n, i) => (
          <div key={i} style={{
            border: `1px solid ${n.color}33`,
            borderLeft: `3px solid ${n.color}`,
            background: `${n.color}0a`,
            padding: "0.5rem 0.65rem",
            borderRadius: 3,
            display: "flex",
            gap: 8,
            alignItems: "flex-start",
          }}>
            <span style={{ color: n.color, fontSize: "0.85rem", textShadow: `0 0 6px ${n.color}88` }}>{n.glyph}</span>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: "0.7rem", color: n.color, fontFamily: "'Caveat', cursive", letterSpacing: "0.04em" }}>{n.title}</div>
              <div style={{ fontSize: "0.6rem", color: C.dim, lineHeight: 1.5, marginTop: 1 }}>{n.body}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── SETTINGS WINDOW ────────────────────────────────────────────────────────
function SettingsWindow({ open, onClose }: { open: boolean; onClose: () => void }) {
  if (!open) return null;
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
  const sec = sections.find(s => s.id === active)!;
  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.65)",
        backdropFilter: "blur(4px)",
        zIndex: 90,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 50,
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          width: "100%",
          maxWidth: 720,
          height: "100%",
          maxHeight: 480,
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
                  width: "100%",
                  textAlign: "left",
                  background: isActive ? `${s.color}1a` : "transparent",
                  border: isActive ? `1px solid ${s.color}55` : "1px solid transparent",
                  borderLeft: isActive ? `3px solid ${s.color}` : "3px solid transparent",
                  color: isActive ? s.color : C.dim,
                  padding: "0.4rem 0.55rem",
                  borderRadius: 2,
                  cursor: "pointer",
                  fontSize: "0.7rem",
                  fontFamily: "'Caveat', cursive",
                  letterSpacing: "0.04em",
                  marginBottom: 2,
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
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
              <div style={{ fontSize: "1.4rem", color: sec.color, fontFamily: "'Caveat', cursive", textShadow: `0 0 10px ${sec.color}55` }}>{sec.label}</div>
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

// ── MAIN PAGE ──────────────────────────────────────────────────────────────
export default function Mirror() {
  const time = useTime();
  const wp = useWallpaperRotation(15000);

  const [activeWs, setActiveWs] = useState(1);
  const [openApp, setOpenApp] = useState<AppDef | null>(null);
  const [showStart, setShowStart] = useState(false);
  const [showPanel, setShowPanel] = useState(false);
  const [showNotif, setShowNotif] = useState(false);
  const [showSettings, setShowSettings] = useState(false);

  // close-all on Esc
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
      backgroundImage: `url(${wp.url})`,
      backgroundSize: "cover",
      backgroundPosition: "center",
      backgroundColor: C.void,
      transition: "background-image 1.5s ease-in-out",
      fontFamily: '"JetBrains Mono", monospace',
    }}>
      {/* Caveat font import (UI body font) */}
      <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Caveat:wght@400;700&family=JetBrains+Mono:wght@400;700&display=swap" />

      {/* dark vignette */}
      <div style={{
        position: "absolute",
        inset: 0,
        background: "radial-gradient(ellipse at center, rgba(0,0,0,0.25) 0%, rgba(0,0,0,0.5) 100%)",
        pointerEvents: "none",
      }} />

      {/* Bars */}
      <TopBar time={time} />
      <LeftBar activeWs={activeWs} onSelect={setActiveWs} />
      <RightBar />
      <BottomBar
        onStart={() => { setShowStart(s => !s); setShowPanel(false); setShowNotif(false); setShowSettings(false); }}
        onPanel={() => { setShowPanel(s => !s); setShowStart(false); setShowNotif(false); setShowSettings(false); }}
        onNotif={() => { setShowNotif(s => !s); setShowStart(false); setShowPanel(false); setShowSettings(false); }}
        onSettings={() => { setShowSettings(s => !s); setShowStart(false); setShowPanel(false); setShowNotif(false); }}
      />

      {/* Desktop icons (left side, below top bar) */}
      <div style={{
        position: "absolute",
        top: 38, left: 40,
        display: "grid",
        gridTemplateColumns: "repeat(auto-fill, 84px)",
        gap: 6,
        maxWidth: "calc(100vw - 80px)",
      }}>
        {APPS.map(a => (
          <DesktopIcon key={a.id} a={a} onOpen={() => setOpenApp(a)} />
        ))}
      </div>

      {/* Hint pill (back to portal) */}
      <a
        href="#/"
        style={{
          position: "absolute",
          bottom: 36, right: 40,
          background: "rgba(8,6,16,0.85)",
          border: `1px solid ${C.purple}66`,
          color: C.purple,
          fontSize: "0.6rem",
          padding: "4px 10px",
          textDecoration: "none",
          letterSpacing: "0.18em",
          borderRadius: 3,
          fontFamily: '"JetBrains Mono", monospace',
          textShadow: `0 0 6px ${C.purple}88`,
          zIndex: 60,
        }}
      >
        ◀ BACK TO PORTAL
      </a>

      {/* Wallpaper indicator */}
      <div style={{
        position: "absolute",
        bottom: 36, left: 40,
        background: "rgba(8,6,16,0.85)",
        border: "1px solid #1a1a1a",
        color: C.dim,
        fontSize: "0.55rem",
        padding: "3px 8px",
        letterSpacing: "0.15em",
        borderRadius: 3,
        fontFamily: '"JetBrains Mono", monospace',
        zIndex: 60,
      }}>
        WALLPAPER {String(wp.idx + 1).padStart(2, "0")}/15
      </div>

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
              style={{
                width: "100%",
                height: "100%",
                border: "none",
                background: C.void,
              }}
            />
          ) : (
            <MockupBody a={openApp} />
          )}
        </Window>
      )}
    </div>
  );
}
