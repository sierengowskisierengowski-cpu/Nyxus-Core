// ============================================
// NYXUS — Build Manifest
// Copyright © 2026 Joseph Sierengowski
// All Rights Reserved
// NYX-J5W-2026-SIERENGOWSKI-LOCKED
// ============================================
//
// Live "what's in this build" page so you can see the full app inventory
// of the current ISO without having to actually boot it. Mirrors
// iso-builder/build-iso.sh APPS_LIST plus the family of system overlays
// (fog, screensaver, demon-wake, welcome) that don't get a menu entry
// but ship in /opt/nyxus.
//
// Hash route: #/build

const NYX = {
  smoke:  "rgba(14,14,22,0.55)",
  ink:    "rgba(8,8,14,0.78)",
  void:   "rgba(0,0,0,0.92)",
  glowSoft:   "rgba(255,255,255,0.45)",
  glowBright: "rgba(255,255,255,0.85)",
  text:   "#e8edf5",
  text2:  "#c8ccd6",
  dim:    "#6a6e78",
  hair:   "rgba(255,255,255,0.08)",
  hair2:  "rgba(255,255,255,0.14)",
  ok:     "#6ee7a3",
};

const FONT_MONO = "'JetBrains Mono', ui-monospace, SFMono-Regular, monospace";
const FONT_DISPLAY = "'Inter Display', 'Inter', system-ui, sans-serif";
const WORDMARK_GLOW = `0 0 8px ${NYX.glowBright}, 0 0 18px ${NYX.glowSoft}`;

type App = {
  bin: string;
  display: string;
  blurb: string;
  status: "menu" | "overlay" | "cli";
  rev: string;
};

const APPS: App[] = [
  // Menu apps (APPS_LIST entries)
  { bin: "nyxus-notepad",    display: "Notepad",        blurb: "Markdown editor with live Pango preview, 2s autosave, Ctrl+N/O/S shortcuts.",         status: "menu",    rev: "Adw r1 · 2026-05-12" },
  { bin: "nyxus-stickies",   display: "Stickies",       blurb: "Cairo paper-note canvas, JSON persistence, drag-to-reposition, color picker.",        status: "menu",    rev: "Adw wrap · 2026-05-12" },
  { bin: "nyxus-notes",      display: "Notes",          blurb: "Lightweight scratchpad with dirty-state save indicator.",                              status: "menu",    rev: "Adw wrap · 2026-05-12" },
  { bin: "nyxus-sysmon",     display: "System Monitor", blurb: "8 Cairo pages: Overview, CPU, Memory, Disk, Network, GPU, Processes, Sensors. Live header pills.", status: "menu", rev: "Adw refactor · 2026-05-12" },
  { bin: "nyxus-settings",   display: "Settings",       blurb: "17 sections, fully wired backends — Network, Bluetooth, Display, Sound, Power, Privacy, Updates, Users, etc.", status: "menu", rev: "r11 · gold standard" },
  { bin: "nyxus-control",    display: "Control",        blurb: "HW profile + fan curves + RGB + processes + profiles. 6 nav pages.",                  status: "menu",    rev: "Adw wrap · 2026-05-12" },
  { bin: "nyxus-terminal",   display: "Terminal",       blurb: "VTE-backed terminal with chrome glow; honest fallback if VTE binding is missing.",     status: "menu",    rev: "Adw wrap · 2026-05-12" },
  { bin: "nyxus-launcher",   display: "Launcher",       blurb: "Rofi-style fuzzy launcher: .desktop scan + score-based match + keyboard nav.",         status: "menu",    rev: "Adw wrap · 2026-05-12" },
  { bin: "nyxus-screenshot", display: "Screenshot",     blurb: "Region or full-screen `grim` + `slurp` wrapper with mode picker.",                    status: "menu",    rev: "Adw wrap · 2026-05-12" },
  { bin: "nyxus-store",      display: "App Store",      blurb: "Settings-style libadwaita package manager: Featured, Installed, Updates, Search, Repos. pacman + AUR + flatpak with pkexec elevation.", status: "menu", rev: "NEW · 2026-05-12" },
  { bin: "nyxus-powermenu",  display: "Power",          blurb: "6 tactile tiles: Lock, Suspend, Logout, Restart, Shutdown, Cancel. Confirm gates on destructive actions.", status: "menu", rev: "NEW · 2026-05-12" },
  { bin: "nyxus-doctor",     display: "Doctor",         blurb: "One-shot health audit (CLI). Cache, scripts, hyprctl, EWW, API server, exits 0/1.",   status: "cli",     rev: "audited · 2026-05-12" },

  // System overlays + first-boot (no APPS_LIST entry on purpose)
  { bin: "nyxus-welcome",    display: "Welcome Wizard", blurb: "First-boot setup: Hello → Region → Network → Account → Appearance → Privacy → Ready.", status: "overlay", rev: "r13 · audited" },
  { bin: "nyxus-fog",        display: "Fog Overlay",    blurb: "Layer-shell Cairo fog drifting around bar edges. Launch crash fixed (NameError on COLOR_GOLD).", status: "overlay", rev: "FIX · 2026-05-12" },
  { bin: "nyxus-screensaver",display: "Screensaver",    blurb: "Fullscreen Cairo screensaver, SIGTERM/SIGINT honored so hypridle wakes cleanly.",     status: "overlay", rev: "Adw wrap · 2026-05-12" },
  { bin: "nyxus-demon-wake", display: "Demon Wake",     blurb: "Lock/wake jumpscare overlay with hard-kill timer.",                                    status: "overlay", rev: "Adw wrap · 2026-05-12" },
];

const STATUS_LABEL: Record<App["status"], string> = {
  menu:    "MENU",
  overlay: "OVERLAY",
  cli:     "CLI",
};

const STATUS_COLOR: Record<App["status"], string> = {
  menu:    "#e8edf5",
  overlay: "#c8ccd6",
  cli:     "#9aa0ad",
};

function Card({ app }: { app: App }) {
  return (
    <div
      style={{
        background: NYX.ink,
        border: `1px solid ${NYX.hair2}`,
        borderRadius: 10,
        padding: "1.1rem 1.25rem",
        display: "flex",
        flexDirection: "column",
        gap: "0.55rem",
      }}
    >
      <div style={{ display: "flex", alignItems: "baseline", gap: "0.75rem", flexWrap: "wrap" }}>
        <div
          style={{
            fontFamily: FONT_DISPLAY,
            fontSize: "1.05rem",
            fontWeight: 600,
            color: NYX.text,
            letterSpacing: "0.02em",
          }}
        >
          {app.display}
        </div>
        <div
          style={{
            fontFamily: FONT_MONO,
            fontSize: "0.62rem",
            color: STATUS_COLOR[app.status],
            letterSpacing: "0.22em",
            border: `1px solid ${NYX.hair2}`,
            borderRadius: 4,
            padding: "1px 6px",
          }}
        >
          {STATUS_LABEL[app.status]}
        </div>
        <div style={{ flex: 1 }} />
        <div style={{ fontFamily: FONT_MONO, fontSize: "0.6rem", color: NYX.dim, letterSpacing: "0.18em" }}>
          {app.rev.toUpperCase()}
        </div>
      </div>
      <div style={{ fontFamily: FONT_MONO, fontSize: "0.65rem", color: NYX.dim, letterSpacing: "0.14em" }}>
        $ {app.bin}
      </div>
      <div style={{ fontFamily: FONT_DISPLAY, fontSize: "0.85rem", color: NYX.text2, lineHeight: 1.55 }}>
        {app.blurb}
      </div>
    </div>
  );
}

export default function BuildManifest() {
  const menuApps    = APPS.filter((a) => a.status === "menu");
  const overlayApps = APPS.filter((a) => a.status === "overlay");
  const cliApps     = APPS.filter((a) => a.status === "cli");

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "radial-gradient(circle at 50% 0%, #14141c 0%, #050507 60%, #000000 100%)",
        color: NYX.text,
        padding: "3rem 1.5rem 5rem",
      }}
    >
      <div style={{ maxWidth: 1100, margin: "0 auto" }}>
        {/* Header */}
        <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", flexWrap: "wrap", gap: "1rem", marginBottom: "0.4rem" }}>
          <div
            style={{
              fontFamily: FONT_DISPLAY,
              fontSize: "2.2rem",
              fontWeight: 700,
              letterSpacing: "0.08em",
              textShadow: WORDMARK_GLOW,
            }}
          >
            NYXUS BUILD MANIFEST
          </div>
          <a
            href="#/"
            style={{
              fontFamily: FONT_MONO,
              fontSize: "0.7rem",
              color: NYX.dim,
              letterSpacing: "0.22em",
              textDecoration: "none",
              border: `1px solid ${NYX.hair2}`,
              borderRadius: 4,
              padding: "0.4rem 0.8rem",
            }}
          >
            ← BACK TO PORTAL
          </a>
        </div>
        <div style={{ fontFamily: FONT_MONO, fontSize: "0.7rem", color: NYX.dim, letterSpacing: "0.22em", marginBottom: "2.5rem" }}>
          DARK MIRROR · TRIPLE-BLACK · REV R15 · 2026-05-12
        </div>

        {/* Stat strip */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
            gap: "0.85rem",
            marginBottom: "2.5rem",
          }}
        >
          <Stat label="MENU APPS"    value={menuApps.length} hint="In the app launcher" />
          <Stat label="OVERLAYS"     value={overlayApps.length} hint="System surfaces, no menu" />
          <Stat label="CLI"          value={cliApps.length} hint="Terminal-only" />
          <Stat label="ADW UNIFIED"  value={APPS.filter(a => a.status !== "cli").length} hint="Same dark theme + flow" />
        </div>

        {/* Menu apps grid */}
        <SectionTitle>App Launcher</SectionTitle>
        <Grid>
          {menuApps.map((a) => <Card key={a.bin} app={a} />)}
        </Grid>

        {/* Overlays */}
        <SectionTitle>System Overlays</SectionTitle>
        <Grid>
          {overlayApps.map((a) => <Card key={a.bin} app={a} />)}
        </Grid>

        {/* CLI */}
        <SectionTitle>Terminal Tools</SectionTitle>
        <Grid>
          {cliApps.map((a) => <Card key={a.bin} app={a} />)}
        </Grid>

        {/* Footer note */}
        <div
          style={{
            marginTop: "3rem",
            padding: "1rem 1.25rem",
            background: NYX.smoke,
            border: `1px solid ${NYX.hair}`,
            borderRadius: 8,
            fontFamily: FONT_MONO,
            fontSize: "0.7rem",
            color: NYX.dim,
            letterSpacing: "0.14em",
            lineHeight: 1.6,
          }}
        >
          ALL 13 GUI APPS NOW SUBCLASS <span style={{ color: NYX.text2 }}>Adw.Application</span>,
          CALL <span style={{ color: NYX.text2 }}>Adw.init()</span>, AND FORCE
          <span style={{ color: NYX.text2 }}> Adw.ColorScheme.FORCE_DARK</span> ON ACTIVATE.
          SAME SHARED <span style={{ color: NYX.text2 }}>nyxus_chrome</span> GRAFFITI BACKGROUND
          + <span style={{ color: NYX.text2 }}>nyxus_palette</span> TOKENS.
          DOCTOR STAYS CLI BY DESIGN.
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value, hint }: { label: string; value: number; hint: string }) {
  return (
    <div
      style={{
        background: NYX.ink,
        border: `1px solid ${NYX.hair2}`,
        borderRadius: 8,
        padding: "1rem 1.1rem",
      }}
    >
      <div style={{ fontFamily: FONT_MONO, fontSize: "0.6rem", color: NYX.dim, letterSpacing: "0.22em", marginBottom: "0.4rem" }}>
        {label}
      </div>
      <div style={{ fontFamily: FONT_DISPLAY, fontSize: "1.8rem", fontWeight: 700, color: NYX.text, lineHeight: 1, marginBottom: "0.3rem" }}>
        {value}
      </div>
      <div style={{ fontFamily: FONT_MONO, fontSize: "0.62rem", color: NYX.dim, letterSpacing: "0.16em" }}>
        {hint}
      </div>
    </div>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        fontFamily: FONT_DISPLAY,
        fontSize: "1.15rem",
        fontWeight: 600,
        color: NYX.text,
        letterSpacing: "0.06em",
        marginBottom: "0.85rem",
        marginTop: "1.25rem",
        paddingBottom: "0.55rem",
        borderBottom: `1px solid ${NYX.hair2}`,
      }}
    >
      {children}
    </div>
  );
}

function Grid({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(330px, 1fr))",
        gap: "0.85rem",
        marginBottom: "2rem",
      }}
    >
      {children}
    </div>
  );
}
