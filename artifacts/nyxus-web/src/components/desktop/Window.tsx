import { ReactNode } from "react";
import { C, AppDef } from "./shared";

export function Window({ a, onClose, children }: { a: AppDef; onClose: () => void; children: ReactNode }) {
  return (
    <div style={{
      position: "fixed",
      top: 44, bottom: 44, left: 50, right: 56,
      maxWidth: 1180,
      margin: "0 auto",
      background: C.glassDark,
      backdropFilter: "blur(14px) saturate(1.1)",
      WebkitBackdropFilter: "blur(14px) saturate(1.1)",
      border: `1px solid ${C.hairline}`,
      borderRadius: 14,
      boxShadow: `0 20px 60px ${C.rimDark}, inset 0 0 0 1px rgba(0,0,0,0.35)`,
      display: "flex",
      flexDirection: "column",
      overflow: "hidden",
      zIndex: 100,
    }}>
      <div style={{
        flex: "0 0 auto",
        height: 30,
        background: C.glassDeeper,
        borderBottom: `1px solid ${C.hairline}`,
        display: "flex",
        alignItems: "center",
        padding: "0 0.7rem",
        gap: 10,
        userSelect: "none",
      }}>
        <div style={{ display: "flex", gap: 6 }}>
          {[0, 1, 2].map(i => (
            <span key={i} style={{
              width: 9, height: 9, borderRadius: "50%",
              background: C.glassDeepest,
              border: `1px solid ${C.hairline}`,
            }} />
          ))}
        </div>
        <span style={{ color: C.textSecondary, fontSize: "0.85rem" }}>{a.glyph}</span>
        <span style={{
          color: C.textPrimary,
          fontSize: "0.78rem",
          fontFamily: '"Inter", sans-serif',
          letterSpacing: "0.04em",
          fontWeight: 600,
        }}>
          {a.name}
        </span>
        <span style={{ color: C.textTertiary, fontSize: "0.55rem", letterSpacing: "0.18em" }}>
          NYXUS
        </span>
        <div style={{ flex: 1 }} />
        <button
          onClick={onClose}
          style={{
            background: "transparent",
            border: `1px solid ${C.hairline}`,
            color: C.textSecondary,
            fontSize: "0.6rem",
            cursor: "pointer",
            borderRadius: 6,
            padding: "2px 9px",
            letterSpacing: "0.15em",
            fontFamily: '"JetBrains Mono", monospace',
          }}
          onMouseEnter={e => { e.currentTarget.style.background = C.glassDeepest; e.currentTarget.style.color = C.white; }}
          onMouseLeave={e => { e.currentTarget.style.background = "transparent"; e.currentTarget.style.color = C.textSecondary; }}
        >
          ✕ CLOSE
        </button>
      </div>
      <div style={{ flex: 1, overflow: "auto", background: "transparent" }}>
        {children}
      </div>
    </div>
  );
}
