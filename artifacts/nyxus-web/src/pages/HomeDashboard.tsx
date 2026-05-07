// ============================================
// NYXUS — nyx-2026.05.02-x86_64.iso
// Copyright © 2026 Joseph Sierengowski
// All Rights Reserved
// NYX-J5W-2026-SIERENGOWSKI-LOCKED
// ============================================
//
// HomeDashboard — the persistent Home (page 0) widgets:
// Clock · Weather · Calendar · Notifications · Notepad · Password Manager.
// Cards are translucent with neon glow and slight rotation (hand-drawn feel).
// A graffiti-spatter layer floats behind the cards so wallpaper + paint mist
// show through. Widgets persist real data via localStorage (Notepad, Password
// Manager) and pull live data over real APIs (Weather: Open-Meteo, no auth).

import { useEffect, useMemo, useRef, useState, ReactNode } from "react";

// ── DARK MIRROR PALETTE (rev r16 LOCKED) — monochrome only ──────────────
// Per-card "neon" tints all collapse to the same off-white.
// Cards now read as dark glass plaques with white hairline borders.
const T = "#e8edf5";  // primary off-white
const T2 = "#c8ccd6"; // secondary
const C = {
  pink:    T,
  cyan:    T,
  purple:  T,
  gold:    T,
  indigo:  T,
  green:   T,
  orange:  T,
  blue:    T,
  red:     T2,    // close buttons stay slightly muted
  white:   "#ffffff",
  text:    T,
  dim:     "#6a6e78",
  void:    "#000000",
};

const NEONS = [T, T2, T, T2, T, T2, T, T2, T];

// ── TYPED LOCALSTORAGE ──────────────────────────────────────────────────
function useLocalStorage<T>(key: string, initial: T) {
  const [val, setVal] = useState<T>(() => {
    if (typeof window === "undefined") return initial;
    try {
      const raw = window.localStorage.getItem(key);
      return raw !== null ? (JSON.parse(raw) as T) : initial;
    } catch {
      return initial;
    }
  });
  useEffect(() => {
    try {
      window.localStorage.setItem(key, JSON.stringify(val));
    } catch { /* quota / private mode */ }
  }, [key, val]);
  return [val, setVal] as const;
}

function useTime() {
  const [t, setT] = useState(new Date());
  useEffect(() => {
    const i = setInterval(() => setT(new Date()), 1000);
    return () => clearInterval(i);
  }, []);
  return t;
}

// ── GRAFFITI SPATTER LAYER ──────────────────────────────────────────────
// Deterministic pseudo-random splats so layout doesn't reshuffle on rerender.
function rng(seed: number) {
  let s = seed;
  return () => {
    s = (s * 9301 + 49297) % 233280;
    return s / 233280;
  };
}

// Graffiti word collage — Arch / Hyprland / NYXUS lexicon, painted across
// the dashboard background in a riot of neon Caveat handwriting + a few
// paint drips. Deterministic positions so the collage is stable per session.
const GRAFFITI_WORDS = [
  "NYXUS", "NYX", "ARCH", "LINUX", "HYPRLAND", "WAYBAR", "KITTY", "FOOT",
  "ROFI", "DUNST", "NEOVIM", "ZSH", "TMUX", "BTRFS", "WAYLAND", "PIPEWIRE",
  "NETWORKD", "SYSTEMD", "PACMAN", "AUR", "MAKEPKG", "CACHYOS", "REISERFS",
  "INTEL", "PHANTOM", "SHIELD", "GODSAPP", "SAGE", "PANEL", "STUDIO",
  "NOTEPAD", "STICKIES", "SYSMON", "WIDGETS", "START",
  "CAVEAT", "JETBRAINS", "NERDFONT", "NEON", "ROOT", "OPS",
  "AES-256-GCM", "PBKDF2", "SHA-256", "TAMPER-OK", "ARMED",
  "SIERENGOWSKI", "J5W", "2026", "v2.0",
  "SILENT", "DARK", "FUNCTIONAL", "OPERATIONAL", "LOCKED",
];

function GraffitiLayer() {
  const words = useMemo(() => {
    const r = rng(20260502);
    return GRAFFITI_WORDS.map((w) => ({
      text:    w,
      x:       r() * 96 + 1,           // 1-97 vw%
      y:       r() * 94 + 2,           // 2-96 vh%
      rot:     -28 + r() * 56,         // -28..28 deg
      size:    0.85 + r() * 1.95,      // rem
      color:   NEONS[Math.floor(r() * NEONS.length)],
      opacity: 0.10 + r() * 0.22,      // 0.10..0.32
      weight:  r() > 0.55 ? 700 : 400,
      font:    r() > 0.30 ? "'Caveat', cursive" : '"JetBrains Mono", monospace',
    }));
  }, []);
  const drips = useMemo(() => {
    const r = rng(60606060);
    return Array.from({ length: 20 }).map(() => ({
      x:       r() * 100,
      y:       r() * 90,
      len:     8 + r() * 30,
      color:   NEONS[Math.floor(r() * NEONS.length)],
      opacity: 0.10 + r() * 0.20,
    }));
  }, []);
  const splats = useMemo(() => {
    const r = rng(31415927);
    return Array.from({ length: 14 }).map(() => ({
      cx:      r() * 100,
      cy:      r() * 100,
      rx:      6 + r() * 14,
      ry:      4 + r() * 12,
      rot:     r() * 360,
      color:   NEONS[Math.floor(r() * NEONS.length)],
      opacity: 0.05 + r() * 0.10,
    }));
  }, []);
  return (
    <div style={{
      position: "absolute",
      inset: 0,
      pointerEvents: "none",
      zIndex: 0,
      overflow: "hidden",
    }}>
      {/* paint mist splats */}
      <svg
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        style={{ position: "absolute", inset: 0, width: "100%", height: "100%", filter: "blur(2px)" }}
      >
        {splats.map((s, i) => (
          <ellipse
            key={`sp${i}`}
            cx={s.cx} cy={s.cy} rx={s.rx / 4} ry={s.ry / 4}
            fill={s.color} opacity={s.opacity}
            transform={`rotate(${s.rot} ${s.cx} ${s.cy})`}
          />
        ))}
        {drips.map((d, i) => (
          <line
            key={`dr${i}`}
            x1={d.x} x2={d.x} y1={d.y} y2={d.y + d.len / 3}
            stroke={d.color} strokeWidth="0.25"
            opacity={d.opacity} strokeLinecap="round"
          />
        ))}
      </svg>
      {/* word collage */}
      {words.map((w, i) => (
        <span
          key={`w${i}`}
          style={{
            position: "absolute",
            left: `${w.x}%`,
            top: `${w.y}%`,
            transform: `translate(-50%, -50%) rotate(${w.rot}deg)`,
            color: w.color,
            opacity: w.opacity,
            fontFamily: w.font,
            fontSize: `${w.size}rem`,
            fontWeight: w.weight,
            letterSpacing: w.font.includes("Caveat") ? "0.02em" : "0.18em",
            textShadow: `0 0 6px ${w.color}55, 0 0 12px ${w.color}33`,
            whiteSpace: "nowrap",
            userSelect: "none",
            mixBlendMode: "screen",
          }}
        >
          {w.text}
        </span>
      ))}
    </div>
  );
}

// ── CARD WRAPPER ────────────────────────────────────────────────────────
function Card({ tilt, color, title, glyph, span = 1, children, footer }: {
  tilt: number;
  color: string;
  title: string;
  glyph: string;
  span?: 1 | 2 | 3;
  children: ReactNode;
  footer?: ReactNode;
}) {
  return (
    <div style={{
      gridColumn: `span ${span}`,
      transform: `rotate(${tilt}deg)`,
      background: "rgba(6,4,12,0.42)",
      border: `1.5px dashed ${color}aa`,
      borderTop: `2px solid ${color}`,
      borderRadius: 8,
      boxShadow: `
        0 0 0 1px ${color}22,
        0 0 18px ${color}55,
        0 0 38px ${color}33,
        0 6px 22px rgba(0,0,0,0.55),
        inset 0 0 24px rgba(0,0,0,0.18)
      `,
      backdropFilter: "blur(14px) saturate(1.6)",
      WebkitBackdropFilter: "blur(14px) saturate(1.6)",
      padding: "0.9rem 1rem",
      display: "flex",
      flexDirection: "column",
      gap: 8,
      position: "relative",
      transition: "transform 0.25s ease",
      minHeight: 0,
    }}>
      <div style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        borderBottom: `1px dashed ${color}33`,
        paddingBottom: 6,
      }}>
        <span style={{
          color,
          fontSize: "1.2rem",
          textShadow: `0 0 10px ${color}, 0 0 18px ${color}88`,
          lineHeight: 1,
        }}>
          {glyph}
        </span>
        <span style={{
          fontFamily: "'Caveat', cursive",
          fontSize: "1.45rem",
          color,
          letterSpacing: "0.02em",
          fontWeight: 700,
          textShadow: `0 0 8px ${color}66`,
          lineHeight: 1,
        }}>
          {title}
        </span>
        <div style={{ flex: 1 }} />
        <span style={{
          fontSize: "0.5rem",
          color: `${color}77`,
          letterSpacing: "0.22em",
          fontFamily: '"JetBrains Mono", monospace',
        }}>
          NYX-J5W-2026
        </span>
      </div>
      <div style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column", gap: 8 }}>
        {children}
      </div>
      {footer && (
        <div style={{
          fontSize: "0.55rem",
          color: `${color}88`,
          letterSpacing: "0.16em",
          fontFamily: '"JetBrains Mono", monospace',
          borderTop: `1px dashed ${color}22`,
          paddingTop: 6,
        }}>
          {footer}
        </div>
      )}
    </div>
  );
}

// ── CLOCK CARD ──────────────────────────────────────────────────────────
function ClockCard() {
  const t = useTime();
  const hh = String(t.getHours()).padStart(2, "0");
  const mm = String(t.getMinutes()).padStart(2, "0");
  const ss = String(t.getSeconds()).padStart(2, "0");
  const day = t.toLocaleDateString("en-US", { weekday: "long" });
  const date = t.toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" });
  return (
    <Card tilt={-1.2} color={C.pink} title="Clock" glyph="◴" footer={`SYSTEM TIME · ${Intl.DateTimeFormat().resolvedOptions().timeZone}`}>
      <div style={{ textAlign: "center", padding: "0.5rem 0" }}>
        <div style={{
          fontFamily: '"JetBrains Mono", monospace',
          fontSize: "2.6rem",
          fontWeight: 700,
          color: C.text,
          letterSpacing: "0.05em",
          textShadow: `0 0 14px ${C.pink}88, 0 0 28px ${C.pink}44`,
          lineHeight: 1.05,
        }}>
          {hh}<span style={{ color: C.pink, opacity: t.getSeconds() % 2 ? 0.4 : 1 }}>:</span>{mm}
          <span style={{ fontSize: "1.2rem", color: C.dim, marginLeft: 6, fontWeight: 400 }}>{ss}</span>
        </div>
        <div style={{
          fontFamily: "'Caveat', cursive",
          fontSize: "1.4rem",
          color: C.cyan,
          letterSpacing: "0.04em",
          textShadow: `0 0 8px ${C.cyan}66`,
          marginTop: 4,
        }}>
          {day}
        </div>
        <div style={{
          fontFamily: '"JetBrains Mono", monospace',
          fontSize: "0.7rem",
          color: C.dim,
          letterSpacing: "0.1em",
          marginTop: 2,
        }}>
          {date}
        </div>
      </div>
    </Card>
  );
}

// ── WEATHER CARD (Open-Meteo, no auth) ──────────────────────────────────
type WeatherLoc = { lat: number; lon: number; label: string };
type WxData = {
  current: { temperature_2m: number; weather_code: number; wind_speed_10m: number };
  daily?: { temperature_2m_max: number[]; temperature_2m_min: number[] };
} | null;

const WX_CODES: Record<number, { label: string; glyph: string }> = {
  0:  { label: "Clear",            glyph: "☀\uFE0E" },
  1:  { label: "Mainly Clear",     glyph: "☀\uFE0E" },
  2:  { label: "Partly Cloudy",    glyph: "◐" },
  3:  { label: "Overcast",         glyph: "☁\uFE0E" },
  45: { label: "Fog",              glyph: "≋" },
  48: { label: "Rime Fog",         glyph: "≋" },
  51: { label: "Light Drizzle",    glyph: "☂\uFE0E" },
  53: { label: "Drizzle",          glyph: "☂\uFE0E" },
  55: { label: "Heavy Drizzle",    glyph: "☂\uFE0E" },
  61: { label: "Light Rain",       glyph: "☂\uFE0E" },
  63: { label: "Rain",             glyph: "☂\uFE0E" },
  65: { label: "Heavy Rain",       glyph: "☂\uFE0E" },
  71: { label: "Light Snow",       glyph: "❄\uFE0E" },
  73: { label: "Snow",             glyph: "❄\uFE0E" },
  75: { label: "Heavy Snow",       glyph: "❄\uFE0E" },
  77: { label: "Snow Grains",      glyph: "❄\uFE0E" },
  80: { label: "Rain Showers",     glyph: "☂\uFE0E" },
  81: { label: "Heavy Showers",    glyph: "☂\uFE0E" },
  82: { label: "Violent Showers",  glyph: "☂\uFE0E" },
  85: { label: "Snow Showers",     glyph: "❄\uFE0E" },
  86: { label: "Heavy Snow Show",  glyph: "❄\uFE0E" },
  95: { label: "Thunderstorm",     glyph: "⚡" },
  96: { label: "Storm + Hail",     glyph: "⚡" },
  99: { label: "Storm + Heavy Hail", glyph: "⚡" },
};

function WeatherCard() {
  const [loc, setLoc] = useLocalStorage<WeatherLoc>("nyxus_home_wxloc", { lat: 40.7128, lon: -74.0060, label: "New York, NY" });
  const [data, setData] = useState<WxData>(null);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState({ lat: String(loc.lat), lon: String(loc.lon), label: loc.label });

  useEffect(() => {
    let cancelled = false;
    setError(null);
    const url = `https://api.open-meteo.com/v1/forecast?latitude=${loc.lat}&longitude=${loc.lon}&current=temperature_2m,weather_code,wind_speed_10m&temperature_unit=fahrenheit&wind_speed_unit=mph&daily=temperature_2m_max,temperature_2m_min&timezone=auto&forecast_days=1`;
    fetch(url)
      .then(r => r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)))
      .then((j: WxData) => { if (!cancelled) setData(j); })
      .catch((e: Error) => { if (!cancelled) setError(e.message || "Network error"); });
    return () => { cancelled = true; };
  }, [loc.lat, loc.lon]);

  const code = data?.current?.weather_code ?? 0;
  const wx = WX_CODES[code] ?? { label: "Unknown", glyph: "◯" };

  return (
    <Card tilt={0.8} color={C.gold} title="Weather" glyph="☼" footer="OPEN-METEO · LIVE · NO AUTH">
      {!data && !error && (
        <div style={{ color: C.dim, fontSize: "0.8rem", textAlign: "center", padding: "1rem 0", fontFamily: "'Caveat', cursive" }}>
          loading…
        </div>
      )}
      {error && (
        <div style={{
          color: C.red, fontSize: "0.65rem", padding: "0.6rem",
          border: `1px dashed ${C.red}55`, borderRadius: 4,
          background: `${C.red}0a`, textAlign: "center",
        }}>
          {error}
        </div>
      )}
      {data && (
        <>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{
              fontSize: "2.2rem",
              color: C.gold,
              textShadow: `0 0 12px ${C.gold}88`,
              lineHeight: 1,
            }}>{wx.glyph}</div>
            <div>
              <div style={{
                fontFamily: '"JetBrains Mono", monospace',
                fontSize: "2.1rem",
                fontWeight: 700,
                color: C.text,
                lineHeight: 1,
                textShadow: `0 0 10px ${C.gold}66`,
              }}>
                {Math.round(data.current.temperature_2m)}<span style={{ fontSize: "1rem", color: C.dim }}>°F</span>
              </div>
              <div style={{ fontFamily: "'Caveat', cursive", fontSize: "1.05rem", color: C.gold, letterSpacing: "0.02em" }}>
                {wx.label}
              </div>
            </div>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.65rem", color: C.dim, fontFamily: '"JetBrains Mono", monospace', letterSpacing: "0.05em" }}>
            <span>↑ {data.daily?.temperature_2m_max?.[0] !== undefined ? Math.round(data.daily.temperature_2m_max[0]) : "—"}°</span>
            <span>↓ {data.daily?.temperature_2m_min?.[0] !== undefined ? Math.round(data.daily.temperature_2m_min[0]) : "—"}°</span>
            <span>WIND {Math.round(data.current.wind_speed_10m)} MPH</span>
          </div>
        </>
      )}
      <div style={{ display: "flex", gap: 4, alignItems: "center", marginTop: "auto" }}>
        <span style={{ flex: 1, fontFamily: "'Caveat', cursive", fontSize: "0.95rem", color: C.cyan, letterSpacing: "0.03em" }}>
          {loc.label}
        </span>
        <button
          onClick={() => { setDraft({ lat: String(loc.lat), lon: String(loc.lon), label: loc.label }); setEditing(e => !e); }}
          style={{
            background: "transparent", border: `1px solid ${C.gold}55`,
            color: C.gold, fontSize: "0.55rem", padding: "2px 8px",
            borderRadius: 2, cursor: "pointer", letterSpacing: "0.18em",
          }}
        >
          {editing ? "✕" : "EDIT"}
        </button>
      </div>
      {editing && (
        <div style={{ display: "flex", flexDirection: "column", gap: 4, padding: "6px 0" }}>
          <input
            value={draft.label}
            onChange={e => setDraft(d => ({ ...d, label: e.target.value }))}
            placeholder="Label"
            style={inputStyle(C.gold)}
          />
          <div style={{ display: "flex", gap: 4 }}>
            <input
              value={draft.lat}
              onChange={e => setDraft(d => ({ ...d, lat: e.target.value }))}
              placeholder="Lat"
              style={inputStyle(C.gold)}
            />
            <input
              value={draft.lon}
              onChange={e => setDraft(d => ({ ...d, lon: e.target.value }))}
              placeholder="Lon"
              style={inputStyle(C.gold)}
            />
          </div>
          <button
            onClick={() => {
              const lat = parseFloat(draft.lat);
              const lon = parseFloat(draft.lon);
              if (!isFinite(lat) || !isFinite(lon)) return;
              setLoc({ lat, lon, label: draft.label.trim() || `${lat.toFixed(2)}, ${lon.toFixed(2)}` });
              setEditing(false);
            }}
            style={primaryBtnStyle(C.gold)}
          >
            SAVE LOCATION
          </button>
        </div>
      )}
    </Card>
  );
}

// ── CALENDAR CARD ───────────────────────────────────────────────────────
function CalendarCard() {
  const today = useMemo(() => new Date(), []);
  const [view, setView] = useState({ y: today.getFullYear(), m: today.getMonth() });
  const monthName = useMemo(() => new Date(view.y, view.m, 1).toLocaleString("en-US", { month: "long" }), [view]);
  const grid = useMemo(() => {
    const first = new Date(view.y, view.m, 1);
    const startDow = first.getDay();
    const daysInMonth = new Date(view.y, view.m + 1, 0).getDate();
    const cells: ({ d: number } | null)[] = [];
    for (let i = 0; i < startDow; i++) cells.push(null);
    for (let d = 1; d <= daysInMonth; d++) cells.push({ d });
    while (cells.length % 7 !== 0) cells.push(null);
    return cells;
  }, [view]);
  const isToday = (d: number) =>
    d === today.getDate() && view.m === today.getMonth() && view.y === today.getFullYear();

  const nav = (n: number) => {
    const m = view.m + n;
    const y = view.y + Math.floor(m / 12);
    const mm = ((m % 12) + 12) % 12;
    setView({ y, m: mm });
  };

  return (
    <Card tilt={-0.5} color={C.purple} title="Calendar" glyph="▦" footer="LOCAL · GREGORIAN">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <button onClick={() => nav(-1)} style={navBtn(C.purple)}>◀</button>
        <div style={{
          fontFamily: "'Caveat', cursive",
          fontSize: "1.25rem",
          color: C.purple,
          letterSpacing: "0.04em",
          textShadow: `0 0 8px ${C.purple}55`,
        }}>
          {monthName} {view.y}
        </div>
        <button onClick={() => nav(1)} style={navBtn(C.purple)}>▶</button>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: 2, fontFamily: '"JetBrains Mono", monospace' }}>
        {["S", "M", "T", "W", "T", "F", "S"].map((d, i) => (
          <div key={i} style={{
            textAlign: "center",
            fontSize: "0.55rem",
            color: `${C.purple}aa`,
            letterSpacing: "0.18em",
            padding: "2px 0",
          }}>{d}</div>
        ))}
        {grid.map((cell, i) => {
          if (!cell) return <div key={i} />;
          const today = isToday(cell.d);
          return (
            <div key={i} style={{
              textAlign: "center",
              fontSize: "0.7rem",
              padding: "4px 0",
              color: today ? "#0a0612" : C.text,
              background: today
                ? `radial-gradient(circle at 35% 35%, ${C.purple}, ${C.pink} 80%)`
                : "transparent",
              borderRadius: today ? "50%" : 0,
              boxShadow: today ? `0 0 12px ${C.purple}, 0 0 20px ${C.pink}66` : "none",
              fontWeight: today ? 800 : 400,
              fontFamily: today ? "'Caveat', cursive" : '"JetBrains Mono", monospace',
            }}>
              {cell.d}
            </div>
          );
        })}
      </div>
      <button
        onClick={() => setView({ y: today.getFullYear(), m: today.getMonth() })}
        style={{
          background: "transparent",
          border: `1px solid ${C.purple}55`,
          color: C.purple,
          fontSize: "0.55rem",
          padding: "3px 8px",
          borderRadius: 2,
          cursor: "pointer",
          letterSpacing: "0.18em",
          alignSelf: "flex-start",
          fontFamily: '"JetBrains Mono", monospace',
        }}
      >
        ◉ TODAY
      </button>
    </Card>
  );
}

// ── NOTIFICATIONS CARD ──────────────────────────────────────────────────
type Notif = { id: string; glyph: string; color: string; title: string; body: string; time: string };

const SEED_NOTIFS: Notif[] = [
  { id: "n1", glyph: "◉", color: C.purple, title: "INTEL",     body: "Investigation auto-saved (3 findings).",     time: "2m"  },
  { id: "n2", glyph: "⛨", color: C.green,  title: "Shield",    body: "Local scan complete — 0 open ports outside policy.", time: "8m"  },
  { id: "n3", glyph: "◈", color: C.blue,   title: "Phantom",   body: "Daemon armed. 0 threats since boot.",        time: "14m" },
  { id: "n4", glyph: "✦", color: C.gold,   title: "GodsApp",   body: "WiFi audit module ready.",                  time: "22m" },
  { id: "n5", glyph: "✑", color: C.purple, title: "Notepad",   body: "5 notes synced to ~/.nyxus/notepad.json.",   time: "1h"  },
  { id: "n6", glyph: "◧", color: C.cyan,   title: "SysMon",    body: "CPU steady at 15% · RAM 56% · Temp 84°C.",   time: "2h"  },
];

function NotificationsCard() {
  const [items, setItems] = useLocalStorage<Notif[]>("nyxus_home_notifs", SEED_NOTIFS);
  const dismiss = (id: string) => setItems(items.filter(n => n.id !== id));
  const reset = () => setItems(SEED_NOTIFS);
  return (
    <Card tilt={1.0} color={C.green} title="Notifications" glyph="✉" footer={`${items.length} ACTIVE · LIVE FEED`}>
      <div style={{ display: "flex", flexDirection: "column", gap: 5, maxHeight: 220, overflow: "auto" }}>
        {items.length === 0 && (
          <div style={{ textAlign: "center", color: C.dim, fontSize: "0.75rem", padding: "1rem 0", fontFamily: "'Caveat', cursive" }}>
            Inbox zero · all clear
          </div>
        )}
        {items.map(n => (
          <div key={n.id} style={{
            border: `1px dashed ${n.color}33`,
            borderLeft: `3px solid ${n.color}`,
            background: `${n.color}10`,
            padding: "0.45rem 0.55rem",
            borderRadius: 3,
            display: "flex",
            gap: 6,
            alignItems: "flex-start",
          }}>
            <span style={{ color: n.color, fontSize: "0.85rem", textShadow: `0 0 6px ${n.color}88`, lineHeight: 1 }}>{n.glyph}</span>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: "flex", alignItems: "baseline", gap: 6 }}>
                <span style={{ fontFamily: "'Caveat', cursive", fontSize: "0.95rem", color: n.color, letterSpacing: "0.03em" }}>{n.title}</span>
                <span style={{ fontSize: "0.5rem", color: C.dim, marginLeft: "auto", letterSpacing: "0.1em", fontFamily: '"JetBrains Mono", monospace' }}>{n.time}</span>
              </div>
              <div style={{ fontSize: "0.6rem", color: C.dim, lineHeight: 1.4, marginTop: 1 }}>{n.body}</div>
            </div>
            <button
              onClick={() => dismiss(n.id)}
              title="Dismiss"
              style={{
                background: "transparent", border: "none",
                color: `${n.color}99`, cursor: "pointer",
                fontSize: "0.65rem", padding: "0 4px",
              }}
            >✕</button>
          </div>
        ))}
      </div>
      {items.length < SEED_NOTIFS.length && (
        <button onClick={reset} style={navBtn(C.green)}>↺ RELOAD FEED</button>
      )}
    </Card>
  );
}

// ── NOTEPAD CARD ────────────────────────────────────────────────────────
function NotepadCard() {
  const [text, setText] = useLocalStorage<string>("nyxus_home_notepad", "");
  const [savedAt, setSavedAt] = useState<number>(0);
  const tref = useRef<number | null>(null);
  useEffect(() => {
    if (tref.current) window.clearTimeout(tref.current);
    tref.current = window.setTimeout(() => setSavedAt(Date.now()), 350);
    return () => { if (tref.current) window.clearTimeout(tref.current); };
  }, [text]);
  const words = text.trim() ? text.trim().split(/\s+/).length : 0;
  const chars = text.length;
  const sinceSave = savedAt ? Math.floor((Date.now() - savedAt) / 1000) : null;
  return (
    <Card
      tilt={-0.8}
      color={C.cyan}
      title="Notepad"
      glyph="✑"
      span={2}
      footer={`AUTOSAVE · localStorage · ${chars} CHARS · ${words} WORDS${sinceSave !== null ? ` · SAVED ${sinceSave}S AGO` : ""}`}
    >
      <textarea
        value={text}
        onChange={e => setText(e.target.value)}
        placeholder="jot something down…  (autosaves)"
        spellCheck={false}
        style={{
          flex: 1,
          minHeight: 160,
          width: "100%",
          background: "rgba(0,0,0,0.45)",
          border: `1px dashed ${C.cyan}44`,
          borderRadius: 4,
          color: C.text,
          padding: "0.7rem 0.85rem",
          fontFamily: "'Caveat', cursive",
          fontSize: "1.15rem",
          letterSpacing: "0.02em",
          lineHeight: 1.55,
          resize: "vertical",
          outline: "none",
          boxShadow: `inset 0 0 12px ${C.cyan}11`,
        }}
        onFocus={e => { e.currentTarget.style.borderColor = `${C.cyan}aa`; e.currentTarget.style.boxShadow = `inset 0 0 16px ${C.cyan}22, 0 0 18px ${C.cyan}44`; }}
        onBlur ={e => { e.currentTarget.style.borderColor = `${C.cyan}44`; e.currentTarget.style.boxShadow = `inset 0 0 12px ${C.cyan}11`; }}
      />
      <div style={{ display: "flex", gap: 6 }}>
        <button onClick={() => setText("")} style={navBtn(C.cyan)} disabled={!text}>✕ CLEAR</button>
        <button
          onClick={() => {
            navigator.clipboard.writeText(text).catch(() => {});
          }}
          style={navBtn(C.cyan)}
          disabled={!text}
        >▤ COPY ALL</button>
      </div>
    </Card>
  );
}

// ── PASSWORD MANAGER CARD ───────────────────────────────────────────────
type PwEntry = { id: string; site: string; user: string; pass: string; created: number };
type GenOpts = { length: number; upper: boolean; lower: boolean; num: boolean; sym: boolean };

const ALPHABETS = {
  upper: "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
  lower: "abcdefghijklmnopqrstuvwxyz",
  num:   "0123456789",
  sym:   "!@#$%^&*()-_=+[]{};:,.<>?/~",
};

function generatePassword(opts: GenOpts): string {
  let pool = "";
  if (opts.upper) pool += ALPHABETS.upper;
  if (opts.lower) pool += ALPHABETS.lower;
  if (opts.num)   pool += ALPHABETS.num;
  if (opts.sym)   pool += ALPHABETS.sym;
  if (!pool) return "";
  const bytes = new Uint32Array(opts.length);
  if (typeof crypto !== "undefined" && crypto.getRandomValues) {
    crypto.getRandomValues(bytes);
  } else {
    for (let i = 0; i < opts.length; i++) bytes[i] = Math.floor(Math.random() * 0xffffffff);
  }
  let out = "";
  for (let i = 0; i < opts.length; i++) out += pool[bytes[i] % pool.length];
  return out;
}

function PasswordManagerCard() {
  const [entries, setEntries] = useLocalStorage<PwEntry[]>("nyxus_home_passwords", []);
  const [draft, setDraft] = useState({ site: "", user: "", pass: "" });
  const [opts, setOpts] = useLocalStorage<GenOpts>("nyxus_home_pwopts", { length: 18, upper: true, lower: true, num: true, sym: true });
  const [reveal, setReveal] = useState<Record<string, boolean>>({});
  const [genPreview, setGenPreview] = useState("");
  const [copiedId, setCopiedId] = useState<string | null>(null);

  useEffect(() => { setGenPreview(generatePassword(opts)); }, [opts]);

  const add = () => {
    if (!draft.site.trim() || !draft.user.trim() || !draft.pass) return;
    const e: PwEntry = {
      id: `${Date.now()}_${Math.floor(Math.random() * 9999)}`,
      site: draft.site.trim(),
      user: draft.user.trim(),
      pass: draft.pass,
      created: Date.now(),
    };
    setEntries([e, ...entries]);
    setDraft({ site: "", user: "", pass: "" });
  };
  const del = (id: string) => setEntries(entries.filter(e => e.id !== id));
  const copy = (text: string, id: string) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopiedId(id);
      window.setTimeout(() => setCopiedId(c => c === id ? null : c), 1200);
    }).catch(() => {});
  };

  return (
    <Card
      tilt={0.5}
      color={C.orange}
      title="Password Manager"
      glyph="⚿"
      span={3}
      footer={`${entries.length} ENTRIES · localStorage · crypto.getRandomValues · NEVER LEAVES THIS BROWSER`}
    >
      {/* generator */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "minmax(0, 1fr) auto",
        gap: 8,
        padding: "0.55rem 0.7rem",
        border: `1px dashed ${C.orange}44`,
        borderRadius: 4,
        background: `${C.orange}08`,
      }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 4, minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <span style={{ fontFamily: "'Caveat', cursive", fontSize: "0.95rem", color: C.orange }}>Generator</span>
            <span style={{ fontSize: "0.5rem", color: `${C.orange}88`, letterSpacing: "0.18em", fontFamily: '"JetBrains Mono", monospace' }}>length {opts.length}</span>
          </div>
          <input
            type="range"
            min={8}
            max={64}
            value={opts.length}
            onChange={e => setOpts({ ...opts, length: Number(e.target.value) })}
            style={{ width: "100%", accentColor: C.orange }}
          />
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, fontSize: "0.6rem", color: C.dim, fontFamily: '"JetBrains Mono", monospace' }}>
            {(["upper", "lower", "num", "sym"] as const).map(k => (
              <label key={k} style={{ display: "flex", alignItems: "center", gap: 3, cursor: "pointer", letterSpacing: "0.08em" }}>
                <input
                  type="checkbox"
                  checked={opts[k]}
                  onChange={e => setOpts({ ...opts, [k]: e.target.checked })}
                  style={{ accentColor: C.orange }}
                />
                <span>{k.toUpperCase()}</span>
              </label>
            ))}
          </div>
          <div style={{
            fontFamily: '"JetBrains Mono", monospace',
            fontSize: "0.75rem",
            color: C.text,
            background: "rgba(0,0,0,0.55)",
            padding: "5px 8px",
            border: `1px dashed ${C.orange}55`,
            borderRadius: 3,
            wordBreak: "break-all",
            letterSpacing: "0.02em",
            minHeight: 22,
          }}>
            {genPreview || <span style={{ color: C.dim }}>pick at least one option</span>}
          </div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <button onClick={() => setGenPreview(generatePassword(opts))} style={primaryBtnStyle(C.orange)}>↻ ROLL</button>
          <button onClick={() => setDraft(d => ({ ...d, pass: genPreview }))} disabled={!genPreview} style={navBtn(C.orange)}>↳ USE</button>
        </div>
      </div>

      {/* add entry */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "minmax(0, 1.2fr) minmax(0, 1.2fr) minmax(0, 1.6fr) auto",
        gap: 6,
        alignItems: "center",
      }}>
        <input value={draft.site} onChange={e => setDraft(d => ({ ...d, site: e.target.value }))} placeholder="site / app" style={inputStyle(C.orange)} />
        <input value={draft.user} onChange={e => setDraft(d => ({ ...d, user: e.target.value }))} placeholder="username / email" style={inputStyle(C.orange)} />
        <input value={draft.pass} onChange={e => setDraft(d => ({ ...d, pass: e.target.value }))} placeholder="password" style={inputStyle(C.orange)} />
        <button onClick={add} disabled={!draft.site || !draft.user || !draft.pass} style={primaryBtnStyle(C.orange)}>+ ADD</button>
      </div>

      {/* entries */}
      <div style={{ display: "flex", flexDirection: "column", gap: 4, maxHeight: 200, overflow: "auto" }}>
        {entries.length === 0 && (
          <div style={{ textAlign: "center", color: C.dim, fontSize: "0.85rem", padding: "0.6rem 0", fontFamily: "'Caveat', cursive" }}>
            no entries yet — add one above or generate a password
          </div>
        )}
        {entries.map(e => {
          const shown = reveal[e.id];
          const id = e.id;
          return (
            <div key={id} style={{
              display: "grid",
              gridTemplateColumns: "minmax(0,1fr) minmax(0,1fr) minmax(0,1.4fr) auto auto auto",
              gap: 6,
              alignItems: "center",
              padding: "0.4rem 0.55rem",
              border: `1px dashed ${C.orange}33`,
              borderRadius: 3,
              background: "rgba(0,0,0,0.35)",
              fontFamily: '"JetBrains Mono", monospace',
              fontSize: "0.7rem",
              color: C.text,
            }}>
              <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", color: C.orange, letterSpacing: "0.04em" }} title={e.site}>{e.site}</span>
              <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", color: C.dim }} title={e.user}>{e.user}</span>
              <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", color: shown ? C.text : C.dim }} title={shown ? e.pass : "•".repeat(e.pass.length)}>
                {shown ? e.pass : "•".repeat(Math.min(e.pass.length, 18))}
              </span>
              <button
                onClick={() => setReveal(r => ({ ...r, [id]: !r[id] }))}
                title={shown ? "Hide" : "Reveal"}
                style={iconBtn(C.orange)}
              >{shown ? "◐" : "◯"}</button>
              <button
                onClick={() => copy(e.pass, id)}
                title="Copy password"
                style={iconBtn(copiedId === id ? C.green : C.orange)}
              >{copiedId === id ? "✓" : "▤"}</button>
              <button
                onClick={() => del(id)}
                title="Delete"
                style={iconBtn(C.red)}
              >✕</button>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

// ── SHARED INPUT/BUTTON STYLES ──────────────────────────────────────────
function inputStyle(color: string): React.CSSProperties {
  return {
    background: "rgba(0,0,0,0.45)",
    border: `1px dashed ${color}55`,
    borderRadius: 3,
    color: C.text,
    padding: "5px 8px",
    fontFamily: '"JetBrains Mono", monospace',
    fontSize: "0.7rem",
    outline: "none",
    minWidth: 0,
    width: "100%",
  };
}
function primaryBtnStyle(color: string): React.CSSProperties {
  return {
    background: `${color}22`,
    border: `1px solid ${color}`,
    color,
    fontFamily: '"JetBrains Mono", monospace',
    fontSize: "0.6rem",
    letterSpacing: "0.18em",
    padding: "5px 10px",
    borderRadius: 3,
    cursor: "pointer",
    fontWeight: 700,
    textShadow: `0 0 6px ${color}88`,
    whiteSpace: "nowrap",
  };
}
function navBtn(color: string): React.CSSProperties {
  return {
    background: "transparent",
    border: `1px solid ${color}55`,
    color,
    fontFamily: '"JetBrains Mono", monospace',
    fontSize: "0.55rem",
    letterSpacing: "0.18em",
    padding: "3px 8px",
    borderRadius: 2,
    cursor: "pointer",
    whiteSpace: "nowrap",
  };
}
function iconBtn(color: string): React.CSSProperties {
  return {
    background: "transparent",
    border: `1px solid ${color}55`,
    color,
    fontSize: "0.7rem",
    padding: "2px 6px",
    borderRadius: 2,
    cursor: "pointer",
    lineHeight: 1,
  };
}

// ── DASHBOARD COMPOSITION ───────────────────────────────────────────────
export default function HomeDashboard() {
  return (
    <div style={{
      position: "absolute",
      inset: 0,
      overflow: "auto",
      padding: "0.85rem 1rem",
    }}>
      {/* graffiti spatter behind everything */}
      <GraffitiLayer />

      {/* header strip */}
      <div style={{
        position: "relative",
        zIndex: 1,
        display: "flex",
        alignItems: "baseline",
        justifyContent: "space-between",
        marginBottom: "0.85rem",
        padding: "0 0.25rem",
      }}>
        <div>
          <div style={{
            fontSize: "0.55rem",
            color: `${C.pink}aa`,
            letterSpacing: "0.28em",
            fontFamily: '"JetBrains Mono", monospace',
          }}>
            NYXUS · WORKSPACE 0 · HOME
          </div>
          <div style={{
            fontFamily: "'Caveat', cursive",
            fontSize: "1.85rem",
            color: C.text,
            letterSpacing: "0.02em",
            textShadow: `0 0 14px ${C.pink}66, 0 0 28px ${C.purple}33`,
            lineHeight: 1.05,
          }}>
            <span style={{ color: C.pink }}>welcome</span> back, <span style={{ color: C.gold }}>operator</span>
          </div>
        </div>
        <div style={{
          fontSize: "0.5rem",
          color: "#444",
          letterSpacing: "0.22em",
          fontFamily: '"JetBrains Mono", monospace',
          textAlign: "right",
        }}>
          NYX-J5W-2026<br />SIERENGOWSKI-LOCKED
        </div>
      </div>

      {/* widgets grid */}
      <div style={{
        position: "relative",
        zIndex: 1,
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
        gridAutoRows: "minmax(0, auto)",
        gap: 14,
        paddingBottom: "1rem",
      }}>
        <ClockCard />
        <WeatherCard />
        <NotificationsCard />
        <CalendarCard />
        <NotepadCard />
        <PasswordManagerCard />
      </div>
    </div>
  );
}
