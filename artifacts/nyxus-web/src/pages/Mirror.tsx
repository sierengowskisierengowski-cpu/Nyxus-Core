// ============================================
// NYXUS — nyx-2026.05.02-x86_64.iso
// Copyright © 2026 Joseph Sierengowski
// All Rights Reserved
// NYX-J5W-2026-SIERENGOWSKI-LOCKED
// ============================================
//
// /mirror — exact mirror image of the NYXUS theme + every app
// shipped via the download portal. Single-page visual encyclopedia
// of everything built so far. Same aesthetic as the home page.

import { useState, useEffect } from "react";

const BASE = "/api/download/nyxus";

const PURPLE = "#c084fc";
const PINK   = "#f472b6";
const GOLD   = "#fbbf24";
const GREEN  = "#34d399";
const ORANGE = "#fb923c";
const RED    = "#f87171";
const BLUE   = "#818cf8";

// ─── 8 TARBALL APPS ────────────────────────────────────────────────────────
const APPS = [
  {
    id: "nyxus-intel.tgz",
    name: "NYXUS INTEL",
    glyph: "◉",
    color: PURPLE,
    tag: "OSINT WORKSTATION",
    desc: "Open source intelligence investigation suite. Email/phone/IP/domain/crypto/photo lookups via real APIs (HIBP, Shodan, VT, AbuseIPDB, IPinfo, blockchain.info, Etherscan, FAA, FCC, SEC, FEC, USPTO, OpenSanctions). Encrypted case storage, PDF reports, passwordless device-key auth, AES-256-GCM at rest.",
    pkg: "/opt/nyxus-intel/",
    bin: "nyxus-intel",
    files: 22,
    install: "nyxus_intel_install.sh",
  },
  {
    id: "nyxus-phantom.tgz",
    name: "NYXUS PHANTOM",
    glyph: "◈",
    color: BLUE,
    tag: "STEALTH SECURITY DAEMON",
    desc: "Always-on threat monitoring + automated response daemon. Forensics module captures evidence, threats engine fingerprints attackers, response engine isolates compromised processes. Runs as systemd service (nyxus-phantom.service).",
    pkg: "/opt/nyxus-phantom/",
    bin: "systemctl start nyxus-phantom",
    files: 5,
    install: "nyxus-phantom.tgz",
  },
  {
    id: "nyxus-shield.tgz",
    name: "NYXUS SHIELD",
    glyph: "⛨",
    color: GREEN,
    tag: "NETWORK SECURITY SCANNER",
    desc: "Active vulnerability + network exposure scanner. Local scan (open ports, services), network scan (subnet sweep, fingerprinting), persistent SQLite DB of findings. NYXUS-themed GTK UI.",
    pkg: "/opt/nyxus-shield/",
    bin: "nyxus-shield",
    files: 5,
    install: "nyxus_security_install.sh",
  },
  {
    id: "nyxus-godsapp.tgz",
    name: "NYXUS GODSAPP",
    glyph: "✦",
    color: GOLD,
    tag: "9-MODULE SUPER TOOL",
    desc: "All-in-one offensive/defensive workstation. 9 modules: m01 network mapper, m02 port scanner, m03 packet capture, m04 wifi audit, m05 vuln scanner, m06 traffic analysis, m07 attack surface, m08 OSINT pivot, m09 password tools. udev rules for live device events.",
    pkg: "/opt/nyxus-godsapp/",
    bin: "nyxus-godsapp",
    files: 14,
    install: "nyxus_godsapp_install.sh",
  },
  {
    id: "nyxus-sage.tgz",
    name: "NYXUS SAGE",
    glyph: "✧",
    color: PINK,
    tag: "RULES + KNOWLEDGE ENGINE",
    desc: "Tabbed Adwaita UI for system rules, audit trails, and knowledge base. CLI companion for headless audits. Pluggable rules engine — add your own checks as Python modules.",
    pkg: "/opt/nyxus-sage/",
    bin: "nyxus-sage",
    files: 9,
    install: "nyxus_sage_install.sh",
  },
  {
    id: "nyxus-panel.tgz",
    name: "NYXUS PANEL",
    glyph: "▦",
    color: PURPLE,
    tag: "TOPBAR + SETTINGS FLYOUT",
    desc: "The Panel — right-side flyout with weather, news ticker, system widgets, and the unified Settings window (Appearance / Profile / Notifications / News Sources / Filters / Browser / Cache / About). Sidebar-nav layout with cross-fade transitions.",
    pkg: "/opt/nyxus-panel/",
    bin: "nyxus-panel  ·  nyxus-settings",
    files: 30,
    install: "nyxus_panel_install.sh",
  },
  {
    id: "nyxus-start.tgz",
    name: "NYXUS START",
    glyph: "◐",
    color: PURPLE,
    tag: "START MENU + BOTTOM BAR",
    desc: "The Start menu (Apps page + Store page, page-switched layout) and the four custom Waybar bottom-bar buttons: Start, The Panel, Notifications, Settings. Idempotent installer that won't double-add to Waybar.",
    pkg: "/opt/nyxus-start/",
    bin: "nyxus-start",
    files: 40,
    install: "nyxus_start_install.sh",
  },
  {
    id: "nyxus-studio.tgz",
    name: "NYXUS CREATIVE STUDIO",
    glyph: "✎",
    color: ORANGE,
    tag: "9-MODULE CREATIVE SUITE",
    desc: "Multi-module creative workstation: m01 paint, m02 vector, m03 3d, m04 video, m05 animate, m06 photo, m07 layout, m08 typography, m09 voice. Cross-module wired with engine/ui/audio_engine/video_engine/three_d_engine/document references.",
    pkg: "/opt/nyxus-studio/",
    bin: "nyxus-studio",
    files: 18,
    install: "nyxus_studio_install.sh",
  },
];

// ─── DESKTOP UTILITY APPS (single-file Python) ─────────────────────────────
const DESKTOP_APPS = [
  { id: "nyxus_notepad.py",     name: "NYXUS Notepad",   color: PURPLE, glyph: "✑",  desc: "GTK4 hand-drawn notepad. Caveat font, dashed sketch borders, NYXUS palette. Persists to ~/.nyxus/notepad.json." },
  { id: "nyxus_stickies.py",    name: "NYXUS Stickies",  color: GOLD,   glyph: "▢",  desc: "Sticky notes widget. Pinned, floating, alway-on-top. Cairo-drawn corners, Caveat font, JSON persistence." },
  { id: "nyxus_weather.py",     name: "NYXUS Weather",   color: BLUE,   glyph: "☼",  desc: "Live weather widget. Pinned to top-left of workspace. Caveat-rendered conditions, dim glow accents." },
  { id: "nyxus_sysmon_gtk.py",  name: "NYXUS SysMon",    color: GREEN,  glyph: "◉",  desc: "Full-screen system monitor (workspace 6). CPU/MEM/NET/DISK live graphs in Cairo, JetBrains Mono Nerd glyphs." },
  { id: "nyxus_terminal.py",    name: "NYXUS Terminal",  color: PURPLE, glyph: "▶",  desc: "Themed terminal launcher with copy/paste keybinds and NYXUS color scheme baked in." },
  { id: "nyxus_settings.py",    name: "NYXUS Settings",  color: PINK,   glyph: "⚙",  desc: "Standalone Settings window — same sidebar-nav layout as the one inside Panel. Themed cog launcher." },
  { id: "nyxus_control.py",     name: "NYXUS Control",   color: ORANGE, glyph: "◧",  desc: "Quick toggles widget — wifi, bluetooth, brightness, volume, night mode. Hand-drawn pill switches." },
  { id: "nyxus_quicksettings.py", name: "NYXUS QuickSettings", color: GOLD, glyph: "◍", desc: "Inline settings popover bound to the topbar — small, fast, no full settings window needed." },
];

// ─── BOOT / TTY COMPONENTS ─────────────────────────────────────────────────
const BOOT = [
  { id: "nyxus_motd.py",    name: "MOTD",     color: PURPLE, glyph: "▤" },
  { id: "nyxus_error.py",   name: "ERROR",    color: RED,    glyph: "▰" },
  { id: "nyxus_preboot.py", name: "PRE-BOOT", color: GREEN,  glyph: "▱" },
  { id: "nyxus_splash.py",  name: "SPLASH",   color: ORANGE, glyph: "▥" },
];

// ─── CONFIG FILES ──────────────────────────────────────────────────────────
const CONFIGS = [
  { id: "hyprland.conf",         label: "Hyprland window manager",          color: PURPLE },
  { id: "hyprlock.conf",         label: "Hyprlock screen locker",           color: PURPLE },
  { id: "hypridle.conf",         label: "Hypridle idle daemon",             color: PURPLE },
  { id: "mako-config",           label: "Mako notification daemon",         color: GOLD   },
  { id: "alacritty.toml",        label: "Alacritty terminal",               color: GREEN  },
  { id: "rofi-config.rasi",      label: "Rofi launcher (default)",          color: PINK   },
  { id: "rofi-nyxus.rasi",       label: "Rofi launcher (NYXUS theme)",      color: PINK   },
  { id: "rofi-startmenu.rasi",   label: "Rofi as a start menu",             color: PINK   },
  { id: "waybar-config.json",    label: "Waybar layout (top + bottom)",     color: BLUE   },
  { id: "waybar-style.css",      label: "Waybar styling",                   color: BLUE   },
  { id: "waybar-stats.sh",       label: "Waybar stats helper",              color: BLUE   },
  { id: "waybar-ticker.sh",      label: "Waybar news/info ticker",          color: BLUE   },
  { id: "wlogout-style.css",     label: "Wlogout power menu styling",       color: ORANGE },
  { id: "wallpaper-rotate.sh",   label: "Rotates the 15 wallpapers",        color: GOLD   },
];

// ─── WALLPAPER FILENAMES ───────────────────────────────────────────────────
const WALLPAPERS = Array.from({ length: 15 }, (_, i) =>
  `nyxus-bg-${String(i + 1).padStart(2, "0")}.png`
);

// ─── COLOR PALETTE ─────────────────────────────────────────────────────────
const PALETTE = [
  { name: "Phantom Purple",   hex: "#c084fc", role: "primary brand"      },
  { name: "Veil Pink",        hex: "#f472b6", role: "accent · highlight" },
  { name: "Oracle Gold",      hex: "#fbbf24", role: "highlight · warn"   },
  { name: "Ghost Green",      hex: "#34d399", role: "success · live"     },
  { name: "Spark Orange",     hex: "#fb923c", role: "info · power"       },
  { name: "Blood Red",        hex: "#f87171", role: "danger · critical"  },
  { name: "Spectral Blue",    hex: "#818cf8", role: "info · daemon"      },
  { name: "Void Black",       hex: "#080808", role: "base background"    },
  { name: "Smoke",            hex: "#1a1a1a", role: "panel background"   },
];

// ─── COMPONENTS ────────────────────────────────────────────────────────────
function SectionHeader({ kicker, title }: { kicker: string; title?: string }) {
  return (
    <div style={{ marginTop: "3.5rem", marginBottom: "1.5rem" }}>
      <div style={{ fontSize: "0.65rem", color: "#444", letterSpacing: "0.2em", marginBottom: "0.4rem" }}>
        {kicker}
      </div>
      {title && (
        <h2 style={{ margin: 0, fontSize: "1.4rem", color: "#ddd", letterSpacing: "0.05em", fontWeight: 700 }}>
          {title}
        </h2>
      )}
    </div>
  );
}

function CurlBox({ cmd }: { cmd: string }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(cmd);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };
  return (
    <div style={{
      background: "rgba(7,7,7,0.85)",
      border: "1px solid #1a1a1a",
      borderRadius: 3,
      padding: "0.55rem 0.75rem",
      display: "flex",
      alignItems: "center",
      gap: "0.5rem",
      fontFamily: "monospace",
    }}>
      <code style={{ flex: 1, fontSize: "0.65rem", color: "#666", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
        <span style={{ color: "#333" }}>$</span> {cmd}
      </code>
      <button
        onClick={copy}
        style={{
          background: copied ? `${PURPLE}33` : "transparent",
          border: `1px solid ${copied ? PURPLE : "#333"}`,
          color: copied ? PURPLE : "#555",
          padding: "2px 8px",
          borderRadius: 2,
          fontSize: "0.6rem",
          cursor: "pointer",
          letterSpacing: "0.05em",
          transition: "all 0.2s",
        }}
      >
        {copied ? "COPIED" : "COPY"}
      </button>
    </div>
  );
}

function AppCard({ a }: { a: typeof APPS[0] }) {
  const cmd = `curl -fsSL "${window.location.origin}${BASE}/${a.install}" | bash`;
  return (
    <div style={{
      border: `1px solid ${a.color}33`,
      borderTop: `2px solid ${a.color}`,
      borderRadius: 4,
      padding: "1.25rem 1.25rem 1rem",
      background: "rgba(8,8,8,0.78)",
      boxShadow: `0 0 28px ${a.color}14, inset 0 0 60px rgba(0,0,0,0.4)`,
      display: "flex",
      flexDirection: "column",
      gap: "0.85rem",
    }}>
      <div style={{ display: "flex", alignItems: "flex-start", gap: "0.85rem" }}>
        <div style={{
          fontSize: "1.6rem",
          color: a.color,
          textShadow: `0 0 14px ${a.color}88`,
          lineHeight: 1,
          flex: "0 0 auto",
        }}>
          {a.glyph}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: "0.95rem", fontWeight: 800, color: a.color, letterSpacing: "0.05em", textShadow: `0 0 8px ${a.color}55` }}>
            {a.name}
          </div>
          <div style={{ fontSize: "0.55rem", color: `${a.color}99`, letterSpacing: "0.18em", marginTop: 2 }}>
            {a.tag}
          </div>
        </div>
        <div style={{ fontSize: "0.55rem", color: "#333", letterSpacing: "0.1em", textAlign: "right" }}>
          {a.files} FILES
        </div>
      </div>

      <p style={{ margin: 0, fontSize: "0.72rem", color: "#888", lineHeight: 1.7 }}>
        {a.desc}
      </p>

      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", fontSize: "0.6rem", color: "#555" }}>
        <span style={{ border: "1px solid #222", padding: "2px 8px", borderRadius: 2 }}>
          <span style={{ color: "#333" }}>install →</span> <span style={{ color: a.color }}>{a.pkg}</span>
        </span>
        <span style={{ border: "1px solid #222", padding: "2px 8px", borderRadius: 2 }}>
          <span style={{ color: "#333" }}>launch →</span> <span style={{ color: a.color }}>{a.bin}</span>
        </span>
      </div>

      <CurlBox cmd={cmd.replace(window.location.origin, "$BASE")} />

      <div style={{ display: "flex", gap: "0.5rem" }}>
        <a
          href={`${BASE}/${a.id}`}
          download={a.id}
          style={{
            flex: 1,
            textAlign: "center",
            padding: "0.45rem",
            background: `${a.color}14`,
            border: `1px solid ${a.color}55`,
            color: a.color,
            textDecoration: "none",
            fontSize: "0.65rem",
            letterSpacing: "0.15em",
            borderRadius: 2,
            fontWeight: 700,
            textShadow: `0 0 6px ${a.color}77`,
          }}
        >
          ▼ TARBALL
        </a>
        <a
          href={`${BASE}/${a.install}`}
          download={a.install}
          style={{
            flex: 1,
            textAlign: "center",
            padding: "0.45rem",
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
  );
}

function MiniRow({ id, name, color, glyph, desc }: typeof DESKTOP_APPS[0]) {
  return (
    <a
      href={`${BASE}/${id}`}
      download={id}
      style={{
        display: "flex",
        alignItems: "center",
        gap: "0.85rem",
        padding: "0.7rem 0.9rem",
        border: "1px solid #1a1a1a",
        borderLeft: `3px solid ${color}`,
        background: "rgba(8,8,8,0.7)",
        borderRadius: 3,
        textDecoration: "none",
        transition: "all 0.2s",
      }}
      onMouseEnter={e => {
        e.currentTarget.style.background = "rgba(20,15,30,0.85)";
        e.currentTarget.style.borderColor = `${color}55`;
        e.currentTarget.style.borderLeftColor = color;
      }}
      onMouseLeave={e => {
        e.currentTarget.style.background = "rgba(8,8,8,0.7)";
        e.currentTarget.style.borderColor = "#1a1a1a";
        e.currentTarget.style.borderLeftColor = color;
      }}
    >
      <div style={{ fontSize: "1.15rem", color, textShadow: `0 0 10px ${color}77`, lineHeight: 1, flex: "0 0 auto" }}>
        {glyph}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: "0.78rem", color, fontWeight: 700, letterSpacing: "0.04em" }}>{name}</div>
        <div style={{ fontSize: "0.65rem", color: "#666", marginTop: 2, lineHeight: 1.5 }}>{desc}</div>
      </div>
      <div style={{ fontSize: "0.55rem", color: "#333", letterSpacing: "0.12em" }}>▼ {id}</div>
    </a>
  );
}

function ConfigPill({ id, label, color }: typeof CONFIGS[0]) {
  return (
    <a
      href={`${BASE}/${id}`}
      download={id}
      style={{
        display: "flex",
        alignItems: "center",
        gap: "0.6rem",
        padding: "0.55rem 0.85rem",
        border: "1px solid #1a1a1a",
        background: "rgba(8,8,8,0.65)",
        borderRadius: 3,
        textDecoration: "none",
        transition: "all 0.2s",
      }}
      onMouseEnter={e => {
        e.currentTarget.style.borderColor = `${color}66`;
        e.currentTarget.style.background = `${color}11`;
      }}
      onMouseLeave={e => {
        e.currentTarget.style.borderColor = "#1a1a1a";
        e.currentTarget.style.background = "rgba(8,8,8,0.65)";
      }}
    >
      <span style={{ color, fontSize: "0.7rem" }}>◈</span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: "0.7rem", color: "#bbb", fontFamily: "monospace" }}>{id}</div>
        <div style={{ fontSize: "0.6rem", color: "#555", marginTop: 1 }}>{label}</div>
      </div>
      <span style={{ fontSize: "0.6rem", color: "#333" }}>▼</span>
    </a>
  );
}

// ─── MAIN MIRROR PAGE ──────────────────────────────────────────────────────
export default function Mirror() {
  const [time, setTime] = useState(new Date().toISOString().replace("T", " ").slice(0, 19));
  useEffect(() => {
    const t = setInterval(() => setTime(new Date().toISOString().replace("T", " ").slice(0, 19)), 1000);
    return () => clearInterval(t);
  }, []);

  const BG_URL = `${import.meta.env.BASE_URL}nyxus-bg.png`;

  return (
    <div style={{
      minHeight: "100vh",
      backgroundImage: `url(${BG_URL})`,
      backgroundSize: "cover",
      backgroundPosition: "center top",
      backgroundAttachment: "fixed",
      position: "relative",
    }}>
      {/* Vignette */}
      <div style={{
        position: "fixed",
        inset: 0,
        background: "radial-gradient(ellipse at 50% 0%, rgba(0,0,0,0.6) 0%, rgba(0,0,0,0.86) 60%, rgba(0,0,0,0.96) 100%)",
        pointerEvents: "none",
        zIndex: 0,
      }} />

      <div style={{ position: "relative", zIndex: 1 }}>

        {/* ─── HEADER ─── */}
        <header style={{
          padding: "2rem 2rem 1.25rem",
          borderBottom: "1px solid rgba(192,132,252,0.08)",
          background: "rgba(0,0,0,0.65)",
          backdropFilter: "blur(2px)",
        }}>
          <div style={{ maxWidth: 1100, margin: "0 auto" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", flexWrap: "wrap", gap: "0.5rem" }}>
              <div>
                <div style={{ fontSize: "0.6rem", color: "#444", letterSpacing: "0.22em", marginBottom: "0.3rem" }}>
                  NYX-J5W-2026-SIERENGOWSKI-LOCKED  ·  REFERENCE MIRROR
                </div>
                <h1 style={{ margin: 0, fontSize: "clamp(1.6rem, 4vw, 2.6rem)", fontWeight: 900, letterSpacing: "0.12em" }}>
                  <span style={{ color: PURPLE, textShadow: `0 0 24px ${PURPLE}99` }}>NYX</span>
                  <span style={{ color: "#444" }}>·</span>
                  <span style={{ color: PURPLE, textShadow: `0 0 24px ${PURPLE}99` }}>NYXUS</span>
                  <span style={{ color: "#666", fontSize: "0.7em", marginLeft: "0.6em", letterSpacing: "0.18em" }}>// MIRROR</span>
                </h1>
                <div style={{ fontSize: "0.6rem", color: "#444", letterSpacing: "0.25em", marginTop: "0.25rem" }}>
                  EVERY THEME · EVERY APP · EVERY CONFIG
                </div>
              </div>
              <div style={{ textAlign: "right" }}>
                <a href="#/" style={{ fontSize: "0.6rem", color: PURPLE, textDecoration: "none", border: `1px solid ${PURPLE}55`, padding: "4px 10px", borderRadius: 2, letterSpacing: "0.15em" }}>
                  ◀ BACK TO PORTAL
                </a>
                <div style={{ fontSize: "0.55rem", color: "#2a2a2a", marginTop: "0.5rem", fontFamily: "monospace" }}>{time} UTC</div>
                <div style={{ fontSize: "0.55rem", color: "#1e1e1e" }}>NYX-2026.05.02-x86_64.iso</div>
              </div>
            </div>
          </div>
        </header>

        <main style={{ maxWidth: 1100, margin: "0 auto", padding: "1.5rem 2rem 4rem", width: "100%" }}>

          {/* ─── INTRO: TWO NAMES ─── */}
          <div style={{
            marginTop: "1.5rem",
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
            gap: "1rem",
          }}>
            <div style={{ border: `1px solid ${PURPLE}33`, borderTop: `2px solid ${PURPLE}`, padding: "1.2rem", borderRadius: 3, background: "rgba(8,8,8,0.75)" }}>
              <div style={{ fontSize: "0.55rem", color: `${PURPLE}99`, letterSpacing: "0.25em", marginBottom: "0.4rem" }}>THE FILE</div>
              <div style={{ fontSize: "1.1rem", fontWeight: 800, color: PURPLE, letterSpacing: "0.08em", textShadow: `0 0 12px ${PURPLE}55` }}>NYX</div>
              <div style={{ fontSize: "0.7rem", color: "#888", marginTop: "0.5rem", lineHeight: 1.6 }}>
                The .iso file you burn to USB. Filename: <code style={{ color: PURPLE }}>nyx-2026.05.02-x86_64.iso</code>. The only place "nyx-" ever appears.
              </div>
            </div>
            <div style={{ border: `1px solid ${PURPLE}33`, borderTop: `2px solid ${PURPLE}`, padding: "1.2rem", borderRadius: 3, background: "rgba(8,8,8,0.75)" }}>
              <div style={{ fontSize: "0.55rem", color: `${PURPLE}99`, letterSpacing: "0.25em", marginBottom: "0.4rem" }}>THE OS</div>
              <div style={{ fontSize: "1.1rem", fontWeight: 800, color: PURPLE, letterSpacing: "0.08em", textShadow: `0 0 12px ${PURPLE}55` }}>NYXUS</div>
              <div style={{ fontSize: "0.7rem", color: "#888", marginTop: "0.5rem", lineHeight: 1.6 }}>
                The operating system that boots from NYX. Every app, doc, menu, and About dialog says NYXUS.
              </div>
            </div>
            <div style={{ border: `1px solid ${GOLD}33`, borderTop: `2px solid ${GOLD}`, padding: "1.2rem", borderRadius: 3, background: "rgba(8,8,8,0.75)" }}>
              <div style={{ fontSize: "0.55rem", color: `${GOLD}99`, letterSpacing: "0.25em", marginBottom: "0.4rem" }}>OWNER</div>
              <div style={{ fontSize: "1.1rem", fontWeight: 800, color: GOLD, letterSpacing: "0.04em", textShadow: `0 0 12px ${GOLD}55` }}>JOSEPH SIERENGOWSKI</div>
              <div style={{ fontSize: "0.7rem", color: "#888", marginTop: "0.5rem", lineHeight: 1.6 }}>
                © 2026 — All Rights Reserved. Custom License v1.0. <code style={{ color: GOLD }}>NYX-J5W-2026-SIERENGOWSKI-LOCKED</code>.
              </div>
            </div>
          </div>

          {/* ─── THEME SYSTEM ─── */}
          <SectionHeader kicker="// THEME SYSTEM · COLORS · FONTS · RULES" title="The NYXUS look" />
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: "0.6rem" }}>
            {PALETTE.map(p => (
              <div key={p.hex} style={{
                border: "1px solid #181818",
                borderRadius: 3,
                background: "rgba(8,8,8,0.7)",
                padding: "0.7rem",
                display: "flex",
                alignItems: "center",
                gap: "0.7rem",
              }}>
                <div style={{
                  width: 36, height: 36,
                  borderRadius: 3,
                  background: p.hex,
                  border: "1px solid rgba(255,255,255,0.1)",
                  boxShadow: `0 0 14px ${p.hex}66`,
                  flex: "0 0 auto",
                }} />
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div style={{ fontSize: "0.7rem", color: p.hex, fontWeight: 700 }}>{p.name}</div>
                  <div style={{ fontSize: "0.6rem", color: "#666", fontFamily: "monospace" }}>{p.hex}</div>
                  <div style={{ fontSize: "0.55rem", color: "#444" }}>{p.role}</div>
                </div>
              </div>
            ))}
          </div>

          <div style={{ marginTop: "1rem", display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "0.75rem" }}>
            <div style={{ border: "1px solid #181818", borderLeft: `3px solid ${PURPLE}`, padding: "0.85rem 1rem", borderRadius: 3, background: "rgba(8,8,8,0.7)" }}>
              <div style={{ fontSize: "0.55rem", color: "#444", letterSpacing: "0.18em" }}>FONT · UI BODY</div>
              <div style={{ fontSize: "1rem", color: PURPLE, fontWeight: 700 }}>Caveat</div>
              <div style={{ fontSize: "0.6rem", color: "#666", marginTop: 2 }}>Hand-drawn cursive. Used for every app label, button, header.</div>
            </div>
            <div style={{ border: "1px solid #181818", borderLeft: `3px solid ${GREEN}`, padding: "0.85rem 1rem", borderRadius: 3, background: "rgba(8,8,8,0.7)" }}>
              <div style={{ fontSize: "0.55rem", color: "#444", letterSpacing: "0.18em" }}>FONT · GLYPHS + CODE</div>
              <div style={{ fontSize: "1rem", color: GREEN, fontFamily: "monospace", fontWeight: 700 }}>JetBrains Mono Nerd</div>
              <div style={{ fontSize: "0.6rem", color: "#666", marginTop: 2 }}>For glyphs, code, terminal, monospace UI. Symbols Nerd Font fallback.</div>
            </div>
            <div style={{ border: "1px solid #181818", borderLeft: `3px solid ${GOLD}`, padding: "0.85rem 1rem", borderRadius: 3, background: "rgba(8,8,8,0.7)" }}>
              <div style={{ fontSize: "0.55rem", color: "#444", letterSpacing: "0.18em" }}>RULES</div>
              <div style={{ fontSize: "0.7rem", color: "#aaa", lineHeight: 1.7 }}>
                <div>◈ <span style={{ color: GOLD }}>NO emojis</span> — Font Awesome / Nerd Font glyphs only</div>
                <div>◈ Dashed / sketched borders, dark base #080808</div>
                <div>◈ All apps native GTK4 Python — no Electron, no WebView</div>
                <div>◈ Cairo for custom drawing, GLib timers</div>
              </div>
            </div>
          </div>

          {/* ─── 8 TARBALL APPS ─── */}
          <SectionHeader kicker="// APP SUITE · 8 INSTALLABLE TARBALLS" title="The NYXUS apps" />
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))", gap: "1rem" }}>
            {APPS.map(a => <AppCard key={a.id} a={a} />)}
          </div>

          {/* ─── DESKTOP UTILITIES ─── */}
          <SectionHeader kicker="// DESKTOP UTILITIES · SINGLE-FILE GTK4 PYTHON" title="Widgets + utility apps" />
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(380px, 1fr))", gap: "0.65rem" }}>
            {DESKTOP_APPS.map(d => <MiniRow key={d.id} {...d} />)}
          </div>

          {/* ─── BOOT COMPONENTS ─── */}
          <SectionHeader kicker="// BOOT / TTY COMPONENTS · LIVE FROM PORTAL HOME" title="Terminal visuals" />
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "0.6rem" }}>
            {BOOT.map(b => (
              <a
                key={b.id}
                href={`${BASE}/${b.id}`}
                download={b.id}
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: "0.4rem",
                  padding: "1rem",
                  border: `1px solid ${b.color}33`,
                  borderTop: `2px solid ${b.color}`,
                  borderRadius: 3,
                  background: "rgba(8,8,8,0.78)",
                  textDecoration: "none",
                  textAlign: "center",
                }}
              >
                <div style={{ fontSize: "1.4rem", color: b.color, textShadow: `0 0 12px ${b.color}99` }}>{b.glyph}</div>
                <div style={{ fontSize: "0.7rem", color: b.color, fontWeight: 700, letterSpacing: "0.15em" }}>{b.name}</div>
                <div style={{ fontSize: "0.55rem", color: "#555", fontFamily: "monospace" }}>{b.id}</div>
              </a>
            ))}
          </div>
          <div style={{ marginTop: "0.8rem", textAlign: "center", fontSize: "0.6rem", color: "#444" }}>
            <a href="#/" style={{ color: PURPLE, textDecoration: "none", letterSpacing: "0.12em" }}>
              See full live previews on the portal home →
            </a>
          </div>

          {/* ─── CONFIGS ─── */}
          <SectionHeader kicker="// HYPRLAND + WAYBAR + ROFI + MAKO + ALACRITTY" title="Config files" />
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "0.5rem" }}>
            {CONFIGS.map(c => <ConfigPill key={c.id} {...c} />)}
          </div>

          <div style={{ marginTop: "0.85rem", display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "0.5rem" }}>
            {[
              { id: "nyxus-ui-configs.tar.gz",   label: "Bundle of every UI config" },
              { id: "nyxus-wlogout.tar.gz",      label: "Wlogout power menu (full theme)" },
              { id: "nyxus-sddm-theme.tar.gz",   label: "SDDM login theme (QML)" },
            ].map(t => (
              <a key={t.id} href={`${BASE}/${t.id}`} download={t.id} style={{
                display: "block",
                padding: "0.7rem 0.9rem",
                border: `1px solid ${PURPLE}44`,
                borderTop: `2px solid ${PURPLE}`,
                borderRadius: 3,
                background: "rgba(8,8,8,0.78)",
                textDecoration: "none",
              }}>
                <div style={{ fontSize: "0.7rem", color: PURPLE, fontWeight: 700, letterSpacing: "0.05em" }}>▼ {t.id}</div>
                <div style={{ fontSize: "0.6rem", color: "#666", marginTop: 2 }}>{t.label}</div>
              </a>
            ))}
          </div>

          {/* ─── WALLPAPERS ─── */}
          <SectionHeader kicker="// WALLPAPER SET · 15 NATIVE NYXUS BACKGROUNDS" title="Wallpapers" />
          <div style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))",
            gap: "0.45rem",
          }}>
            {WALLPAPERS.map((w, i) => (
              <a
                key={w}
                href={`${BASE}/${w}`}
                download={w}
                style={{
                  position: "relative",
                  display: "block",
                  aspectRatio: "16 / 10",
                  border: "1px solid #1a1a1a",
                  borderRadius: 3,
                  overflow: "hidden",
                  background: "#000",
                  textDecoration: "none",
                }}
              >
                <img
                  src={`${BASE}/${w}`}
                  alt={w}
                  loading="lazy"
                  style={{ width: "100%", height: "100%", objectFit: "cover", opacity: 0.92 }}
                />
                <div style={{
                  position: "absolute",
                  inset: 0,
                  background: "linear-gradient(to top, rgba(0,0,0,0.85) 0%, transparent 50%)",
                  display: "flex",
                  alignItems: "flex-end",
                  padding: "0.4rem 0.5rem",
                }}>
                  <div style={{ fontSize: "0.55rem", color: PURPLE, fontFamily: "monospace", letterSpacing: "0.05em" }}>
                    {String(i + 1).padStart(2, "0")} · {w}
                  </div>
                </div>
              </a>
            ))}
          </div>

          {/* ─── SECURITY STACK ─── */}
          <SectionHeader kicker="// OWNERSHIP · WATERMARKING · TAMPER DETECTION" title="Security + legal stack" />
          <div style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
            gap: "0.75rem",
          }}>
            {[
              { glyph: "⛬", title: "Copyright headers", color: PURPLE, body: "6-line banner on every Python, Bash, and CSS file in every shipped tarball. Lock code + ISO filename + © 2026 Joseph Sierengowski." },
              { glyph: "⌬", title: "Fingerprint", color: GOLD, body: "_fingerprint._check() called from main() on every launch. Silent, non-blocking. Lives in every NYXUS Python app." },
              { glyph: "✪", title: "Tamper manifest", color: GREEN, body: "_tamper.py SHA-256s every shipped .py (including itself). Mismatch logs to ~/.config/nyxus/tamper.log. Always continues." },
              { glyph: "✦", title: "Legal disclaimer", color: PINK, body: "_legal.py first-launch modal. Acceptance keyed by app name in ~/.config/nyxus/accepted.json." },
              { glyph: "◉", title: "About dialog", color: BLUE, body: "_about.py NYXUS-themed about window. Wired to topbar info button. Shows version, ISO, owner, lock code." },
              { glyph: "◈", title: "AES-256-GCM at rest", color: ORANGE, body: "INTEL case storage encrypted via per-device key (auto-generated on first launch, mode 0600 in ~/.config/nyxus-intel/device.key)." },
            ].map((s, i) => (
              <div key={i} style={{
                border: `1px solid ${s.color}33`,
                borderTop: `2px solid ${s.color}`,
                background: "rgba(8,8,8,0.75)",
                borderRadius: 3,
                padding: "0.85rem 1rem",
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.4rem" }}>
                  <span style={{ fontSize: "1rem", color: s.color, textShadow: `0 0 10px ${s.color}88` }}>{s.glyph}</span>
                  <span style={{ fontSize: "0.75rem", color: s.color, fontWeight: 700, letterSpacing: "0.05em" }}>{s.title}</span>
                </div>
                <div style={{ fontSize: "0.65rem", color: "#888", lineHeight: 1.7 }}>{s.body}</div>
              </div>
            ))}
          </div>

          {/* ─── ISO BUILDER ─── */}
          <SectionHeader kicker="// ISO BUILDER · BAKES NYX-2026.05.02-X86_64.ISO" title="Bake it" />
          <div style={{
            border: `1px solid ${GOLD}44`,
            borderTop: `2px solid ${GOLD}`,
            borderRadius: 4,
            padding: "1.25rem 1.5rem",
            background: "rgba(8,8,8,0.78)",
            boxShadow: `0 0 32px ${GOLD}14`,
          }}>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "1rem", alignItems: "flex-start" }}>
              <div style={{ flex: "1 1 280px" }}>
                <div style={{ fontSize: "0.55rem", color: `${GOLD}99`, letterSpacing: "0.2em", marginBottom: "0.4rem" }}>iso-builder/</div>
                <div style={{ fontSize: "1.1rem", color: GOLD, fontWeight: 800, letterSpacing: "0.05em", textShadow: `0 0 12px ${GOLD}66` }}>build-iso.sh</div>
                <p style={{ fontSize: "0.72rem", color: "#888", lineHeight: 1.7, marginTop: "0.5rem" }}>
                  One-command archiso wrapper. Runs on your MSI (Arch + root + archiso). Pulls the latest INTEL tarball, seeds the tamper manifest, mirrors the OS docs into <code style={{ color: GOLD }}>/etc/nyxus/</code>, runs <code style={{ color: GOLD }}>mkarchiso</code>, renames the output to <code style={{ color: PURPLE }}>nyx-2026.05.02-x86_64.iso</code>.
                </p>
              </div>
              <div style={{ flex: "1 1 240px" }}>
                <div style={{ fontSize: "0.55rem", color: "#444", letterSpacing: "0.2em", marginBottom: 6 }}>// RUN ON ARCH</div>
                <pre style={{ margin: 0, fontSize: "0.7rem", color: "#888", background: "rgba(0,0,0,0.6)", padding: "0.8rem 1rem", borderRadius: 3, border: "1px solid #1a1a1a", lineHeight: 1.8, overflow: "auto" }}>
{`git pull
cd iso-builder
sudo ./build-iso.sh

# output:
out/nyx-2026.05.02-x86_64.iso`}
                </pre>
              </div>
            </div>
            <div style={{ marginTop: "1rem", display: "flex", flexWrap: "wrap", gap: "0.4rem", fontSize: "0.6rem", color: "#555" }}>
              {["profiledef.sh", "packages.x86_64", "pacman.conf", "airootfs/etc/os-release", "airootfs/etc/motd", "airootfs/etc/skel/.config/hypr/", "syslinux/syslinux.cfg", "efiboot/loader/", "grub/grub.cfg"].map(f => (
                <span key={f} style={{ border: "1px solid #1a1a1a", padding: "2px 8px", borderRadius: 2, color: GOLD }}>{f}</span>
              ))}
            </div>
          </div>

          {/* ─── FOOTER ─── */}
          <div style={{
            marginTop: "4rem",
            paddingTop: "1.5rem",
            borderTop: "1px solid #151515",
            display: "flex",
            flexWrap: "wrap",
            justifyContent: "space-between",
            gap: "0.5rem",
            fontSize: "0.55rem",
            color: "#333",
            letterSpacing: "0.18em",
          }}>
            <div>© 2026 JOSEPH SIERENGOWSKI · ALL RIGHTS RESERVED</div>
            <div>NYX-J5W-2026-SIERENGOWSKI-LOCKED</div>
            <div>SILENT · DARK · PURELY FUNCTIONAL</div>
          </div>

        </main>
      </div>
    </div>
  );
}
