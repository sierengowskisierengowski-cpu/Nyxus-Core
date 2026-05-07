import { C, NEONS } from "./shared";

export function LeftBar({ activeWs, onSelect }: { activeWs: number; onSelect: (n: number) => void }) {
  return (
    <div style={{
      position: "fixed",
      top: 32, left: 6, bottom: 32,
      width: 32,
      background: C.panelBg,
      border: `1px solid ${C.pink}`,
      borderRadius: 4,
      boxShadow: `0 0 10px ${C.pink}66, 0 0 20px ${C.pink}33`,
      backdropFilter: "blur(14px) saturate(1.6)",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      padding: "8px 0",
      gap: 7,
      zIndex: 50,
      userSelect: "none",
    }}>
      {Array.from({ length: 9 }).map((_, i) => {
        const n = i + 1;
        const color = NEONS[i];
        const active = n === activeWs;
        return (
          <button
            key={n}
            onClick={() => onSelect(n)}
            title={`Workspace ${n}`}
            style={{
              width: 20, height: 20,
              borderRadius: "50%",
              background: active
                ? `radial-gradient(circle at 35% 35%, ${color}, ${color}66 70%, transparent)`
                : `radial-gradient(circle at 35% 35%, ${color}cc, ${color}44 70%, transparent)`,
              border: `1.5px solid ${color}`,
              boxShadow: active
                ? `0 0 12px ${color}, 0 0 24px ${color}88, inset 0 0 4px rgba(255,255,255,0.4)`
                : `0 0 6px ${color}88, inset 0 0 3px rgba(255,255,255,0.2)`,
              color: "#0a0612",
              fontSize: "0.6rem",
              fontWeight: 900,
              fontFamily: '"JetBrains Mono", monospace',
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              padding: 0,
              transition: "all 0.15s",
            }}
          >
            {n}
          </button>
        );
      })}
      <div style={{ flex: 1 }} />
      <button
        title="Power"
        style={{
          width: 22, height: 22,
          borderRadius: 4,
          background: `${C.red}22`,
          border: `1px solid ${C.red}`,
          color: C.red,
          fontSize: "0.85rem",
          cursor: "pointer",
          textShadow: `0 0 6px ${C.red}`,
          padding: 0,
          display: "flex", alignItems: "center", justifyContent: "center",
        }}
      >⏻</button>
    </div>
  );
}
