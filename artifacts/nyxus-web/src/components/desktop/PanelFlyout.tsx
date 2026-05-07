import { C, useTime } from "./shared";

export function PanelFlyout({ open, onClose }: { open: boolean; onClose: () => void }) {
  const time = useTime();
  if (!open) return null;
  return (
    <div style={{
      position: "fixed",
      top: 32, bottom: 32, right: 46,
      width: 320,
      background: "rgba(6,4,12,0.55)",
      backdropFilter: "blur(14px) saturate(1.6)",
      WebkitBackdropFilter: "blur(14px) saturate(1.6)",
      border: `1px solid ${C.purple}66`,
      borderTop: `2px solid ${C.purple}`,
      borderRadius: 6,
      boxShadow: `0 0 40px ${C.purple}66`,
      padding: "1rem 1.1rem",
      display: "flex", flexDirection: "column", gap: "0.85rem",
      zIndex: 80,
      fontFamily: '"JetBrains Mono", monospace',
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <div>
          <div style={{ fontSize: "0.5rem", color: `${C.purple}aa`, letterSpacing: "0.22em" }}>NYXUS · PANEL</div>
          <div style={{ fontSize: "1.1rem", color: C.purple, fontFamily: "'Caveat', cursive", textShadow: `0 0 10px ${C.purple}55` }}>The Panel</div>
        </div>
        <button onClick={onClose} style={{ background: "transparent", border: `1px solid ${C.red}66`, color: C.red, padding: "2px 8px", fontSize: "0.6rem", cursor: "pointer", borderRadius: 2 }}>✕</button>
      </div>

      <div style={{ border: `1px solid ${C.gold}44`, borderLeft: `3px solid ${C.gold}`, borderRadius: 3, padding: "0.75rem 0.85rem", background: "rgba(255,255,0,0.04)" }}>
        <div style={{ fontSize: "0.55rem", color: `${C.gold}aa`, letterSpacing: "0.18em" }}>WEATHER</div>
        <div style={{ display: "flex", alignItems: "baseline", gap: 8, marginTop: 4 }}>
          <div style={{ fontSize: "1.6rem", color: C.gold, textShadow: `0 0 12px ${C.gold}66`, fontFamily: "'Caveat', cursive" }}>72°F</div>
          <div style={{ fontSize: "0.65rem", color: C.dim }}>Clear · Light breeze</div>
        </div>
      </div>

      <div style={{ border: `1px solid ${C.cyan}44`, borderLeft: `3px solid ${C.cyan}`, borderRadius: 3, padding: "0.75rem 0.85rem", background: "rgba(34,211,238,0.04)" }}>
        <div style={{ fontSize: "0.55rem", color: `${C.cyan}aa`, letterSpacing: "0.18em" }}>NEWS</div>
        <div style={{ fontSize: "0.7rem", color: C.text, marginTop: 4, lineHeight: 1.5 }}>
          NYXUS v2.0 ships with 8 tarball apps and 4-bar Waybar
        </div>
      </div>

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
