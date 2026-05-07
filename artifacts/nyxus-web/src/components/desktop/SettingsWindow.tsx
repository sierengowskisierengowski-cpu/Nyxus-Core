import { useState } from "react";
import { C } from "./shared";

export function SettingsWindow({ open, onClose }: { open: boolean; onClose: () => void }) {
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
        background: "rgba(6,4,12,0.72)",
        backdropFilter: "blur(14px) saturate(1.6)",
        WebkitBackdropFilter: "blur(14px) saturate(1.6)",
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
          background: "rgba(6,4,12,0.55)",
          backdropFilter: "blur(14px) saturate(1.6)",
          WebkitBackdropFilter: "blur(14px) saturate(1.6)",
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
        <div style={{ background: "rgba(6,4,12,0.55)", backdropFilter: "blur(14px) saturate(1.6)", WebkitBackdropFilter: "blur(14px) saturate(1.6)", borderRight: `1px solid ${sec.color}22`, padding: "0.85rem 0.5rem" }}>
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
