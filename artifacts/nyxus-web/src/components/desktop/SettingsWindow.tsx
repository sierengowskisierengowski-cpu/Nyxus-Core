import { useState } from "react";
import { C } from "./shared";

export function SettingsWindow({ open, onClose }: { open: boolean; onClose: () => void }) {
  const sections = [
    { id: "appearance",    label: "Appearance",    glyph: "◐" },
    { id: "profile",       label: "Profile",       glyph: "✦" },
    { id: "notifications", label: "Notifications", glyph: "✉" },
    { id: "news",          label: "News Sources",  glyph: "▦" },
    { id: "filters",       label: "Filters",       glyph: "⊘" },
    { id: "browser",       label: "Browser",       glyph: "◍" },
    { id: "cache",         label: "Cache",         glyph: "◧" },
    { id: "about",         label: "About",         glyph: "ⓘ" },
  ];
  const [active, setActive] = useState("appearance");
  if (!open) return null;
  const sec = sections.find(s => s.id === active)!;

  const renderBody = () => {
    switch (active) {
      case "appearance":
        return (
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <Row label="Theme"        value="DARK MIRROR · rev r16 (locked)" />
            <Row label="Wallpaper"    value="nyxus-ink-swirl.png · rotation on (15s)" />
            <Row label="Blur"         value="size 14 · 4 passes · brightness 0.92" />
            <Row label="Window opacity" value="0.92 focused / 0.78 unfocused" />
            <Row label="Border"       value="Hyprland rim-light gradient (white → off-white → black)" />
          </div>
        );
      case "profile":
        return (
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <Row label="User"      value="jsierengowski" />
            <Row label="Hostname"  value="nyxus" />
            <Row label="ISO"       value="nyx-2026.05.02-x86_64.iso" />
            <Row label="OS"        value="NYXUS · Arch + Hyprland" />
            <Row label="License"   value="NYX-J5W-2026-SIERENGOWSKI-LOCKED" />
          </div>
        );
      case "notifications":
        return (
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <Row label="Daemon"     value="Dunst (system-wide)" />
            <Row label="Position"   value="Top-right · 6px gutter" />
            <Row label="Timeout"    value="6s default · 0 for critical" />
            <Row label="Do Not Disturb" value="off" />
          </div>
        );
      case "news":
        return (
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <Row label="Sources"    value="Hacker News · Lobsters · Phoronix" />
            <Row label="Refresh"    value="every 5 min" />
            <Row label="Ticker"     value="bottom waybar · scroll left → right" />
          </div>
        );
      case "filters":
        return <Row label="Content filters" value="standard ruleset · 14 rules active" />;
      case "browser":
        return <Row label="Default browser" value="firefox-developer-edition" />;
      case "cache":
        return (
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <Row label="Cache size"  value="34 MB · ~/.cache/nyxus/" />
            <Row label="Last purge"  value="2 hours ago" />
          </div>
        );
      case "about":
        return (
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <Row label="NYXUS"     value="rev r16 · DARK MIRROR (LOCKED)" />
            <Row label="Apps"      value="26 installed (3 live + 11 tarball + 12 system)" />
            <Row label="Creator"   value="Joseph Sierengowski" />
            <Row label="Source"    value="github.com/sierengowskisierengowski-cpu/Nyxus-Core" />
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed", inset: 0,
        background: "rgba(0,0,0,0.55)",
        backdropFilter: "blur(8px)",
        zIndex: 90,
        display: "flex", alignItems: "center", justifyContent: "center",
        padding: 50,
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          width: "100%", maxWidth: 760,
          height: "100%", maxHeight: 520,
          background: C.glassDark,
          backdropFilter: "blur(14px) saturate(1.1)",
          WebkitBackdropFilter: "blur(14px) saturate(1.1)",
          border: `1px solid ${C.hairline}`,
          borderRadius: 14,
          boxShadow: `0 20px 60px ${C.rimDark}`,
          display: "grid",
          gridTemplateColumns: "200px 1fr",
          fontFamily: '"Inter", sans-serif',
          overflow: "hidden",
        }}
      >
        {/* sidebar */}
        <div style={{
          background: C.glassDeeper,
          borderRight: `1px solid ${C.hairline}`,
          padding: "0.9rem 0.55rem",
          display: "flex",
          flexDirection: "column",
          gap: 3,
        }}>
          <div style={{
            fontSize: "0.55rem",
            color: C.textTertiary,
            letterSpacing: "0.22em",
            padding: "0.35rem 0.55rem",
            marginBottom: 6,
            fontFamily: '"JetBrains Mono", monospace',
          }}>SETTINGS</div>
          {sections.map(s => {
            const isActive = s.id === active;
            return (
              <button
                key={s.id}
                onClick={() => setActive(s.id)}
                style={{
                  width: "100%",
                  textAlign: "left",
                  background: isActive ? C.glassDeepest : "transparent",
                  border: `1px solid ${isActive ? C.hairlineHi : "transparent"}`,
                  color: isActive ? C.white : C.textSecondary,
                  padding: "6px 10px",
                  borderRadius: 8,
                  fontSize: "0.75rem",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  fontFamily: '"Inter", sans-serif',
                  transition: "all 0.12s",
                }}
                onMouseEnter={e => { e.currentTarget.style.color = C.white; }}
                onMouseLeave={e => { e.currentTarget.style.color = isActive ? C.white : C.textSecondary; }}
              >
                <span style={{ width: 14, textAlign: "center" }}>{s.glyph}</span>
                {s.label}
              </button>
            );
          })}

          <div style={{ flex: 1 }} />
          <button onClick={onClose} style={{
            background: "transparent",
            border: `1px solid ${C.hairline}`,
            color: C.textSecondary,
            padding: "5px 10px",
            fontSize: "0.65rem",
            cursor: "pointer",
            borderRadius: 6,
            letterSpacing: "0.15em",
            fontFamily: '"JetBrains Mono", monospace',
          }}>✕ CLOSE</button>
        </div>

        {/* body */}
        <div style={{ padding: "1.4rem 1.6rem", overflowY: "auto" }}>
          <div style={{
            fontSize: "0.55rem",
            color: C.textTertiary,
            letterSpacing: "0.22em",
            fontFamily: '"JetBrains Mono", monospace',
          }}>NYXUS · {sec.label.toUpperCase()}</div>
          <div style={{
            fontSize: "1.4rem",
            color: C.textPrimary,
            fontFamily: '"Architects Daughter", "Caveat", cursive',
            marginBottom: "1.2rem",
            marginTop: 2,
          }}>{sec.label}</div>

          {renderBody()}
        </div>
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div style={{
      display: "flex",
      justifyContent: "space-between",
      gap: 16,
      padding: "9px 12px",
      background: C.glassDeeper,
      border: `1px solid ${C.hairline}`,
      borderRadius: 10,
      fontSize: "0.75rem",
    }}>
      <span style={{ color: C.textTertiary, letterSpacing: "0.04em" }}>{label}</span>
      <span style={{ color: C.textPrimary, textAlign: "right" }}>{value}</span>
    </div>
  );
}
