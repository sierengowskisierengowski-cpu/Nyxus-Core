import { C, AppDef } from "./shared";

export function MockupBody({ a }: { a: AppDef }) {
  return (
    <div style={{
      padding: "1.6rem 1.8rem",
      display: "flex",
      flexDirection: "column",
      gap: "1.2rem",
      fontFamily: '"Inter", sans-serif',
      color: C.textPrimary,
      height: "100%",
      background: "transparent",
    }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "flex-start", gap: 16 }}>
        <div style={{
          width: 56, height: 56,
          borderRadius: 14,
          background: C.glassDeeper,
          border: `1px solid ${C.hairline}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: "1.7rem",
          color: C.textPrimary,
          flexShrink: 0,
        }}>{a.glyph}</div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{
            fontSize: "0.55rem",
            color: C.textTertiary,
            letterSpacing: "0.22em",
            fontFamily: '"JetBrains Mono", monospace',
            marginBottom: 4,
          }}>{a.tagline ?? "NYXUS APP"}</div>
          <div style={{
            fontSize: "1.7rem",
            color: C.textPrimary,
            fontFamily: '"Architects Daughter", "Caveat", cursive',
          }}>{a.name}</div>
          <div style={{
            fontSize: "0.55rem",
            color: C.textTertiary,
            letterSpacing: "0.22em",
            fontFamily: '"JetBrains Mono", monospace',
            marginTop: 6,
          }}>
            {a.category === "tarball" ? "TARBALL · GTK4" : a.category === "system" ? "SYSTEM UTILITY" : "LIVE WEB MOCKUP"}
          </div>
        </div>
      </div>

      {/* Description */}
      {a.desc && (
        <div style={{
          background: C.glassDeeper,
          border: `1px solid ${C.hairline}`,
          borderRadius: 12,
          padding: "0.95rem 1.05rem",
          fontSize: "0.8rem",
          color: C.textSecondary,
          lineHeight: 1.65,
        }}>
          {a.desc}
        </div>
      )}

      {/* Modules */}
      {a.modules && a.modules.length > 0 && (
        <div>
          <div style={{
            fontSize: "0.55rem",
            color: C.textTertiary,
            letterSpacing: "0.22em",
            fontFamily: '"JetBrains Mono", monospace',
            marginBottom: 8,
          }}>MODULES · {a.modules.length}</div>
          <div style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))",
            gap: 8,
          }}>
            {a.modules.map(m => (
              <div key={m} style={{
                background: C.glassDeeper,
                border: `1px solid ${C.hairline}`,
                borderRadius: 10,
                padding: "0.55rem 0.75rem",
                fontSize: "0.72rem",
                color: C.textPrimary,
              }}>
                {m}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Install info */}
      {(a.install || a.download) && (
        <div style={{
          background: C.glassDeeper,
          border: `1px solid ${C.hairline}`,
          borderRadius: 12,
          padding: "0.95rem 1.05rem",
          display: "flex",
          flexDirection: "column",
          gap: 8,
        }}>
          <div style={{
            fontSize: "0.55rem",
            color: C.textTertiary,
            letterSpacing: "0.22em",
            fontFamily: '"JetBrains Mono", monospace',
          }}>INSTALL</div>
          {a.install && (
            <div style={{
              fontSize: "0.72rem",
              color: C.textPrimary,
              fontFamily: '"JetBrains Mono", monospace',
            }}>
              <span style={{ color: C.textTertiary }}>$ </span>{a.install}
            </div>
          )}
          {a.download && (
            <div style={{
              fontSize: "0.72rem",
              color: C.textSecondary,
              fontFamily: '"JetBrains Mono", monospace',
            }}>
              <span style={{ color: C.textTertiary }}>tarball · </span>{a.download}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
