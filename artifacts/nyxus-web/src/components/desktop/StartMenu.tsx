import { C, APPS, AppDef } from "./shared";

export function StartMenu({ open, onClose, onLaunch }: { open: boolean; onClose: () => void; onLaunch: (a: AppDef) => void }) {
  if (!open) return null;
  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.7)",
        backdropFilter: "blur(14px) saturate(1.6)",
        zIndex: 90,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "60px 40px",
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          width: "100%", maxWidth: 820, maxHeight: "100%",
          background: "rgba(8,6,16,0.97)",
          border: `1px solid ${C.cyan}66`,
          borderTop: `2px solid ${C.cyan}`,
          borderRadius: 8,
          boxShadow: `0 0 60px ${C.cyan}55`,
          padding: "1.5rem 1.75rem",
          display: "flex", flexDirection: "column", gap: "1rem",
          fontFamily: '"JetBrains Mono", monospace',
          overflow: "auto",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
          <div>
            <div style={{ fontSize: "0.55rem", color: `${C.cyan}aa`, letterSpacing: "0.22em" }}>NYXUS · START</div>
            <div style={{ fontSize: "1.4rem", color: C.cyan, fontFamily: "'Caveat', cursive", textShadow: `0 0 10px ${C.cyan}55` }}>All apps</div>
          </div>
          <button onClick={onClose} style={{ background: "transparent", border: `1px solid ${C.red}66`, color: C.red, padding: "3px 10px", fontSize: "0.65rem", cursor: "pointer", borderRadius: 2, letterSpacing: "0.15em" }}>✕ CLOSE</button>
        </div>

        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(120px, 1fr))",
          gap: 10,
        }}>
          {APPS.map(a => (
            <button
              key={a.id}
              onClick={() => { onLaunch(a); onClose(); }}
              style={{
                display: "flex", flexDirection: "column",
                alignItems: "center", gap: 6,
                padding: "0.8rem 0.6rem",
                background: "rgba(0,0,0,0.4)",
                border: `1px solid ${a.color}44`,
                borderTop: `2px solid ${a.color}`,
                borderRadius: 4,
                cursor: "pointer",
                color: a.color,
                transition: "all 0.15s",
              }}
              onMouseEnter={e => { e.currentTarget.style.background = `${a.color}1a`; }}
              onMouseLeave={e => { e.currentTarget.style.background = "rgba(0,0,0,0.4)"; }}
            >
              <div style={{ fontSize: "1.6rem", color: a.color, textShadow: `0 0 12px ${a.color}` }}>{a.glyph}</div>
              <div style={{ fontSize: "0.85rem", fontFamily: "'Caveat', cursive", letterSpacing: "0.04em", color: a.color }}>
                {a.name}
              </div>
              <div style={{ fontSize: "0.45rem", color: C.dim, letterSpacing: "0.1em" }}>
                {a.kind === "iframe" ? "LIVE" : "MOCKUP"}
              </div>
            </button>
          ))}
        </div>

        <div style={{ borderTop: `1px solid ${C.cyan}22`, paddingTop: "0.75rem", display: "flex", justifyContent: "space-between", fontSize: "0.55rem", color: "#555", letterSpacing: "0.18em" }}>
          <span>{APPS.length} APPS</span>
          <span>NYX-J5W-2026-SIERENGOWSKI-LOCKED</span>
        </div>
      </div>
    </div>
  );
}
