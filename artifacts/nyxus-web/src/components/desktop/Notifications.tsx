import { C } from "./shared";

export function Notifications({ open, onClose }: { open: boolean; onClose: () => void }) {
  if (!open) return null;
  const items = [
    { glyph: "◉", title: "INTEL",     body: "Investigation auto-saved (3 findings)." },
    { glyph: "⛨", title: "Shield",    body: "Local scan complete — 0 open ports outside policy." },
    { glyph: "◈", title: "Phantom",   body: "Daemon armed. 0 threats since boot." },
    { glyph: "✦", title: "GodsApp",   body: "WiFi audit module ready." },
    { glyph: "✑", title: "Notepad",   body: "5 notes synced to ~/.nyxus/notepad.json." },
    { glyph: "⚙", title: "Settings",  body: "DARK MIRROR rev r16 — chrome refreshed." },
  ];
  return (
    <div onClick={onClose} style={{ position: "fixed", inset: 0, zIndex: 85 }}>
      <div
        onClick={e => e.stopPropagation()}
        style={{
          position: "absolute",
          bottom: 38, right: 14,
          width: 340,
          background: C.glassDark,
          backdropFilter: "blur(14px) saturate(1.1)",
          WebkitBackdropFilter: "blur(14px) saturate(1.1)",
          border: `1px solid ${C.hairline}`,
          borderRadius: 14,
          padding: "0.95rem 1rem",
          display: "flex", flexDirection: "column", gap: 7,
          fontFamily: '"Inter", sans-serif',
          boxShadow: `0 20px 60px ${C.rimDark}`,
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 4 }}>
          <div style={{
            fontSize: "0.55rem",
            color: C.textTertiary,
            letterSpacing: "0.22em",
            fontFamily: '"JetBrains Mono", monospace',
          }}>NYXUS · NOTIFICATIONS</div>
          <button onClick={onClose} style={{
            background: "transparent",
            border: `1px solid ${C.hairline}`,
            color: C.textSecondary,
            padding: "1px 7px",
            fontSize: "0.55rem",
            cursor: "pointer",
            borderRadius: 6,
            fontFamily: '"JetBrains Mono", monospace',
          }}>✕</button>
        </div>
        {items.map((n, i) => (
          <div key={i} style={{
            background: C.glassDeeper,
            border: `1px solid ${C.hairline}`,
            padding: "0.55rem 0.7rem",
            borderRadius: 10,
            display: "flex", gap: 9, alignItems: "flex-start",
          }}>
            <span style={{ color: C.textPrimary, fontSize: "0.85rem" }}>{n.glyph}</span>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{
                fontSize: "0.78rem",
                color: C.textPrimary,
                fontFamily: '"Inter", sans-serif',
                letterSpacing: "0.02em",
                fontWeight: 600,
              }}>{n.title}</div>
              <div style={{ fontSize: "0.65rem", color: C.textSecondary, lineHeight: 1.5, marginTop: 2 }}>{n.body}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
