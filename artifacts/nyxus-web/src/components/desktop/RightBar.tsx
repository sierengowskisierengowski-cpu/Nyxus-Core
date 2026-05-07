import { C, APPS, AppDef } from "./shared";

export function RightBar({ onLaunch, openId }: { onLaunch: (a: AppDef) => void; openId: string | null }) {
  return (
    <div style={{
      position: "fixed",
      top: 32, right: 6, bottom: 32,
      width: 36,
      background: C.panelBg,
      border: `1px solid ${C.gold}`,
      borderRadius: 4,
      boxShadow: `0 0 10px ${C.gold}66, 0 0 20px ${C.gold}33`,
      backdropFilter: "blur(14px) saturate(1.6)",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      padding: "6px 0",
      gap: 5,
      zIndex: 50,
      userSelect: "none",
      overflowY: "auto",
    }}>
      {APPS.map(a => {
        const active = a.id === openId;
        return (
          <button
            key={a.id}
            onClick={() => onLaunch(a)}
            title={a.name}
            style={{
              width: 26, height: 26,
              borderRadius: 4,
              background: `linear-gradient(145deg, ${a.color}cc 0%, ${a.color}66 60%, ${a.color}22 100%)`,
              border: active ? `2px solid ${C.white}` : `1.5px solid ${a.color}`,
              boxShadow: active
                ? `0 0 14px ${a.color}, 0 0 26px ${a.color}88, inset 0 0 4px rgba(255,255,255,0.5)`
                : `0 0 6px ${a.color}99, inset 0 0 3px rgba(255,255,255,0.25)`,
              color: "#0a0612",
              fontSize: "0.85rem",
              fontWeight: 900,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              padding: 0,
              transition: "all 0.15s",
              textShadow: "0 1px 2px rgba(255,255,255,0.4)",
            }}
            onMouseEnter={e => {
              e.currentTarget.style.transform = "scale(1.1)";
            }}
            onMouseLeave={e => {
              e.currentTarget.style.transform = "scale(1)";
            }}
          >
            {a.glyph}
          </button>
        );
      })}
    </div>
  );
}
