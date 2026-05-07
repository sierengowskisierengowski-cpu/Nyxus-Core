import { C, FRAME } from "./shared";

function Stat({ glyph, value }: { glyph: string; value: string }) {
  return (
    <span style={{
      display: "inline-flex",
      alignItems: "center",
      gap: 5,
      color: C.textSecondary,
      fontSize: "0.62rem",
      fontFamily: '"JetBrains Mono", monospace',
      letterSpacing: "0.05em",
      whiteSpace: "nowrap",
    }}>
      <span style={{ fontSize: "0.7rem", color: C.textTertiary }}>{glyph}</span>
      <span style={{ color: C.textPrimary }}>{value}</span>
    </span>
  );
}

export function TopBar({ time }: { time: Date }) {
  const hh = String(time.getHours()).padStart(2, "0");
  const mm = String(time.getMinutes()).padStart(2, "0");
  const ss = String(time.getSeconds()).padStart(2, "0");
  const date = time.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });

  return (
    <div style={{
      ...FRAME,
      position: "fixed",
      top: 6, left: 6, right: 6,
      height: 24,
      display: "flex",
      alignItems: "center",
      padding: "0 10px",
      fontFamily: '"JetBrains Mono", monospace',
      zIndex: 50,
      userSelect: "none",
    }}>
      <div style={{ flex: 1, display: "flex", alignItems: "center", gap: 14, overflow: "hidden" }}>
        <Stat glyph="◉" value="CPU 15%"   />
        <Stat glyph="▲" value="84°C"      />
        <Stat glyph="↓" value="0KB/s"     />
        <Stat glyph="↑" value="0KB/s"     />
        <Stat glyph="⊘" value="NO-WIFI"   />
        <Stat glyph="▣" value="92%"       />
        <Stat glyph="◧" value="DISK 35%"  />
      </div>
      <div style={{
        flex: "0 0 auto",
        padding: "0 1.2rem",
        fontWeight: 700,
        letterSpacing: "0.32em",
        fontSize: "0.7rem",
        color: C.textPrimary,
        fontFamily: '"Architects Daughter", "Caveat", cursive',
      }}>
        N Y X U S
      </div>
      <div style={{ flex: 1, display: "flex", justifyContent: "flex-end", alignItems: "center", gap: 12, fontSize: "0.62rem" }}>
        <span style={{ color: C.textTertiary }}>{date}</span>
        <span style={{ color: C.textSecondary }}>▢</span>
        <span style={{ fontWeight: 700, color: C.textPrimary }}>{hh}:{mm}:{ss}</span>
      </div>
    </div>
  );
}
