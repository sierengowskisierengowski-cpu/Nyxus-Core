import { C, NEONS } from "./shared";

export function BottomBar({ activeWs, onSelectWs, onStart, onHome, onSettings, onPanel, onNotif, time }: {
  activeWs: number;
  onSelectWs: (n: number) => void;
  onStart: () => void;
  onHome: () => void;
  onSettings: () => void;
  onPanel: () => void;
  onNotif: () => void;
  time: Date;
}) {
  const hh = String(time.getHours()).padStart(2, "0");
  const mm = String(time.getMinutes()).padStart(2, "0");
  const ss = String(time.getSeconds()).padStart(2, "0");
  return (
    <div style={{
      position: "fixed",
      bottom: 6, left: 6, right: 6,
      height: 24,
      background: C.panelBg,
      border: `1px solid ${C.pink}`,
      borderRadius: 4,
      boxShadow: `0 0 10px ${C.pink}66, 0 0 20px ${C.pink}33`,
      backdropFilter: "blur(14px) saturate(1.6)",
      display: "flex",
      alignItems: "center",
      padding: "0 8px",
      gap: 8,
      zIndex: 50,
      userSelect: "none",
      fontFamily: '"JetBrains Mono", monospace',
    }}>
      {/* Start button */}
      <button
        onClick={onStart}
        style={{
          background: "transparent",
          border: "none",
          color: C.cyan,
          fontSize: "0.72rem",
          letterSpacing: "0.06em",
          fontWeight: 700,
          cursor: "pointer",
          padding: "1px 8px",
          textShadow: `0 0 6px ${C.cyan}88`,
          fontFamily: "'Caveat', cursive",
        }}
        onMouseEnter={e => { e.currentTarget.style.color = C.pink; }}
        onMouseLeave={e => { e.currentTarget.style.color = C.cyan; }}
      >
        Start
      </button>

      {/* Home button (workspace 0 — dashboard) */}
      <button
        onClick={onHome}
        title="Home dashboard (workspace 0)"
        style={{
          background: activeWs === 0 ? `${C.pink}22` : "transparent",
          border: activeWs === 0 ? `1px solid ${C.pink}88` : "1px solid transparent",
          color: activeWs === 0 ? C.pink : C.gold,
          fontSize: "0.72rem",
          letterSpacing: "0.04em",
          fontWeight: 700,
          cursor: "pointer",
          padding: "0px 8px",
          textShadow: `0 0 6px ${activeWs === 0 ? C.pink : C.gold}88`,
          fontFamily: "'Caveat', cursive",
          borderRadius: 3,
          display: "flex",
          alignItems: "center",
          gap: 4,
        }}
        onMouseEnter={e => { if (activeWs !== 0) e.currentTarget.style.color = C.pink; }}
        onMouseLeave={e => { if (activeWs !== 0) e.currentTarget.style.color = C.gold; }}
      >
        <span style={{ fontSize: "0.8rem", lineHeight: 1 }}>⌂</span> Home
      </button>

      {/* center: workspace pager */}
      <div style={{ flex: 1, display: "flex", justifyContent: "center", alignItems: "center", gap: 6 }}>
        {Array.from({ length: 6 }).map((_, i) => {
          const n = i + 1;
          const color = NEONS[i];
          const active = n === activeWs;
          return (
            <button
              key={n}
              onClick={() => onSelectWs(n)}
              title={`Workspace ${n}`}
              style={{
                width: 16, height: 16,
                borderRadius: "50%",
                background: active
                  ? `radial-gradient(circle at 35% 35%, ${color}, ${color}66 70%)`
                  : `radial-gradient(circle at 35% 35%, ${color}aa, ${color}33 70%)`,
                border: `1.2px solid ${color}`,
                boxShadow: active
                  ? `0 0 8px ${color}, 0 0 16px ${color}88`
                  : `0 0 4px ${color}66`,
                color: "#0a0612",
                fontSize: "0.5rem",
                fontWeight: 900,
                cursor: "pointer",
                padding: 0,
                display: "flex", alignItems: "center", justifyContent: "center",
              }}
            >
              {n}
            </button>
          );
        })}
      </div>

      {/* right cluster: gear time | The Panel | Notifications */}
      <button
        onClick={onSettings}
        title="Settings"
        style={{
          background: "transparent", border: "none",
          color: C.gold, fontSize: "0.85rem",
          cursor: "pointer", padding: "0 4px",
          textShadow: `0 0 6px ${C.gold}88`,
        }}
      >⚙&#xFE0E;</button>
      <span style={{ color: C.text, fontSize: "0.65rem", fontWeight: 700, letterSpacing: "0.04em" }}>
        {hh}:{mm}:{ss}
      </span>
      <button
        onClick={onPanel}
        style={{
          background: "transparent", border: "none",
          color: C.purple, fontSize: "0.72rem",
          letterSpacing: "0.04em", fontWeight: 700, cursor: "pointer",
          padding: "1px 8px", textShadow: `0 0 6px ${C.purple}88`,
          fontFamily: "'Caveat', cursive",
        }}
        onMouseEnter={e => { e.currentTarget.style.color = C.pink; }}
        onMouseLeave={e => { e.currentTarget.style.color = C.purple; }}
      >
        The Panel
      </button>
      <button
        onClick={onNotif}
        style={{
          background: "transparent", border: "none",
          color: C.green, fontSize: "0.72rem",
          letterSpacing: "0.04em", fontWeight: 700, cursor: "pointer",
          padding: "1px 8px", textShadow: `0 0 6px ${C.green}88`,
          fontFamily: "'Caveat', cursive",
        }}
        onMouseEnter={e => { e.currentTarget.style.color = C.cyan; }}
        onMouseLeave={e => { e.currentTarget.style.color = C.green; }}
      >
        Notifications
      </button>
    </div>
  );
}
