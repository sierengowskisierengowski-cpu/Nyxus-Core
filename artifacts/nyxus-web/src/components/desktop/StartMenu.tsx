import { useState } from "react";
import { C, APPS, AppDef } from "./shared";

type Tab = "all" | "live" | "tarball" | "system";

export function StartMenu({ open, onClose, onLaunch }: { open: boolean; onClose: () => void; onLaunch: (a: AppDef) => void }) {
  const [tab, setTab] = useState<Tab>("all");
  if (!open) return null;

  const filtered = tab === "all" ? APPS : APPS.filter(a => a.category === tab);
  const tabs: { id: Tab; label: string; count: number }[] = [
    { id: "all",     label: "All",      count: APPS.length },
    { id: "live",    label: "Live",     count: APPS.filter(a => a.category === "live").length },
    { id: "tarball", label: "Apps",     count: APPS.filter(a => a.category === "tarball").length },
    { id: "system",  label: "System",   count: APPS.filter(a => a.category === "system").length },
  ];

  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.55)",
        backdropFilter: "blur(8px)",
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
          width: "100%", maxWidth: 880, maxHeight: "100%",
          background: C.glassDark,
          backdropFilter: "blur(14px) saturate(1.1)",
          WebkitBackdropFilter: "blur(14px) saturate(1.1)",
          border: `1px solid ${C.hairline}`,
          borderRadius: 14,
          boxShadow: `0 20px 60px ${C.rimDark}`,
          padding: "1.4rem 1.6rem",
          display: "flex", flexDirection: "column", gap: "1rem",
          fontFamily: '"Inter", sans-serif',
          overflow: "hidden",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
          <div>
            <div style={{ fontSize: "0.55rem", color: C.textTertiary, letterSpacing: "0.22em", fontFamily: '"JetBrains Mono", monospace' }}>NYXUS · START</div>
            <div style={{
              fontSize: "1.5rem",
              color: C.textPrimary,
              fontFamily: '"Architects Daughter", "Caveat", cursive',
              marginTop: 2,
            }}>
              All apps
            </div>
          </div>
          <button onClick={onClose} style={{
            background: "transparent",
            border: `1px solid ${C.hairline}`,
            color: C.textSecondary,
            padding: "3px 11px",
            fontSize: "0.65rem",
            cursor: "pointer",
            borderRadius: 6,
            letterSpacing: "0.15em",
            fontFamily: '"JetBrains Mono", monospace',
          }}>✕ CLOSE</button>
        </div>

        {/* Category tabs */}
        <div style={{ display: "flex", gap: 6, borderBottom: `1px solid ${C.hairline}`, paddingBottom: 8 }}>
          {tabs.map(t => {
            const isActive = t.id === tab;
            return (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                style={{
                  background: isActive ? C.glassDeeper : "transparent",
                  border: `1px solid ${isActive ? C.hairlineHi : "transparent"}`,
                  color: isActive ? C.white : C.textSecondary,
                  fontSize: "0.7rem",
                  padding: "5px 14px",
                  borderRadius: 8,
                  cursor: "pointer",
                  letterSpacing: "0.04em",
                  fontFamily: '"Inter", sans-serif',
                }}
              >
                {t.label} <span style={{ color: C.textTertiary, marginLeft: 4 }}>{t.count}</span>
              </button>
            );
          })}
        </div>

        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(120px, 1fr))",
          gap: 10,
          overflowY: "auto",
          paddingRight: 4,
        }}>
          {filtered.map(a => (
            <button
              key={a.id}
              onClick={() => { onLaunch(a); onClose(); }}
              style={{
                display: "flex", flexDirection: "column",
                alignItems: "center", gap: 8,
                padding: "0.95rem 0.6rem",
                background: C.glassDeeper,
                border: `1px solid ${C.hairline}`,
                borderRadius: 12,
                cursor: "pointer",
                color: C.textPrimary,
                transition: "all 0.15s",
              }}
              onMouseEnter={e => {
                e.currentTarget.style.background = C.glassDeepest;
                e.currentTarget.style.borderColor = C.hairlineHi;
              }}
              onMouseLeave={e => {
                e.currentTarget.style.background = C.glassDeeper;
                e.currentTarget.style.borderColor = C.hairline;
              }}
            >
              <div style={{ fontSize: "1.7rem", color: C.textPrimary }}>{a.glyph}</div>
              <div style={{
                fontSize: "0.78rem",
                fontFamily: '"Inter", sans-serif',
                letterSpacing: "0.02em",
                color: C.textPrimary,
                fontWeight: 500,
              }}>
                {a.name}
              </div>
              <div style={{
                fontSize: "0.45rem",
                color: C.textTertiary,
                letterSpacing: "0.16em",
                fontFamily: '"JetBrains Mono", monospace',
              }}>
                {a.category === "live" ? "LIVE" : a.category === "tarball" ? "APP" : "SYSTEM"}
              </div>
            </button>
          ))}
        </div>

        <div style={{
          borderTop: `1px solid ${C.hairline}`,
          paddingTop: "0.65rem",
          display: "flex",
          justifyContent: "space-between",
          fontSize: "0.55rem",
          color: C.textTertiary,
          letterSpacing: "0.18em",
          fontFamily: '"JetBrains Mono", monospace',
        }}>
          <span>{filtered.length} / {APPS.length} APPS</span>
          <span>NYX-J5W-2026-SIERENGOWSKI-LOCKED</span>
        </div>
      </div>
    </div>
  );
}
