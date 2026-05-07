import { C } from "./shared";

export function Notifications({ open, onClose }: { open: boolean; onClose: () => void }) {
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
          background: "rgba(6,4,12,0.55)",
          backdropFilter: "blur(14px) saturate(1.6)",
          WebkitBackdropFilter: "blur(14px) saturate(1.6)",
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
