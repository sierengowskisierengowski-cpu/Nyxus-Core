// ============================================
// NYXUS — Download Portal
// Copyright © 2026 Joseph Sierengowski
// All Rights Reserved
// NYX-J5W-2026-SIERENGOWSKI-LOCKED
// ============================================
//
// Landing page for nyxus-web. Mirrors the current state of NYXUS as of
// rev r5 (2026-05-10): Arch + Hyprland live ISO with built-in disk
// installer (`sudo nyxus-install`) and full hardware enablement for the
// MSI GS77 hybrid-graphics target. Locked to DARK MIRROR triple-black
// monochrome — no per-section accent colors, no neon. The only chroma
// allowed is the wallpaper image bleeding through and the white-glow
// accents on wordmarks (NYXUS / SIERENGOWSKI).

import { useState, useEffect } from "react";
import Mirror from "./pages/Mirror";
import WaybarMockup from "./pages/WaybarMockup";
import BuildManifest from "./pages/BuildManifest";

const BASE = "/api/download/nyxus";
const ISO_NAME = "nyx-2026.05.02-x86_64.iso";

// ── DARK MIRROR · TRIPLE-BLACK palette (matches replit.md rev r14) ──
const NYX = {
  smoke:  "rgba(14,14,22,0.55)",   // bars, panels, window backgrounds
  ink:    "rgba(8,8,14,0.78)",     // raised pebbles, cards, buttons
  void:   "rgba(0,0,0,0.92)",      // hover, active, popovers
  glowSoft:   "rgba(255,255,255,0.45)",
  glowBright: "rgba(255,255,255,0.85)",
  text:   "#e8edf5",
  text2:  "#c8ccd6",
  dim:    "#6a6e78",
  hair:   "rgba(255,255,255,0.08)",  // hairline borders
  hair2:  "rgba(255,255,255,0.14)",  // raised hairline
};

const FONT_MONO = "'JetBrains Mono', ui-monospace, SFMono-Regular, monospace";
const WORDMARK_GLOW = `0 0 8px ${NYX.glowBright}, 0 0 18px ${NYX.glowSoft}`;

// ── routing ────────────────────────────────────────────────────────────
function useHashRoute(): string {
  const [route, setRoute] = useState(() =>
    typeof window === "undefined" ? "" : window.location.hash.replace(/^#\/?/, ""),
  );
  useEffect(() => {
    const handler = () => setRoute(window.location.hash.replace(/^#\/?/, ""));
    window.addEventListener("hashchange", handler);
    return () => window.removeEventListener("hashchange", handler);
  }, []);
  return route;
}

// ── primitives ─────────────────────────────────────────────────────────
function Pebble({ children, raised = false }: { children: React.ReactNode; raised?: boolean }) {
  return (
    <div
      style={{
        background: raised ? NYX.ink : NYX.smoke,
        border: `1px solid ${raised ? NYX.hair2 : NYX.hair}`,
        borderRadius: 6,
        padding: "1.25rem 1.5rem",
        backdropFilter: "blur(14px) saturate(1.4)",
        WebkitBackdropFilter: "blur(14px) saturate(1.4)",
      }}
    >
      {children}
    </div>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        fontFamily: FONT_MONO,
        fontSize: "0.62rem",
        color: NYX.dim,
        letterSpacing: "0.22em",
        textTransform: "uppercase",
        marginBottom: "0.85rem",
      }}
    >
      // {children}
    </div>
  );
}

function SpecRow({ k, v }: { k: string; v: string }) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        gap: "1rem",
        fontSize: "0.72rem",
        padding: "0.4rem 0",
        borderBottom: `1px solid ${NYX.hair}`,
      }}
    >
      <span style={{ color: NYX.dim, fontFamily: FONT_MONO, letterSpacing: "0.08em" }}>{k}</span>
      <span style={{ color: NYX.text, fontFamily: FONT_MONO, textAlign: "right" }}>{v}</span>
    </div>
  );
}

function Code({ children }: { children: React.ReactNode }) {
  return (
    <code
      style={{
        background: NYX.void,
        border: `1px solid ${NYX.hair}`,
        borderRadius: 3,
        padding: "0.15rem 0.4rem",
        fontFamily: FONT_MONO,
        fontSize: "0.72rem",
        color: NYX.text,
      }}
    >
      {children}
    </code>
  );
}

function CopyBlock({ lines }: { lines: string[] }) {
  const [copied, setCopied] = useState(false);
  const text = lines.join("\n");
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* ignore */
    }
  };
  return (
    <div
      style={{
        background: NYX.void,
        border: `1px solid ${NYX.hair}`,
        borderRadius: 4,
        padding: "0.85rem 1rem",
        position: "relative",
      }}
    >
      <button
        onClick={copy}
        style={{
          position: "absolute",
          top: 8,
          right: 8,
          background: copied ? NYX.text : "transparent",
          color: copied ? "#000" : NYX.dim,
          border: `1px solid ${copied ? NYX.text : NYX.hair2}`,
          borderRadius: 3,
          padding: "2px 9px",
          fontFamily: FONT_MONO,
          fontSize: "0.6rem",
          letterSpacing: "0.18em",
          cursor: "pointer",
          transition: "all 0.15s",
        }}
      >
        {copied ? "COPIED" : "COPY"}
      </button>
      <pre
        style={{
          margin: 0,
          fontFamily: FONT_MONO,
          fontSize: "0.7rem",
          color: NYX.text2,
          lineHeight: 1.7,
          overflow: "auto",
          paddingRight: "3.5rem",
        }}
      >
        {text}
      </pre>
    </div>
  );
}

function NavPill({ href, label }: { href: string; label: string }) {
  const [hover, setHover] = useState(false);
  return (
    <a
      href={href}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        display: "inline-block",
        background: hover ? NYX.void : NYX.ink,
        border: `1px solid ${hover ? NYX.glowSoft : NYX.hair2}`,
        color: NYX.text,
        padding: "0.5rem 0.95rem",
        fontFamily: FONT_MONO,
        fontSize: "0.62rem",
        letterSpacing: "0.18em",
        textDecoration: "none",
        borderRadius: 3,
        textShadow: hover ? WORDMARK_GLOW : undefined,
        transition: "all 0.15s",
      }}
    >
      {label}
    </a>
  );
}

// ── ROOT LANDING ───────────────────────────────────────────────────────
const BG_URL = `${import.meta.env.BASE_URL}nyxus-bg.png`;

function Landing() {
  const [time, setTime] = useState(() => new Date().toISOString().replace("T", " ").slice(0, 19));
  useEffect(() => {
    const t = setInterval(
      () => setTime(new Date().toISOString().replace("T", " ").slice(0, 19)),
      1000,
    );
    return () => clearInterval(t);
  }, []);

  return (
    <div
      style={{
        minHeight: "100vh",
        color: NYX.text,
        backgroundImage: `url(${BG_URL})`,
        backgroundSize: "cover",
        backgroundPosition: "center top",
        backgroundAttachment: "fixed",
        backgroundRepeat: "no-repeat",
        position: "relative",
        fontFamily: "system-ui, -apple-system, sans-serif",
      }}
    >
      {/* Vignette — keeps the wallpaper readable but never tinted */}
      <div
        style={{
          position: "fixed",
          inset: 0,
          background:
            "radial-gradient(ellipse at 50% 0%, rgba(0,0,0,0.70) 0%, rgba(0,0,0,0.88) 60%, rgba(0,0,0,0.95) 100%)",
          pointerEvents: "none",
          zIndex: 0,
        }}
      />

      <div style={{ position: "relative", zIndex: 1 }}>
        {/* ── Header ────────────────────────────────────────────────── */}
        <header
          style={{
            padding: "1.5rem 2rem 1.25rem",
            background: NYX.smoke,
            backdropFilter: "blur(18px) saturate(1.5)",
            WebkitBackdropFilter: "blur(18px) saturate(1.5)",
            borderBottom: `1px solid ${NYX.hair}`,
          }}
        >
          <div
            style={{
              maxWidth: 1080,
              margin: "0 auto",
              display: "flex",
              alignItems: "flex-end",
              justifyContent: "space-between",
              flexWrap: "wrap",
              gap: "1rem",
            }}
          >
            <div>
              <div
                style={{
                  fontFamily: FONT_MONO,
                  fontSize: "0.6rem",
                  color: NYX.dim,
                  letterSpacing: "0.28em",
                  marginBottom: "0.55rem",
                }}
              >
                NYX-J5W-2026-SIERENGOWSKI-LOCKED
              </div>
              <h1
                style={{
                  margin: 0,
                  fontSize: "clamp(2.2rem, 6vw, 3.4rem)",
                  fontWeight: 900,
                  letterSpacing: "0.12em",
                  color: NYX.text,
                  textShadow: WORDMARK_GLOW,
                  lineHeight: 1,
                }}
              >
                NYXUS
              </h1>
              <div
                style={{
                  fontFamily: FONT_MONO,
                  fontSize: "0.65rem",
                  color: NYX.text2,
                  letterSpacing: "0.32em",
                  marginTop: "0.55rem",
                  textTransform: "uppercase",
                }}
              >
                Dark · Silent · Purely Functional
              </div>
            </div>

            <div
              style={{
                textAlign: "right",
                fontFamily: FONT_MONO,
                fontSize: "0.62rem",
                color: NYX.dim,
                lineHeight: 1.9,
              }}
            >
              <div>{time} UTC</div>
              <div>
                BUILD <span style={{ color: NYX.text2 }}>{ISO_NAME}</span>
              </div>
              <div>
                STATUS <span style={{ color: NYX.text }}>OPERATIONAL</span>
              </div>
              <div style={{ marginTop: "0.6rem", display: "flex", gap: "0.4rem", justifyContent: "flex-end" }}>
                <NavPill href="#/mirror" label="◐ MIRROR" />
                <NavPill href="#/waybars" label="◑ EWW BAR" />
              </div>
            </div>
          </div>
        </header>

        {/* ── Body ──────────────────────────────────────────────────── */}
        <main style={{ maxWidth: 1080, margin: "0 auto", padding: "2.5rem 2rem 3rem" }}>
          {/* ── Hero / overview ─────────────────────────────────────── */}
          <Pebble>
            <SectionLabel>WHAT IT IS</SectionLabel>
            <p style={{ margin: 0, fontSize: "0.95rem", lineHeight: 1.75, color: NYX.text }}>
              NYXUS is an{" "}
              <span style={{ color: NYX.text, textShadow: WORDMARK_GLOW }}>Arch Linux</span>-based
              operating system built on{" "}
              <span style={{ color: NYX.text, textShadow: WORDMARK_GLOW }}>Hyprland</span> with a
              suite of native Python GTK4 applications. The live ISO ships a guided disk installer
              and a full hardware-enablement stack tuned for{" "}
              <span style={{ color: NYX.text2 }}>MSI GS77 (i9-12900H + RTX 3060)</span>: NVIDIA
              hybrid graphics, Intel iGPU, sof-firmware audio, Vulkan, Steam-ready multilib, and
              power/thermal management. Locked to a single visual system —{" "}
              <span style={{ color: NYX.text2 }}>DARK MIRROR · Triple-Black</span>.
            </p>
          </Pebble>

          {/* ── System spec grid ────────────────────────────────────── */}
          <div
            style={{
              marginTop: "1.25rem",
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
              gap: "1.25rem",
            }}
          >
            <Pebble raised>
              <SectionLabel>BASE SYSTEM</SectionLabel>
              <SpecRow k="OS" v="Arch Linux" />
              <SpecRow k="Kernel" v="linux (latest)" />
              <SpecRow k="Init" v="systemd" />
              <SpecRow k="Compositor" v="Hyprland" />
              <SpecRow k="Login" v="SDDM" />
              <SpecRow k="Audio" v="PipeWire" />
            </Pebble>

            <Pebble raised>
              <SectionLabel>HARDWARE STACK</SectionLabel>
              <SpecRow k="dGPU" v="NVIDIA DKMS + lib32" />
              <SpecRow k="iGPU" v="Intel media-driver" />
              <SpecRow k="Vulkan" v="loaders + tools" />
              <SpecRow k="Audio FW" v="sof-firmware" />
              <SpecRow k="Power" v="thermald + PPD" />
              <SpecRow k="Suspend" v="nvidia-{s,r,h}" />
            </Pebble>

            <Pebble raised>
              <SectionLabel>VISUAL SYSTEM</SectionLabel>
              <SpecRow k="Theme" v="DARK MIRROR r14" />
              <SpecRow k="Surfaces" v="Triple-Black" />
              <SpecRow k="Toolkit" v="GTK4 + libadwaita" />
              <SpecRow k="Chrome" v="nyxus_chrome.py" />
              <SpecRow k="Notify" v="Dunst" />
              <SpecRow k="Bar" v="EWW · 4 bars + dashboard + OSDs" />
              <SpecRow k="Wallpaper" v="swaybg · void-vortex" />
            </Pebble>
          </div>

          {/* ── Get the ISO ─────────────────────────────────────────── */}
          <div style={{ marginTop: "2rem" }}>
            <Pebble>
              <SectionLabel>GET THE ISO</SectionLabel>
              <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap", alignItems: "center" }}>
                <a
                  href={`${BASE}/${ISO_NAME}`}
                  download={ISO_NAME}
                  style={{
                    background: NYX.text,
                    color: "#000",
                    padding: "0.85rem 1.6rem",
                    fontFamily: FONT_MONO,
                    fontWeight: 700,
                    fontSize: "0.78rem",
                    letterSpacing: "0.18em",
                    textDecoration: "none",
                    borderRadius: 3,
                    border: `1px solid ${NYX.text}`,
                    boxShadow: `0 0 24px ${NYX.glowSoft}`,
                    transition: "all 0.15s",
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.boxShadow = `0 0 32px ${NYX.glowBright}`)}
                  onMouseLeave={(e) => (e.currentTarget.style.boxShadow = `0 0 24px ${NYX.glowSoft}`)}
                >
                  ▼  DOWNLOAD  {ISO_NAME}
                </a>
                <span style={{ fontSize: "0.7rem", color: NYX.dim, fontFamily: FONT_MONO }}>
                  ~2.5 GB · x86_64 · BIOS + UEFI bootable · Ventoy compatible
                </span>
              </div>

              <div style={{ marginTop: "1.25rem" }}>
                <div style={{ fontSize: "0.7rem", color: NYX.dim, marginBottom: "0.5rem" }}>
                  Or pull it from the command line:
                </div>
                <CopyBlock
                  lines={[
                    `curl -fL -o ${ISO_NAME} \\`,
                    `  "${typeof window !== "undefined" ? window.location.origin : ""}${BASE}/${ISO_NAME}"`,
                    `sha256sum ${ISO_NAME}`,
                  ]}
                />
              </div>
            </Pebble>
          </div>

          {/* ── Install flow ────────────────────────────────────────── */}
          <div style={{ marginTop: "2rem" }}>
            <Pebble>
              <SectionLabel>INSTALL FLOW · 4 STEPS</SectionLabel>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "1rem" }}>
                {[
                  {
                    n: "01",
                    h: "Flash to USB",
                    b: "Drop the .iso onto a Ventoy stick or write it with `dd` / Rufus / balenaEtcher.",
                  },
                  {
                    n: "02",
                    h: "Boot the live session",
                    b: "Pick the NYX entry from your boot menu. Live login is `nyx` / `nyx`. Pick Hyprland in SDDM.",
                  },
                  {
                    n: "03",
                    h: "Open a terminal",
                    b: "Run `sudo nyxus-install`. Wraps `archinstall`, then auto-runs the NYXUS post-install hook.",
                  },
                  {
                    n: "04",
                    h: "Reboot",
                    b: "Hardware drivers loaded, services enabled, GTK4 apps installed from offline cache. Done.",
                  },
                ].map((s) => (
                  <div
                    key={s.n}
                    style={{
                      background: NYX.ink,
                      border: `1px solid ${NYX.hair2}`,
                      borderRadius: 4,
                      padding: "1rem 1.1rem",
                    }}
                  >
                    <div
                      style={{
                        fontFamily: FONT_MONO,
                        fontSize: "1.6rem",
                        color: NYX.text,
                        letterSpacing: "0.05em",
                        textShadow: WORDMARK_GLOW,
                        marginBottom: "0.45rem",
                      }}
                    >
                      {s.n}
                    </div>
                    <div
                      style={{
                        fontSize: "0.78rem",
                        color: NYX.text,
                        fontWeight: 600,
                        marginBottom: "0.4rem",
                        letterSpacing: "0.04em",
                      }}
                    >
                      {s.h}
                    </div>
                    <div style={{ fontSize: "0.7rem", color: NYX.dim, lineHeight: 1.6 }}>
                      {s.b.split("`").map((part, i) => (i % 2 === 1 ? <Code key={i}>{part}</Code> : <span key={i}>{part}</span>))}
                    </div>
                  </div>
                ))}
              </div>

              <div style={{ marginTop: "1.25rem" }}>
                <div style={{ fontSize: "0.7rem", color: NYX.dim, marginBottom: "0.5rem" }}>
                  Recommended <Code>archinstall</Code> answers:
                </div>
                <CopyBlock
                  lines={[
                    "Bootloader      → systemd-boot (or grub)",
                    "Profile         → minimal",
                    "Audio           → pipewire",
                    "Kernels         → linux",
                    "Network         → NetworkManager",
                    "Additional pkgs → leave EMPTY (postinstall handles them)",
                    "Desktop profile → DO NOT enable (NYXUS replaces it)",
                  ]}
                />
              </div>
            </Pebble>
          </div>

          {/* ── Hardware enablement details ─────────────────────────── */}
          <div style={{ marginTop: "2rem" }}>
            <Pebble>
              <SectionLabel>WHAT POSTINSTALL DOES</SectionLabel>
              <ul
                style={{
                  margin: 0,
                  paddingLeft: "1.2rem",
                  fontSize: "0.78rem",
                  color: NYX.text2,
                  lineHeight: 2,
                }}
              >
                <li>
                  Installs the full NYXUS hardware stack into the new root via{" "}
                  <Code>pacman -S --needed</Code> — independent of which archinstall profile you
                  pick.
                </li>
                <li>
                  Stages the locked <Code>/etc/mkinitcpio.conf</Code> (i915 → nvidia early-KMS) and{" "}
                  <Code>/etc/modprobe.d/nvidia.conf</Code> (modeset=1) into the new root, then
                  regenerates initramfs.
                </li>
                <li>
                  Enables: <Code>NetworkManager</Code>, <Code>SDDM</Code>, <Code>bluetooth</Code>,{" "}
                  <Code>thermald</Code>, <Code>power-profiles-daemon</Code>, <Code>cups</Code>,{" "}
                  <Code>acpid</Code>, <Code>fstrim.timer</Code>, and the NVIDIA{" "}
                  <Code>suspend</Code>/<Code>resume</Code>/<Code>hibernate</Code> hooks.
                </li>
                <li>
                  Installs all NYXUS GTK4 apps from the baked offline cache at{" "}
                  <Code>/opt/nyxus-cache</Code> with <Code>NYXUS_OFFLINE_DIR</Code> set — works
                  even with no internet.
                </li>
              </ul>
            </Pebble>
          </div>

          {/* ── Apps suite ──────────────────────────────────────────── */}
          <div style={{ marginTop: "2rem" }}>
            <Pebble>
              <SectionLabel>NATIVE GTK4 APP SUITE</SectionLabel>
              <p style={{ margin: "0 0 1rem", fontSize: "0.78rem", color: NYX.text2, lineHeight: 1.7 }}>
                Every NYXUS app is native Python + GTK4 with the unified{" "}
                <Code>nyxus_chrome.py</Code> shell applied. No Electron. No web shells. Click
                through to the live web mirror to interact with the desktop.
              </p>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))",
                  gap: "0.5rem",
                  marginBottom: "1.25rem",
                }}
              >
                {[
                  "Home",
                  "Notes",
                  "Stickies",
                  "Terminal",
                  "Settings",
                  "SysMon",
                  "Control",
                  "Launcher",
                  "Powermenu",
                  "Screenshot",
                  "Calendar",
                  "Clock",
                  "Cheatsheet",
                  "Studio",
                  "Sage",
                  "Shield",
                  "Intel",
                  "Phantom",
                  "Passwords",
                  "Weather",
                ].map((n) => (
                  <div
                    key={n}
                    style={{
                      background: NYX.ink,
                      border: `1px solid ${NYX.hair}`,
                      borderRadius: 3,
                      padding: "0.55rem 0.7rem",
                      fontFamily: FONT_MONO,
                      fontSize: "0.7rem",
                      color: NYX.text2,
                      letterSpacing: "0.06em",
                      textAlign: "center",
                    }}
                  >
                    {n}
                  </div>
                ))}
              </div>
              <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                <NavPill href="#/mirror" label="◐ OPEN DESKTOP MIRROR" />
                <NavPill href="#/waybars" label="◑ OPEN EWW BAR PREVIEW" />
              </div>
            </Pebble>
          </div>

          {/* ── Live login / build info ─────────────────────────────── */}
          <div style={{ marginTop: "2rem", display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "1.25rem" }}>
            <Pebble raised>
              <SectionLabel>LIVE ISO CREDENTIALS</SectionLabel>
              <SpecRow k="user" v="nyx · nyx" />
              <SpecRow k="root" v="root · nyx" />
              <SpecRow k="session" v="Hyprland (SDDM)" />
              <SpecRow k="install cmd" v="sudo nyxus-install" />
            </Pebble>

            <Pebble raised>
              <SectionLabel>BUILD IT YOURSELF</SectionLabel>
              <CopyBlock
                lines={[
                  "git clone <repo> nyxus && cd nyxus",
                  "pnpm install",
                  "pnpm --filter @workspace/api-server run build",
                  "cd iso-builder && sudo ./build-iso.sh",
                  `# → out/${ISO_NAME}`,
                ]}
              />
            </Pebble>
          </div>
        </main>

        {/* ── Footer ────────────────────────────────────────────────── */}
        <footer
          style={{
            padding: "1.25rem 2rem",
            borderTop: `1px solid ${NYX.hair}`,
            background: NYX.smoke,
            textAlign: "center",
          }}
        >
          <div style={{ fontFamily: FONT_MONO, fontSize: "0.6rem", color: NYX.dim, letterSpacing: "0.22em" }}>
            © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED ·{" "}
            <span style={{ color: NYX.text2 }}>DARK MIRROR · Triple-Black · rev r14</span>
          </div>
        </footer>
      </div>
    </div>
  );
}

export default function App() {
  const route = useHashRoute();
  if (route === "mirror") return <Mirror />;
  if (route === "waybars") return <WaybarMockup />;
  if (route === "build") return <BuildManifest />;
  return <Landing />;
}
