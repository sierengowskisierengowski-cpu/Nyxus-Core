import { C } from "./shared";

function Stat({ glyph, value, color }: { glyph: string; value: string; color: string }) {
  return (
    <span style={{
      display: "inline-flex",
      alignItems: "center",
      gap: 4,
      color,
      fontSize: "0.62rem",
      fontFamily: '"JetBrains Mono", monospace',
      letterSpacing: "0.05em",
      textShadow: `0 0 4px ${color}88`,
      whiteSpace: "nowrap",
    }}>
      <span style={{ fontSize: "0.7rem" }}>{glyph}</span>
      <span style={{ color: C.text }}>{value}</span>
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
      position: "fixed",
      top: 6, left: 6, right: 6,
      height: 22,
      background: C.panelBg,
      border: `1px solid ${C.pink}`,
      borderRadius: 4,
      boxShadow: `0 0 10px ${C.pink}66, 0 0 20px ${C.pink}33, inset 0 0 10px rgba(255,0,255,0.06)`,
      display: "flex",
      alignItems: "center",
      padding: "0 8px",
      fontFamily: '"JetBrains Mono", monospace',
      zIndex: 50,
      userSelect: "none",
      backdropFilter: "blur(14px) saturate(1.6)",
    }}>
      <div style={{ flex: 1, display: "flex", alignItems: "center", gap: 12, overflow: "hidden" }}>
        <Stat glyph="◉" value="CPU 15%"      color={C.purple} />
        <Stat glyph="▲" value="TEMP 84°C"    color={C.orange} />
        <Stat glyph="↓" value="0KB/s"        color={C.green} />
        <Stat glyph="↑" value="0KB/s"        color={C.green} />
        <Stat glyph="⊘" value="NO-WIFI"      color={C.red} />
        <Stat glyph="▣" value="92%"          color={C.gold} />
        <Stat glyph="◧" value="DISK 35%"     color={C.cyan} />
      </div>
      <div style={{ flex: "0 0 auto", padding: "0 1.2rem", fontWeight: 800, letterSpacing: "0.18em", fontSize: "0.7rem" }}>
        <span style={{ color: C.pink   }}>N</span>
        <span style={{ color: C.orange }}> Y</span>
        <span style={{ color: C.gold   }}> X</span>
        <span style={{ color: C.green  }}> U</span>
        <span style={{ color: C.blue   }}> S</span>
      </div>
      <div style={{ flex: 1, display: "flex", justifyContent: "flex-end", alignItems: "center", gap: 10, color: C.text, fontSize: "0.62rem" }}>
        <span style={{ color: C.dim }}>{date}</span>
        <span style={{ color: C.cyan, fontSize: "0.65rem" }}>▢</span>
        <span style={{ fontWeight: 700, color: C.text }}>{hh}:{mm}:{ss}</span>
      </div>
    </div>
  );
}
