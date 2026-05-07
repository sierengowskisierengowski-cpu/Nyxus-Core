import { ReactNode } from "react";
import { C, AppDef } from "./shared";

export function Window({ a, onClose, children }: { a: AppDef; onClose: () => void; children: ReactNode }) {
  return (
    <div style={{
      position: "fixed",
      top: 40, bottom: 40, left: 50, right: 56,
      maxWidth: 1180,
      margin: "0 auto",
      background: "rgba(6,4,12,0.55)",
      backdropFilter: "blur(14px) saturate(1.6)",
      WebkitBackdropFilter: "blur(14px) saturate(1.6)",
      border: `1px solid ${a.color}`,
      borderTop: `2px solid ${a.color}`,
      borderRadius: 6,
      boxShadow: `0 0 40px ${a.color}66, 0 0 100px rgba(0,0,0,0.85), inset 0 0 80px rgba(0,0,0,0.4)`,
      display: "flex",
      flexDirection: "column",
      overflow: "hidden",
      zIndex: 100,
    }}>
      <div style={{
        flex: "0 0 auto",
        height: 28,
        background: `linear-gradient(180deg, ${a.color}22 0%, rgba(0,0,0,0.55) 100%)`,
        borderBottom: `1px solid ${a.color}55`,
        display: "flex",
        alignItems: "center",
        padding: "0 0.6rem",
        gap: 10,
        userSelect: "none",
      }}>
        <div style={{ display: "flex", gap: 5 }}>
          {[C.green, C.gold, C.red].map(c => (
            <span key={c} style={{ width: 9, height: 9, borderRadius: "50%", background: c, opacity: 0.7, boxShadow: `0 0 4px ${c}` }} />
          ))}
        </div>
        <span style={{ color: a.color, fontSize: "0.85rem", textShadow: `0 0 8px ${a.color}` }}>{a.glyph}</span>
        <span style={{
          color: a.color,
          fontSize: "0.85rem",
          fontFamily: "'Caveat', cursive",
          letterSpacing: "0.04em",
          fontWeight: 700,
          textShadow: `0 0 6px ${a.color}55`,
        }}>
          {a.name}
        </span>
        <span style={{ color: C.dim, fontSize: "0.55rem", letterSpacing: "0.18em", opacity: 0.6 }}>
          NYXUS · WINDOW
        </span>
        <div style={{ flex: 1 }} />
        <button
          onClick={onClose}
          style={{
            background: "transparent",
            border: `1px solid ${C.red}66`,
            color: C.red,
            fontSize: "0.6rem",
            cursor: "pointer",
            borderRadius: 2,
            padding: "2px 8px",
            letterSpacing: "0.15em",
          }}
          onMouseEnter={e => { e.currentTarget.style.background = `${C.red}22`; }}
          onMouseLeave={e => { e.currentTarget.style.background = "transparent"; }}
        >
          ✕ CLOSE
        </button>
      </div>
      <div style={{ flex: 1, overflow: "auto", background: C.void }}>
        {children}
      </div>
    </div>
  );
}
