import { C, APPS, AppDef, FRAME } from "./shared";

// Right bar shows the 4 LIVE iframe apps + the 11 tarball apps.
// System utilities (12) live inside the Start menu only.
const RIGHT_BAR_APPS = APPS.filter(a => a.category === "live" || a.category === "tarball");

export function RightBar({ onLaunch, openId }: { onLaunch: (a: AppDef) => void; openId: string | null }) {
  return (
    <div style={{
      ...FRAME,
      position: "fixed",
      top: 34, right: 6, bottom: 34,
      width: 38,
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      padding: "8px 0",
      gap: 6,
      zIndex: 50,
      userSelect: "none",
      overflowY: "auto",
    }}>
      {RIGHT_BAR_APPS.map(a => {
        const active = a.id === openId;
        return (
          <button
            key={a.id}
            onClick={() => onLaunch(a)}
            title={a.name}
            style={{
              width: 28, height: 28,
              borderRadius: 7,
              background: active ? C.glassDeeper : "transparent",
              border: `1px solid ${active ? C.hairlineHi : "transparent"}`,
              color: active ? C.white : C.textSecondary,
              fontSize: "0.95rem",
              fontWeight: 600,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              padding: 0,
              transition: "all 0.15s",
            }}
            onMouseEnter={e => {
              e.currentTarget.style.background = C.glassDeeper;
              e.currentTarget.style.color = C.white;
            }}
            onMouseLeave={e => {
              e.currentTarget.style.background = active ? C.glassDeeper : "transparent";
              e.currentTarget.style.color = active ? C.white : C.textSecondary;
            }}
          >
            {a.glyph}
          </button>
        );
      })}
    </div>
  );
}
