import { useState, useEffect, useRef } from "react";
import Mirror from "./pages/Mirror";

const BASE = "/api/download/nyxus";

function useHashRoute() {
  const [route, setRoute] = useState(() => window.location.hash.replace(/^#\/?/, ""));
  useEffect(() => {
    const handler = () => setRoute(window.location.hash.replace(/^#\/?/, ""));
    window.addEventListener("hashchange", handler);
    return () => window.removeEventListener("hashchange", handler);
  }, []);
  return route;
}

const SCRIPTS = [
  {
    id: "nyxus_motd.py",
    label: "MOTD",
    title: "nyxus_motd.py",
    tag: "Component A",
    color: "#c084fc",
    glow: "rgba(192,132,252,0.25)",
    desc: "Terminal welcome banner. Dense hacker aesthetic ASCII art filling the entire screen — NYXUS logo, 30+ tool names scattered in neon colors, skull art, binary filler rows, and a live boot status panel.",
    detail: [
      "Auto-fits any terminal size",
      "30+ tools: nmap, metasploit, hashcat, wireshark…",
      "Skull ASCII art + warning block",
      "Press [ENTER] to continue",
    ],
  },
  {
    id: "nyxus_error.py",
    label: "ERROR",
    title: "nyxus_error.py",
    tag: "Component B",
    color: "#f87171",
    glow: "rgba(248,113,113,0.25)",
    desc: "Full-screen red binary matrix takeover. 0s and 1s cascade down every column in deep red gradients, glowing ERROR block letters bloom from the center, with error details and retry options below.",
    detail: [
      "Live animated rain loop",
      "Multi-shade red depth (52→196)",
      "Radial glow bloom effect",
      "[R] Retry  [S] Shell  [Q] Quit",
    ],
  },
  {
    id: "nyxus_preboot.py",
    label: "PRE-BOOT",
    title: "nyxus_preboot.py",
    tag: "Component C",
    color: "#34d399",
    glow: "rgba(52,211,153,0.25)",
    desc: "TV static / signal corruption glitch at 24fps. Random block chars, box drawing, braille, hex — all in white/cyan/magenta/green chaos with horizontal scanline tears and color spikes. Snaps to black.",
    detail: [
      "2.8s of pure chaos at 24fps",
      "Horizontal scanline tear glitches",
      "Color spike explosions",
      "3-flash white snap → black",
    ],
  },
  {
    id: "nyxus_splash.py",
    label: "SPLASH",
    title: "nyxus_splash.py",
    tag: "Component D",
    color: "#fb923c",
    glow: "rgba(251,146,60,0.25)",
    desc: "Red Matrix boot splash. Real-looking hex/assembly code rains down in a deep red radial glow. NYXUS logo fades in after 3s, tagline appears, boot status prints, then fades to black.",
    detail: [
      "30fps animated code rain",
      "Radial glow gradient center",
      "Assembly + hex code lines",
      "Boot status messages",
    ],
  },
];

function GlitchText({ text, color }: { text: string; color: string }) {
  const [display, setDisplay] = useState(text);
  const chars = "!@#$%^&*_-+=[]{}|;:<>?/\\~`0123456789ABCDEFabcdef";
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  const glitch = () => {
    let iter = 0;
    if (timer.current) clearInterval(timer.current);
    timer.current = setInterval(() => {
      setDisplay(
        text
          .split("")
          .map((ch, i) => {
            if (i < iter) return text[i];
            return ch === " " ? " " : chars[Math.floor(Math.random() * chars.length)];
          })
          .join("")
      );
      if (iter >= text.length) {
        clearInterval(timer.current!);
        setDisplay(text);
      }
      iter += 1.5;
    }, 30);
  };

  return (
    <span
      style={{ color, textShadow: `0 0 12px ${color}`, cursor: "default", fontWeight: 700 }}
      onMouseEnter={glitch}
    >
      {display}
    </span>
  );
}

function MatrixRain({ color }: { color: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const W = canvas.width = canvas.offsetWidth;
    const H = canvas.height = canvas.offsetHeight;
    const cols = Math.floor(W / 12);
    const drops = Array(cols).fill(0).map(() => Math.random() * H / 14);

    const draw = () => {
      ctx.fillStyle = "rgba(10,10,10,0.18)";
      ctx.fillRect(0, 0, W, H);
      ctx.fillStyle = color + "cc";
      ctx.font = "11px monospace";
      for (let i = 0; i < drops.length; i++) {
        const ch = Math.random() > 0.5 ? "1" : "0";
        ctx.fillText(ch, i * 12, drops[i] * 14);
        if (drops[i] * 14 > H && Math.random() > 0.975) drops[i] = 0;
        drops[i]++;
      }
    };

    const id = setInterval(draw, 50);
    return () => clearInterval(id);
  }, [color]);

  return <canvas ref={canvasRef} style={{ position: "absolute", inset: 0, width: "100%", height: "100%", opacity: 0.18 }} />;
}

function ScriptCard({ s, idx }: { s: typeof SCRIPTS[0]; idx: number }) {
  const [copied, setCopied] = useState(false);
  const curlCmd = `curl -fsSL -O "${window.location.origin}${BASE}/${s.id}"`;

  const copy = () => {
    navigator.clipboard.writeText(curlCmd);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      style={{
        position: "relative",
        border: `1px solid ${s.color}44`,
        borderRadius: 4,
        padding: "1.5rem",
        background: "rgba(6,4,12,0.55)",
        backdropFilter: "blur(14px) saturate(1.6)",
        WebkitBackdropFilter: "blur(14px) saturate(1.6)",
        boxShadow: `0 0 32px ${s.glow}, inset 0 0 40px rgba(0,0,0,0.5)`,
        overflow: "hidden",
        animationDelay: `${idx * 0.1}s`,
      }}
      className="animate-fade-in"
    >
      <MatrixRain color={s.color} />

      <div style={{ position: "relative", zIndex: 1 }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: "0.75rem", marginBottom: "0.75rem" }}>
          <span style={{ fontSize: "0.65rem", color: s.color, border: `1px solid ${s.color}66`, padding: "1px 6px", borderRadius: 2 }}>
            {s.tag}
          </span>
          <span style={{ color: "#555", fontSize: "0.7rem" }}>──────</span>
        </div>

        <h2 style={{ margin: "0 0 0.25rem", fontSize: "1.1rem" }}>
          <GlitchText text={s.title} color={s.color} />
        </h2>

        <div style={{ fontSize: "0.7rem", color: "#888", marginBottom: "1rem", letterSpacing: "0.15em", textTransform: "uppercase" }}>
          {s.label} MODULE
        </div>

        <p style={{ color: "#aaa", fontSize: "0.8rem", lineHeight: 1.7, marginBottom: "1rem" }}>
          {s.desc}
        </p>

        <ul style={{ listStyle: "none", padding: 0, margin: "0 0 1.25rem", display: "flex", flexDirection: "column", gap: "0.3rem" }}>
          {s.detail.map((d, i) => (
            <li key={i} style={{ fontSize: "0.72rem", color: "#777", display: "flex", gap: "0.5rem" }}>
              <span style={{ color: s.color }}>▸</span>
              <span>{d}</span>
            </li>
          ))}
        </ul>

        <div style={{ background: "#0a0a0a", border: "1px solid #222", borderRadius: 3, padding: "0.6rem 0.85rem", marginBottom: "0.75rem", display: "flex", alignItems: "center", justifyContent: "space-between", gap: "0.5rem" }}>
          <code style={{ fontSize: "0.68rem", color: "#666", flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            <span style={{ color: "#444" }}>$</span> {curlCmd.replace(`${window.location.origin}`, `$BASE`)}
          </code>
          <button
            onClick={copy}
            style={{
              background: copied ? s.color + "33" : "transparent",
              border: `1px solid ${copied ? s.color : "#333"}`,
              color: copied ? s.color : "#555",
              padding: "2px 8px",
              borderRadius: 2,
              fontSize: "0.65rem",
              cursor: "pointer",
              whiteSpace: "nowrap",
              transition: "all 0.2s",
              letterSpacing: "0.05em",
            }}
          >
            {copied ? "COPIED" : "COPY"}
          </button>
        </div>

        <a
          href={`${BASE}/${s.id}`}
          download={s.id}
          style={{
            display: "block",
            textAlign: "center",
            padding: "0.6rem",
            background: s.color + "18",
            border: `1px solid ${s.color}66`,
            color: s.color,
            textDecoration: "none",
            fontSize: "0.75rem",
            letterSpacing: "0.15em",
            borderRadius: 2,
            transition: "all 0.2s",
            textShadow: `0 0 8px ${s.color}`,
          }}
          onMouseEnter={e => (e.currentTarget.style.background = s.color + "30")}
          onMouseLeave={e => (e.currentTarget.style.background = s.color + "18")}
        >
          ▼  DOWNLOAD  {s.id.toUpperCase()}
        </a>
      </div>
    </div>
  );
}

function Ticker() {
  const items = [
    "NYXUS OS v2.0", "SILENT", "DARK", "PURELY FUNCTIONAL",
    "© 2026 JOSEPH SIERENGOWSKI", "NYX-J5W-2026-SIERENGOWSKI-LOCKED",
    "nmap", "metasploit", "hashcat", "wireshark", "hydra", "sqlmap",
    "SYSTEM OPERATIONAL", "STEALTH MODE", "AES-256 ARMED",
  ];
  const full = [...items, ...items];
  return (
    <div style={{ overflow: "hidden", borderTop: "1px solid #1a1a1a", borderBottom: "1px solid #1a1a1a", padding: "0.35rem 0", background: "#070707" }}>
      <div style={{ display: "flex", gap: "3rem", animation: "ticker 30s linear infinite", whiteSpace: "nowrap" }}>
        {full.map((item, i) => (
          <span key={i} style={{ fontSize: "0.65rem", color: "#333", letterSpacing: "0.12em", textTransform: "uppercase" }}>
            {item}
          </span>
        ))}
      </div>
      <style>{`@keyframes ticker { from { transform: translateX(0) } to { transform: translateX(-50%) } }`}</style>
    </div>
  );
}

const BG_URL = `${import.meta.env.BASE_URL}nyxus-bg.png`;

export default function App() {
  const route = useHashRoute();
  const [time, setTime] = useState(new Date().toISOString().replace("T", " ").slice(0, 19));

  useEffect(() => {
    const t = setInterval(() => setTime(new Date().toISOString().replace("T", " ").slice(0, 19)), 1000);
    return () => clearInterval(t);
  }, []);

  if (route === "mirror") return <Mirror />;

  return (
    <div style={{
      minHeight: "100vh",
      display: "flex",
      flexDirection: "column",
      backgroundImage: `url(${BG_URL})`,
      backgroundSize: "cover",
      backgroundPosition: "center top",
      backgroundAttachment: "fixed",
      backgroundRepeat: "no-repeat",
      position: "relative",
    }}>
      {/* Dark vignette overlay — keeps text readable */}
      <div style={{
        position: "fixed",
        inset: 0,
        background: "radial-gradient(ellipse at 50% 0%, rgba(0,0,0,0.55) 0%, rgba(0,0,0,0.82) 60%, rgba(0,0,0,0.95) 100%)",
        pointerEvents: "none",
        zIndex: 0,
      }} />

      {/* All content above overlay */}
      <div style={{ position: "relative", zIndex: 1, display: "flex", flexDirection: "column", minHeight: "100vh" }}>

        {/* Header */}
        <header style={{ padding: "2rem 2rem 1rem", borderBottom: "1px solid rgba(255,255,255,0.04)", background: "rgba(0,0,0,0.6)", backdropFilter: "blur(2px)" }}>
          <div style={{ maxWidth: 960, margin: "0 auto" }}>
            <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", flexWrap: "wrap", gap: "0.5rem" }}>
              <div>
                <div style={{ fontSize: "0.65rem", color: "#444", letterSpacing: "0.2em", marginBottom: "0.4rem" }}>
                  NYX-J5W-2026-SIERENGOWSKI-LOCKED
                </div>
                <h1 style={{ margin: 0, fontSize: "clamp(1.8rem, 5vw, 3rem)", fontWeight: 900, letterSpacing: "0.12em" }}>
                  <span style={{ color: "#c084fc", textShadow: "0 0 24px rgba(192,132,252,0.6)" }}>NYX</span>
                  <span style={{ color: "#555" }}>US</span>
                </h1>
                <div style={{ fontSize: "0.65rem", color: "#444", letterSpacing: "0.25em", marginTop: "0.2rem" }}>
                  SILENT · DARK · PURELY FUNCTIONAL
                </div>
              </div>
              <div style={{ textAlign: "right" }}>
                <a
                  href="#/mirror"
                  style={{
                    display: "inline-block",
                    fontSize: "0.6rem",
                    color: "#c084fc",
                    textDecoration: "none",
                    border: "1px solid rgba(192,132,252,0.4)",
                    padding: "4px 10px",
                    borderRadius: 2,
                    letterSpacing: "0.18em",
                    marginBottom: "0.4rem",
                    textShadow: "0 0 8px rgba(192,132,252,0.5)",
                    transition: "all 0.2s",
                  }}
                  onMouseEnter={e => (e.currentTarget.style.background = "rgba(192,132,252,0.18)")}
                  onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
                >
                  ◐ MIRROR · ALL APPS
                </a>
                <div style={{ fontSize: "0.6rem", color: "#2a2a2a", fontFamily: "monospace" }}>{time} UTC</div>
                <div style={{ fontSize: "0.6rem", color: "#1e1e1e", marginTop: "0.2rem" }}>KERNEL 6.6.0-nyxus · x86_64</div>
                <div style={{ fontSize: "0.6rem", color: "#1e1e1e" }}>STATUS: <span style={{ color: "#2d6a3f" }}>OPERATIONAL</span></div>
              </div>
            </div>
          </div>
        </header>

        <Ticker />

        {/* Body */}
        <main style={{ flex: 1, padding: "2rem", maxWidth: 960, margin: "0 auto", width: "100%" }}>

          <div style={{ marginBottom: "2rem" }}>
            <div style={{ fontSize: "0.65rem", color: "#444", letterSpacing: "0.2em", marginBottom: "0.5rem" }}>
              // VISUAL COMPONENTS · LIVE TTY ENVIRONMENT
            </div>
            <p style={{ color: "#555", fontSize: "0.8rem", lineHeight: 1.8, maxWidth: 640 }}>
              Four terminal components for the NYXUS live environment.
              Drop them into <code style={{ color: "#c084fc" }}>/usr/local/lib/nyxus/</code> and run with Python 3.
              Pure standard library. No external dependencies.
            </p>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(420px, 1fr))", gap: "1.25rem" }}>
            {SCRIPTS.map((s, i) => <ScriptCard key={s.id} s={s} idx={i} />)}
          </div>

          {/* Wallpaper section */}
          <div style={{ marginTop: "3rem" }}>
            <div style={{ fontSize: "0.65rem", color: "#444", letterSpacing: "0.2em", marginBottom: "1rem" }}>
              // NYXUS WALLPAPER · HYPRLAND DESKTOP BACKGROUND
            </div>
            <div style={{
              position: "relative",
              border: "1px solid rgba(192,132,252,0.3)",
              borderRadius: 4,
              overflow: "hidden",
              background: "#000",
              boxShadow: "0 0 60px rgba(192,132,252,0.15), 0 0 120px rgba(192,132,252,0.06)",
            }}>
              <img
                src={`${import.meta.env.BASE_URL}nyxus-wallpaper.png`}
                alt="NYXUS Wallpaper"
                style={{ display: "block", width: "100%", height: "auto", maxHeight: 360, objectFit: "cover", opacity: 0.92 }}
              />
              <div style={{
                position: "absolute",
                bottom: 0,
                left: 0,
                right: 0,
                background: "linear-gradient(to top, rgba(0,0,0,0.95) 0%, rgba(0,0,0,0.6) 60%, transparent 100%)",
                padding: "1.5rem",
                display: "flex",
                alignItems: "flex-end",
                justifyContent: "space-between",
                gap: "1rem",
                flexWrap: "wrap",
              }}>
                <div>
                  <div style={{ fontSize: "0.6rem", color: "#c084fc99", letterSpacing: "0.2em", marginBottom: "0.3rem" }}>WALLPAPER · 16:9 · PNG</div>
                  <div style={{ fontSize: "0.85rem", color: "#c084fc", fontWeight: 700, letterSpacing: "0.1em", textShadow: "0 0 12px rgba(192,132,252,0.6)" }}>
                    nyxus-wallpaper.png
                  </div>
                  <div style={{ fontSize: "0.65rem", color: "#555", marginTop: "0.3rem" }}>
                    Crystal spire · volumetric neon glow · hex tile floor · NYXUS palette
                  </div>
                </div>
                <a
                  href={`${window.location.origin}${BASE}/nyxus-wallpaper.png`}
                  download="nyxus-wallpaper.png"
                  style={{
                    display: "inline-block",
                    padding: "0.5rem 1.25rem",
                    background: "rgba(192,132,252,0.12)",
                    border: "1px solid rgba(192,132,252,0.4)",
                    borderRadius: 3,
                    color: "#c084fc",
                    fontSize: "0.65rem",
                    letterSpacing: "0.15em",
                    textDecoration: "none",
                    fontWeight: 700,
                    transition: "all 0.2s",
                    textShadow: "0 0 8px rgba(192,132,252,0.5)",
                  }}
                  onMouseEnter={e => (e.currentTarget.style.background = "rgba(192,132,252,0.25)")}
                  onMouseLeave={e => (e.currentTarget.style.background = "rgba(192,132,252,0.12)")}
                >
                  ▼  DOWNLOAD
                </a>
              </div>
            </div>

            {/* Wallpaper curl command */}
            <div style={{ marginTop: "0.75rem", background: "rgba(6,4,12,0.55)", backdropFilter: "blur(14px) saturate(1.6)", WebkitBackdropFilter: "blur(14px) saturate(1.6)", border: "1px solid rgba(255,0,255,0.1)", borderRadius: 3, padding: "0.75rem 1rem" }}>
              <pre style={{ margin: 0, fontSize: "0.7rem", color: "#555", lineHeight: 1.6, overflow: "auto" }}>
{`# Download to ~/.config/hypr/
curl -fsSL -o ~/.config/hypr/nyxus-wallpaper.png "${window.location.origin}${BASE}/nyxus-wallpaper.png"`}
              </pre>
            </div>
          </div>

          {/* SDDM Theme section */}
          <div style={{ marginTop: "3rem" }}>
            <div style={{ fontSize: "0.65rem", color: "#444", letterSpacing: "0.2em", marginBottom: "1rem" }}>
              // SDDM LOGIN THEME · HYPRLAND · GLASS PANEL UI
            </div>

            <div style={{
              border: "1px solid rgba(192,132,252,0.25)",
              borderRadius: 4,
              overflow: "hidden",
              background: "rgba(6,4,12,0.55)",
              backdropFilter: "blur(14px) saturate(1.6)",
              WebkitBackdropFilter: "blur(14px) saturate(1.6)",
              boxShadow: "0 0 60px rgba(192,132,252,0.08), inset 0 0 60px rgba(192,132,252,0.02)",
            }}>
              {/* Title bar — matches the theme's own panel chrome */}
              <div style={{
                padding: "0.6rem 1rem",
                borderBottom: "1px solid rgba(192,132,252,0.12)",
                background: "rgba(192,132,252,0.05)",
                display: "flex",
                alignItems: "center",
                gap: "0.6rem",
              }}>
                {["#f87171","#fb923c","#34d399"].map(c => (
                  <span key={c} style={{ width: 8, height: 8, borderRadius: "50%", background: c, opacity: 0.7, display: "inline-block" }} />
                ))}
                <span style={{ fontSize: "0.65rem", color: "rgba(192,132,252,0.6)", letterSpacing: "0.2em", marginLeft: 4 }}>
                  NYXUS · SECURE SESSION INIT
                </span>
              </div>

              {/* Preview mockup — glass panel rendered in HTML */}
              <div style={{ padding: "2rem", display: "flex", gap: "2rem", alignItems: "flex-start", flexWrap: "wrap" }}>

                {/* Left: login form mockup */}
                <div style={{ flex: "1 1 260px", minWidth: 240 }}>
                  <div style={{ fontSize: "0.55rem", color: "rgba(52,211,153,0.7)", letterSpacing: "0.12em", lineHeight: 2 }}>
                    {["[  0.001]  Initializing NYXUS security kernel...", "[  0.043]  Loading encrypted session modules...", "[  0.112]  Establishing secure handshake...", "[  0.198]  Awaiting operator credentials."].map((l,i) => (
                      <div key={i}>{l}</div>
                    ))}
                  </div>
                  <div style={{ marginTop: "1rem", borderTop: "1px solid rgba(192,132,252,0.1)", paddingTop: "1rem" }}>
                    <div style={{ fontSize: "0.55rem", color: "rgba(192,132,252,0.45)", letterSpacing: "0.2em", marginBottom: 4 }}>OPERATOR ID</div>
                    <div style={{ border: "1px solid rgba(192,132,252,0.3)", padding: "0.35rem 0.75rem", fontSize: "0.7rem", color: "#c084fc", fontFamily: "monospace", marginBottom: "0.75rem" }}>nyx</div>
                    <div style={{ fontSize: "0.55rem", color: "rgba(192,132,252,0.45)", letterSpacing: "0.2em", marginBottom: 4 }}>PASSPHRASE</div>
                    <div style={{ border: "1px solid #c084fc", padding: "0.35rem 0.75rem", fontSize: "0.9rem", color: "#c084fc", fontFamily: "monospace", letterSpacing: "0.35em", boxShadow: "0 0 10px rgba(192,132,252,0.2)" }}>████████</div>
                    <div style={{ marginTop: "1rem", border: "1px solid rgba(192,132,252,0.4)", padding: "0.5rem", textAlign: "center", fontSize: "0.6rem", color: "#c084fc", letterSpacing: "0.2em", background: "rgba(192,132,252,0.08)" }}>
                      AUTHENTICATE  →
                    </div>
                  </div>
                </div>

                {/* Right: features */}
                <div style={{ flex: "1 1 220px" }}>
                  <div style={{ fontSize: "0.8rem", color: "#c084fc", fontWeight: 700, letterSpacing: "0.08em", marginBottom: "0.75rem", textShadow: "0 0 12px rgba(192,132,252,0.5)" }}>
                    nyxus-sddm-theme
                  </div>
                  <div style={{ fontSize: "0.6rem", color: "#444", lineHeight: 2 }}>
                    {[
                      { icon: "◈", c: "#c084fc", t: "Animated hex-grid canvas overlay" },
                      { icon: "◈", c: "#c084fc", t: "Border traces itself on boot (QML Canvas)" },
                      { icon: "◈", c: "#34d399", t: "Sequential terminal boot log reveal" },
                      { icon: "◈", c: "#34d399", t: "Glassmorphism panel · FastBlur backdrop" },
                      { icon: "◈", c: "#fb923c", t: "Neon glow on focus · shake on fail" },
                      { icon: "◈", c: "#fb923c", t: "Session selector + reboot / shutdown" },
                      { icon: "◈", c: "#f87171", t: "Caps lock warning · live system clock" },
                      { icon: "◈", c: "#f87171", t: "Full Hyprland/Wayland compatible" },
                    ].map((f, i) => (
                      <div key={i} style={{ color: "#333" }}>
                        <span style={{ color: f.c, marginRight: 8 }}>{f.icon}</span>{f.t}
                      </div>
                    ))}
                  </div>

                  <div style={{ marginTop: "1.25rem", display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                    <a
                      href={`${BASE}/nyxus-sddm-theme.tar.gz`}
                      download="nyxus-sddm-theme.tar.gz"
                      style={{
                        display: "block",
                        textAlign: "center",
                        padding: "0.55rem 1rem",
                        background: "rgba(192,132,252,0.12)",
                        border: "1px solid rgba(192,132,252,0.45)",
                        borderTop: "2px solid #c084fc",
                        color: "#c084fc",
                        fontSize: "0.65rem",
                        letterSpacing: "0.15em",
                        textDecoration: "none",
                        fontWeight: 700,
                        textShadow: "0 0 8px rgba(192,132,252,0.5)",
                        transition: "all 0.2s",
                      }}
                      onMouseEnter={e => (e.currentTarget.style.background = "rgba(192,132,252,0.22)")}
                      onMouseLeave={e => (e.currentTarget.style.background = "rgba(192,132,252,0.12)")}
                    >
                      ▼  DOWNLOAD  nyxus-sddm-theme.tar.gz
                    </a>
                    <div style={{ fontSize: "0.55rem", color: "#2a2a2a", textAlign: "center", letterSpacing: "0.1em" }}>
                      QML · SDDM 0.20+ · Qt 5.15 · Hyprland/Wayland
                    </div>
                  </div>
                </div>
              </div>

              {/* Install command */}
              <div style={{ borderTop: "1px solid rgba(192,132,252,0.08)", padding: "0.75rem 1.25rem", background: "rgba(0,0,0,0.4)" }}>
                <div style={{ fontSize: "0.55rem", color: "#2a2a2a", letterSpacing: "0.15em", marginBottom: 6 }}>// INSTALL</div>
                <pre style={{ margin: 0, fontSize: "0.68rem", color: "#444", lineHeight: 1.8, overflow: "auto" }}>
{`BASE="${window.location.origin}${BASE}"
curl -fsSL -o nyxus-sddm-theme.tar.gz "$BASE/nyxus-sddm-theme.tar.gz"
tar -xzf nyxus-sddm-theme.tar.gz
sudo bash sddm-theme/install.sh`}
                </pre>
              </div>
            </div>
          </div>

          {/* ── HYPRLOCK SECTION ──────────────────────────────── */}
          <div style={{ marginTop: "3rem" }}>
            <div style={{ fontSize: "0.65rem", color: "#444", letterSpacing: "0.2em", marginBottom: "1rem" }}>
              // HYPRLOCK · LOCK SCREEN · PURE BLACK
            </div>

            <div style={{
              border: "1px solid rgba(192,132,252,0.22)",
              borderRadius: 4,
              overflow: "hidden",
              background: "rgba(0,0,0,0.8)",
              backdropFilter: "blur(8px)",
              boxShadow: "0 0 48px rgba(192,132,252,0.07)",
            }}>
              {/* Mockup preview */}
              <div style={{ padding: "2rem", display: "flex", gap: "2rem", alignItems: "flex-start", flexWrap: "wrap" }}>

                {/* Left — visual mockup */}
                <div style={{
                  flex: "0 0 220px",
                  background: "#080808",
                  border: "1px solid rgba(192,132,252,0.15)",
                  padding: "1.5rem 1rem",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: "0.5rem",
                  fontFamily: "monospace",
                }}>
                  {/* Clock */}
                  <div style={{ fontSize: "2rem", fontWeight: 900, color: "#c084fc", textShadow: "0 0 20px rgba(192,132,252,0.6)", letterSpacing: "0.08em" }}>23:59</div>
                  <div style={{ fontSize: "0.55rem", color: "rgba(80,70,100,0.8)", letterSpacing: "0.15em" }}>Saturday · April 26 · 2026</div>

                  <div style={{ width: "60%", height: "1px", background: "rgba(192,132,252,0.08)", margin: "0.4rem 0" }} />

                  {/* Logo mark */}
                  <div style={{ fontSize: "1.6rem", letterSpacing: "0.05em" }}>
                    <span style={{ color: "#c084fc" }}>◤</span>
                    <span style={{ color: "#f472b6", fontWeight: 900 }}> X </span>
                    <span style={{ color: "#fbbf24" }}>◥</span>
                  </div>

                  {/* Wordmark */}
                  <div style={{ fontSize: "0.8rem", fontWeight: 700, letterSpacing: "0.12em" }}>
                    <span style={{ color: "#c084fc" }}>N</span>
                    <span style={{ color: "#d8b4fe" }}>y</span>
                    <span style={{ color: "#f472b6" }}>X</span>
                    <span style={{ color: "#818cf8" }}>.</span>
                    <span style={{ color: "#c084fc" }}>x</span>
                    <span style={{ color: "#818cf8" }}>.</span>
                    <span style={{ color: "#fbbf24" }}>O</span>
                    <span style={{ color: "#f9a8d4" }}>S</span>
                  </div>

                  <div style={{ fontSize: "0.5rem", color: "rgba(60,55,80,0.8)", letterSpacing: "0.12em" }}>Silent. Dark. Purely Functional.</div>

                  {/* Password field */}
                  <div style={{
                    marginTop: "0.5rem",
                    width: "90%",
                    border: "1px solid #c084fc",
                    padding: "0.35rem 0.7rem",
                    background: "rgba(8,8,8,0.97)",
                    color: "#c084fc",
                    fontSize: "0.85rem",
                    letterSpacing: "0.4em",
                    textAlign: "center",
                    boxShadow: "0 0 14px rgba(192,132,252,0.35)",
                  }}>
                    ████████
                  </div>
                </div>

                {/* Right — feature list */}
                <div style={{ flex: "1 1 220px" }}>
                  <div style={{ fontSize: "0.8rem", color: "#c084fc", fontWeight: 700, letterSpacing: "0.08em", marginBottom: "0.75rem", textShadow: "0 0 12px rgba(192,132,252,0.4)" }}>
                    hyprlock.conf
                  </div>
                  <div style={{ fontSize: "0.6rem", color: "#333", lineHeight: 2.2 }}>
                    {[
                      { c: "#c084fc", t: "Pure #080808 black background" },
                      { c: "#c084fc", t: "Large live clock, purple glow — HH:MM above logo" },
                      { c: "#d8b4fe", t: "Dim date line below clock" },
                      { c: "#f472b6", t: "NyX.x.OS X logo mark — purple/pink/gold" },
                      { c: "#fbbf24", t: "NyX.x.OS wordmark + tagline" },
                      { c: "#34d399", t: "Password field — dark BG, purple border glow" },
                      { c: "#f87171", t: "Fail state — red glow + ACCESS DENIED" },
                      { c: "#fb923c", t: "Caps lock warning — orange tint" },
                    ].map((f, i) => (
                      <div key={i}>
                        <span style={{ color: f.c, marginRight: 8 }}>◈</span>{f.t}
                      </div>
                    ))}
                  </div>

                  <div style={{ marginTop: "1.25rem", display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                    <a
                      href={`${BASE}/hyprlock.conf`}
                      download="hyprlock.conf"
                      style={{
                        display: "block",
                        textAlign: "center",
                        padding: "0.55rem 1rem",
                        background: "rgba(192,132,252,0.10)",
                        border: "1px solid rgba(192,132,252,0.42)",
                        borderTop: "2px solid #c084fc",
                        color: "#c084fc",
                        fontSize: "0.65rem",
                        letterSpacing: "0.15em",
                        textDecoration: "none",
                        fontWeight: 700,
                        textShadow: "0 0 8px rgba(192,132,252,0.4)",
                        transition: "all 0.2s",
                      }}
                      onMouseEnter={e => (e.currentTarget.style.background = "rgba(192,132,252,0.20)")}
                      onMouseLeave={e => (e.currentTarget.style.background = "rgba(192,132,252,0.10)")}
                    >
                      ▼  DOWNLOAD  hyprlock.conf
                    </a>
                    <div style={{ fontSize: "0.55rem", color: "#2a2a2a", textAlign: "center", letterSpacing: "0.1em" }}>
                      Hyprlock · JetBrains Mono · Wayland
                    </div>
                  </div>
                </div>
              </div>

              {/* Install */}
              <div style={{ borderTop: "1px solid rgba(192,132,252,0.08)", padding: "0.75rem 1.25rem", background: "rgba(0,0,0,0.4)" }}>
                <div style={{ fontSize: "0.55rem", color: "#2a2a2a", letterSpacing: "0.15em", marginBottom: 6 }}>// INSTALL</div>
                <pre style={{ margin: 0, fontSize: "0.68rem", color: "#444", lineHeight: 1.8, overflow: "auto" }}>
{`mkdir -p ~/.config/hypr
curl -fsSL -o ~/.config/hypr/hyprlock.conf "${window.location.origin}${BASE}/hyprlock.conf"
# Run: hyprlock`}
                </pre>
              </div>
            </div>
          </div>

          {/* ── WLOGOUT SECTION ───────────────────────────────── */}
          <div style={{ marginTop: "3rem" }}>
            <div style={{ fontSize: "0.65rem", color: "#444", letterSpacing: "0.2em", marginBottom: "1rem" }}>
              // WLOGOUT · POWER MENU · 6 ACTIONS
            </div>

            <div style={{
              border: "1px solid rgba(192,132,252,0.22)",
              borderRadius: 4,
              overflow: "hidden",
              background: "rgba(0,0,0,0.8)",
              backdropFilter: "blur(8px)",
              boxShadow: "0 0 48px rgba(192,132,252,0.07)",
            }}>
              {/* Mockup */}
              <div style={{ padding: "2rem", display: "flex", gap: "2rem", alignItems: "flex-start", flexWrap: "wrap" }}>

                {/* Left — button grid mockup */}
                <div style={{
                  flex: "0 0 260px",
                  background: "rgba(8,8,8,0.98)",
                  border: "1px solid rgba(192,132,252,0.12)",
                  padding: "1.25rem",
                }}>
                  <div style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(3, 1fr)",
                    gap: "6px",
                  }}>
                    {[
                      { label: "Lock",      icon: "⊘", color: "#c084fc" },
                      { label: "Logout",    icon: "→",  color: "#c084fc" },
                      { label: "Suspend",   icon: "☽",  color: "#c084fc" },
                      { label: "Hibernate", icon: "⏸",  color: "#c084fc" },
                      { label: "Reboot",    icon: "↺",  color: "#c084fc" },
                      { label: "Shutdown",  icon: "⏻",  color: "#f87171" },
                    ].map(({ label, icon, color }) => (
                      <div key={label} style={{
                        border: `1px solid ${color === "#f87171" ? "rgba(248,113,113,0.25)" : "rgba(192,132,252,0.28)"}`,
                        padding: "0.6rem 0.25rem",
                        display: "flex",
                        flexDirection: "column",
                        alignItems: "center",
                        gap: "0.3rem",
                        background: "rgba(12,10,18,0.92)",
                        fontFamily: "monospace",
                      }}>
                        <span style={{ fontSize: "1rem", color }}>{icon}</span>
                        <span style={{ fontSize: "0.45rem", color: color === "#f87171" ? "rgba(248,113,113,0.7)" : "rgba(192,132,252,0.7)", letterSpacing: "0.1em" }}>{label.toUpperCase()}</span>
                      </div>
                    ))}
                  </div>
                  <div style={{ marginTop: "0.75rem", textAlign: "center", fontSize: "0.45rem", color: "rgba(192,132,252,0.15)", letterSpacing: "0.15em", fontFamily: "monospace" }}>
                    NyX.x.OS · POWER CONTROL
                  </div>
                </div>

                {/* Right — features */}
                <div style={{ flex: "1 1 220px" }}>
                  <div style={{ fontSize: "0.8rem", color: "#c084fc", fontWeight: 700, letterSpacing: "0.08em", marginBottom: "0.75rem", textShadow: "0 0 12px rgba(192,132,252,0.4)" }}>
                    nyxus-wlogout.tar.gz
                  </div>
                  <div style={{ fontSize: "0.6rem", color: "#333", lineHeight: 2.2 }}>
                    {[
                      { c: "#c084fc", t: "Full-screen #080808 black background" },
                      { c: "#c084fc", t: "6 buttons — Lock, Logout, Suspend, Hibernate, Reboot, Shutdown" },
                      { c: "#d8b4fe", t: "Dark panel, purple border — SVG line icons" },
                      { c: "#f472b6", t: "Hover: transparent purple glow, border brightens" },
                      { c: "#f87171", t: "Shutdown: red accent, separate glow color" },
                      { c: "#34d399", t: "JetBrains Mono throughout, spaced caps labels" },
                      { c: "#fb923c", t: "NyX.x.OS branding at bottom" },
                      { c: "#818cf8", t: "layout + style.css + install.sh" },
                    ].map((f, i) => (
                      <div key={i}>
                        <span style={{ color: f.c, marginRight: 8 }}>◈</span>{f.t}
                      </div>
                    ))}
                  </div>

                  <div style={{ marginTop: "1.25rem", display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                    <a
                      href={`${BASE}/nyxus-wlogout.tar.gz`}
                      download="nyxus-wlogout.tar.gz"
                      style={{
                        display: "block",
                        textAlign: "center",
                        padding: "0.55rem 1rem",
                        background: "rgba(192,132,252,0.10)",
                        border: "1px solid rgba(192,132,252,0.42)",
                        borderTop: "2px solid #c084fc",
                        color: "#c084fc",
                        fontSize: "0.65rem",
                        letterSpacing: "0.15em",
                        textDecoration: "none",
                        fontWeight: 700,
                        textShadow: "0 0 8px rgba(192,132,252,0.4)",
                        transition: "all 0.2s",
                      }}
                      onMouseEnter={e => (e.currentTarget.style.background = "rgba(192,132,252,0.20)")}
                      onMouseLeave={e => (e.currentTarget.style.background = "rgba(192,132,252,0.10)")}
                    >
                      ▼  DOWNLOAD  nyxus-wlogout.tar.gz
                    </a>
                    <div style={{ fontSize: "0.55rem", color: "#2a2a2a", textAlign: "center", letterSpacing: "0.1em" }}>
                      GTK CSS · Wlogout · Wayland / Hyprland
                    </div>
                  </div>
                </div>
              </div>

              {/* Install */}
              <div style={{ borderTop: "1px solid rgba(192,132,252,0.08)", padding: "0.75rem 1.25rem", background: "rgba(0,0,0,0.4)" }}>
                <div style={{ fontSize: "0.55rem", color: "#2a2a2a", letterSpacing: "0.15em", marginBottom: 6 }}>// INSTALL</div>
                <pre style={{ margin: 0, fontSize: "0.68rem", color: "#444", lineHeight: 1.8, overflow: "auto" }}>
{`curl -fsSL -o nyxus-wlogout.tar.gz "${window.location.origin}${BASE}/nyxus-wlogout.tar.gz"
tar -xzf nyxus-wlogout.tar.gz && bash install.sh
# Run: wlogout --protocol layer-shell -b 4 -c 0 -r 0 -L 0`}
                </pre>
              </div>
            </div>
          </div>

          {/* ── UI CONFIGS SECTION ────────────────────────────── */}
          <div style={{ marginTop: "3rem" }}>
            <div style={{ fontSize: "0.65rem", color: "#444", letterSpacing: "0.2em", marginBottom: "1rem" }}>
              // UI CONFIGS · MAKO · ALACRITTY · GTK THEME
            </div>

            <div style={{
              border: "1px solid rgba(192,132,252,0.22)",
              borderRadius: 4,
              overflow: "hidden",
              background: "rgba(0,0,0,0.8)",
              backdropFilter: "blur(8px)",
              boxShadow: "0 0 48px rgba(192,132,252,0.07)",
            }}>
              <div style={{ padding: "2rem", display: "flex", gap: "2rem", flexWrap: "wrap" }}>

                {/* Left — visual mockups */}
                <div style={{ flex: "0 0 240px", display: "flex", flexDirection: "column", gap: "0.75rem" }}>

                  {/* Mako notification mockup */}
                  <div style={{
                    background: "rgba(8,8,8,0.96)",
                    border: "1px solid rgba(123,94,167,0.2)",
                    borderLeft: "3px solid #7B5EA7",
                    borderRadius: 6,
                    padding: "0.75rem 1rem",
                    fontFamily: "monospace",
                  }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.25rem" }}>
                      <span style={{ fontSize: "0.9rem" }}>🔔</span>
                      <span style={{ fontSize: "0.65rem", fontWeight: 700, color: "#f472b6", letterSpacing: "0.06em" }}>NyX.x.OS</span>
                    </div>
                    <div style={{ fontSize: "0.58rem", color: "rgba(200,192,192,0.65)", lineHeight: 1.5 }}>System initialized. All modules operational.</div>
                  </div>

                  {/* Mako error urgency */}
                  <div style={{
                    background: "rgba(15,8,10,0.96)",
                    border: "1px solid rgba(248,113,113,0.2)",
                    borderLeft: "3px solid #f87171",
                    borderRadius: 6,
                    padding: "0.75rem 1rem",
                    fontFamily: "monospace",
                  }}>
                    <div style={{ fontSize: "0.65rem", fontWeight: 700, color: "#f87171", marginBottom: "0.2rem" }}>CRITICAL</div>
                    <div style={{ fontSize: "0.58rem", color: "rgba(248,165,165,0.65)", lineHeight: 1.5 }}>Anomaly detected — high urgency alert</div>
                  </div>

                  {/* Alacritty terminal mockup */}
                  <div style={{
                    background: "rgba(8,8,8,0.88)",
                    border: "1px solid rgba(123,94,167,0.15)",
                    borderRadius: 4,
                    padding: "0.75rem 1rem",
                    fontFamily: "monospace",
                    fontSize: "0.55rem",
                    lineHeight: 1.7,
                  }}>
                    <div style={{ color: "#7B5EA7" }}>nyx<span style={{ color: "#C4607A" }}>@</span><span style={{ color: "#c084fc" }}>arch</span><span style={{ color: "#555" }}> ~ </span><span style={{ color: "#34d399" }}>$</span></div>
                    <div style={{ color: "#C8C0C0" }}>neofetch</div>
                    <div style={{ color: "#c084fc" }}>NyX.x.OS</div>
                    <div style={{ color: "#7a7080" }}>Silent. Dark. Purely Functional.</div>
                    <div style={{ color: "#34d399" }}>Kernel: 6.6.0-nyxus</div>
                    <div style={{ color: "#818cf8" }}>WM: Hyprland</div>
                  </div>
                </div>

                {/* Right — config list + downloads */}
                <div style={{ flex: "1 1 240px" }}>
                  <div style={{ fontSize: "0.8rem", color: "#c084fc", fontWeight: 700, letterSpacing: "0.08em", marginBottom: "0.75rem", textShadow: "0 0 12px rgba(192,132,252,0.4)" }}>
                    nyxus-ui-configs.tar.gz
                  </div>

                  <div style={{ display: "flex", flexDirection: "column", gap: "0.85rem", marginBottom: "1.25rem" }}>
                    {[
                      {
                        label: "MAKO NOTIFICATIONS",
                        file: "mako-config",
                        color: "#c084fc",
                        desc: "Pure black bg · purple left border · pink title · dim body · per-urgency glow",
                        dest: "~/.config/mako/config",
                      },
                      {
                        label: "ALACRITTY TERMINAL",
                        file: "alacritty.toml",
                        color: "#34d399",
                        desc: "JetBrains Mono Nerd Font · #080808 bg · #C8C0C0 text · 88% opacity · full NyX palette",
                        dest: "~/.config/alacritty/alacritty.toml",
                      },
                      {
                        label: "GTK 3/4 THEME",
                        file: null,
                        color: "#f472b6",
                        desc: "#080808 windows · #7B5EA7 accent · #C4607A hover · full widget coverage · Libadwaita vars",
                        dest: "~/.themes/NyXxOS/",
                      },
                    ].map((cfg, i) => (
                      <div key={i} style={{ borderLeft: `2px solid ${cfg.color}33`, paddingLeft: "0.75rem" }}>
                        <div style={{ fontSize: "0.6rem", color: cfg.color, letterSpacing: "0.15em", fontWeight: 700, marginBottom: "0.2rem" }}>{cfg.label}</div>
                        <div style={{ fontSize: "0.58rem", color: "#555", lineHeight: 1.5, marginBottom: "0.2rem" }}>{cfg.desc}</div>
                        <div style={{ fontSize: "0.52rem", color: "#333", fontFamily: "monospace" }}>{cfg.dest}</div>
                        {cfg.file && (
                          <a
                            href={`${BASE}/${cfg.file}`}
                            download={cfg.file}
                            style={{
                              display: "inline-block",
                              marginTop: "0.4rem",
                              padding: "2px 10px",
                              border: `1px solid ${cfg.color}44`,
                              color: cfg.color,
                              fontSize: "0.55rem",
                              letterSpacing: "0.12em",
                              textDecoration: "none",
                              transition: "all 0.2s",
                            }}
                            onMouseEnter={e => (e.currentTarget.style.borderColor = cfg.color)}
                            onMouseLeave={e => (e.currentTarget.style.borderColor = cfg.color + "44")}
                          >
                            ▼ {cfg.file}
                          </a>
                        )}
                      </div>
                    ))}
                  </div>

                  <a
                    href={`${BASE}/nyxus-ui-configs.tar.gz`}
                    download="nyxus-ui-configs.tar.gz"
                    style={{
                      display: "block",
                      textAlign: "center",
                      padding: "0.55rem 1rem",
                      background: "rgba(192,132,252,0.10)",
                      border: "1px solid rgba(192,132,252,0.42)",
                      borderTop: "2px solid #c084fc",
                      color: "#c084fc",
                      fontSize: "0.65rem",
                      letterSpacing: "0.15em",
                      textDecoration: "none",
                      fontWeight: 700,
                      textShadow: "0 0 8px rgba(192,132,252,0.4)",
                      transition: "all 0.2s",
                    }}
                    onMouseEnter={e => (e.currentTarget.style.background = "rgba(192,132,252,0.20)")}
                    onMouseLeave={e => (e.currentTarget.style.background = "rgba(192,132,252,0.10)")}
                  >
                    ▼  DOWNLOAD  nyxus-ui-configs.tar.gz
                  </a>
                  <div style={{ fontSize: "0.55rem", color: "#2a2a2a", textAlign: "center", letterSpacing: "0.1em", marginTop: "0.4rem" }}>
                    Mako · Alacritty · GTK3 · GTK4 · install.sh
                  </div>
                </div>
              </div>

              {/* Install */}
              <div style={{ borderTop: "1px solid rgba(192,132,252,0.08)", padding: "0.75rem 1.25rem", background: "rgba(0,0,0,0.4)" }}>
                <div style={{ fontSize: "0.55rem", color: "#2a2a2a", letterSpacing: "0.15em", marginBottom: 6 }}>// INSTALL ALL</div>
                <pre style={{ margin: 0, fontSize: "0.68rem", color: "#444", lineHeight: 1.8, overflow: "auto" }}>
{`curl -fsSL -o nyxus-ui-configs.tar.gz "${window.location.origin}${BASE}/nyxus-ui-configs.tar.gz"
tar -xzf nyxus-ui-configs.tar.gz && bash install.sh

# Hyprland: add to hyprland.conf
env = GTK_THEME,NyXxOS`}
                </pre>
              </div>
            </div>
          </div>

          {/* Batch curl block */}
          <div style={{ marginTop: "2.5rem", border: "1px solid #1a1a1a", borderRadius: 4, padding: "1.25rem", background: "rgba(7,7,7,0.9)" }}>
            <div style={{ fontSize: "0.65rem", color: "#444", letterSpacing: "0.15em", marginBottom: "0.75rem" }}>
              // BATCH INSTALL · COPY AND RUN
            </div>
            <pre style={{ margin: 0, fontSize: "0.72rem", color: "#555", lineHeight: 2, overflow: "auto" }}>
{`BASE="${window.location.origin}${BASE}"
curl -fsSL -o "nyxus_motd.py"    "$BASE/nyxus_motd.py"    && echo "✅ motd"
curl -fsSL -o "nyxus_error.py"   "$BASE/nyxus_error.py"   && echo "✅ error"
curl -fsSL -o "nyxus_preboot.py" "$BASE/nyxus_preboot.py" && echo "✅ preboot"
curl -fsSL -o "nyxus_splash.py"  "$BASE/nyxus_splash.py"  && echo "✅ splash"
chmod +x *.py && echo "✅ all ready"`}
            </pre>
          </div>
        </main>

        {/* Footer */}
        <footer style={{ padding: "1rem 2rem", borderTop: "1px solid rgba(255,255,255,0.03)", textAlign: "center", background: "rgba(0,0,0,0.7)" }}>
          <div style={{ fontSize: "0.6rem", color: "#222", letterSpacing: "0.15em" }}>
            © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
          </div>
        </footer>

      </div>
    </div>
  );
}
