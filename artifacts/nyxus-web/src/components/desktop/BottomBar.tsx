import { C, FRAME } from "./shared";

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

  const navBtn = (label: string, onClick: () => void, isActive = false) => (
    <button
      onClick={onClick}
      style={{
        background: isActive ? C.glassDeeper : "transparent",
        border: `1px solid ${isActive ? C.hairlineHi : "transparent"}`,
        color: isActive ? C.white : C.textSecondary,
        fontSize: "0.7rem",
        letterSpacing: "0.06em",
        fontWeight: 500,
        cursor: "pointer",
        padding: "2px 10px",
        borderRadius: 8,
        fontFamily: '"Inter", sans-serif',
        transition: "all 0.12s",
      }}
      onMouseEnter={e => { e.currentTarget.style.color = C.white; }}
      onMouseLeave={e => { e.currentTarget.style.color = isActive ? C.white : C.textSecondary; }}
    >
      {label}
    </button>
  );

  return (
    <div style={{
      ...FRAME,
      position: "fixed",
      bottom: 6, left: 6, right: 6,
      height: 26,
      display: "flex",
      alignItems: "center",
      padding: "0 10px",
      gap: 4,
      zIndex: 50,
      userSelect: "none",
      fontFamily: '"Inter", sans-serif',
    }}>
      {navBtn("Start",         onStart)}
      {navBtn("Home",          onHome,  activeWs === 0)}
      {navBtn("Panel",         onPanel)}
      {navBtn("Notifications", onNotif)}
      {navBtn("Settings",      onSettings)}

      <div style={{ width: 12 }} />

      {/* Workspace identity stripes — the ONLY color permitted, only here */}
      <div style={{ display: "flex", gap: 5 }}>
        {Array.from({ length: 9 }).map((_, i) => {
          const n = i + 1;
          const active = n === activeWs;
          const stripe = C.ws[i];
          return (
            <button
              key={n}
              onClick={() => onSelectWs(n)}
              title={`Workspace ${n}`}
              style={{
                width: 14, height: 14,
                borderRadius: "50%",
                background: active ? stripe : "transparent",
                border: `1px solid ${active ? stripe : `${stripe}88`}`,
                opacity: active ? 1 : 0.55,
                color: active ? C.void : C.textTertiary,
                fontSize: "0.5rem",
                fontWeight: 700,
                fontFamily: '"JetBrains Mono", monospace',
                cursor: "pointer",
                padding: 0,
                display: "flex", alignItems: "center", justifyContent: "center",
                transition: "all 0.15s",
              }}
            >
              {n}
            </button>
          );
        })}
      </div>

      <div style={{ flex: 1 }} />

      <span style={{
        color: C.textTertiary,
        fontSize: "0.55rem",
        letterSpacing: "0.18em",
        fontFamily: '"Architects Daughter", "Caveat", cursive',
      }}>
        OWL
      </span>
      <span style={{
        color: C.textPrimary,
        fontSize: "0.7rem",
        fontWeight: 700,
        fontFamily: '"JetBrains Mono", monospace',
      }}>
        {hh}:{mm}
      </span>
    </div>
  );
}
