import { C, FRAME } from "./shared";

export function LeftBar({ activeWs, onSelect }: { activeWs: number; onSelect: (n: number) => void }) {
  return (
    <div style={{
      ...FRAME,
      position: "fixed",
      top: 34, left: 6, bottom: 34,
      width: 36,
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      padding: "10px 0",
      gap: 8,
      zIndex: 50,
      userSelect: "none",
    }}>
      {Array.from({ length: 9 }).map((_, i) => {
        const n = i + 1;
        const active = n === activeWs;
        return (
          <button
            key={n}
            onClick={() => onSelect(n)}
            title={`Workspace ${n}`}
            style={{
              width: 22, height: 22,
              borderRadius: "50%",
              background: active ? C.white : C.glassDeeper,
              border: `1px solid ${active ? C.white : C.hairlineHi}`,
              boxShadow: active
                ? `0 0 8px rgba(255,255,255,0.45), inset 0 0 0 2px ${C.glassDark}`
                : `inset 0 0 0 1px rgba(0,0,0,0.35)`,
              color: active ? C.void : C.textSecondary,
              fontSize: "0.6rem",
              fontWeight: 700,
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
          width: 24, height: 24,
          borderRadius: 6,
          background: C.glassDeeper,
          border: `1px solid ${C.hairline}`,
          color: C.textSecondary,
          fontSize: "0.85rem",
          cursor: "pointer",
          padding: 0,
          display: "flex", alignItems: "center", justifyContent: "center",
        }}
      >⏻</button>
    </div>
  );
}
