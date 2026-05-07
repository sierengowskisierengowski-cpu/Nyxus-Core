import { C, useTime } from "./shared";

function Card({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{
      background: C.glassDeeper,
      border: `1px solid ${C.hairline}`,
      borderRadius: 12,
      padding: "0.8rem 0.95rem",
    }}>
      <div style={{
        fontSize: "0.55rem",
        color: C.textTertiary,
        letterSpacing: "0.18em",
        fontFamily: '"JetBrains Mono", monospace',
        marginBottom: 6,
      }}>{label}</div>
      {children}
    </div>
  );
}

export function PanelFlyout({ open, onClose }: { open: boolean; onClose: () => void }) {
  const time = useTime();
  if (!open) return null;
  return (
    <div style={{
      position: "fixed",
      top: 34, bottom: 34, right: 50,
      width: 320,
      background: C.glassDark,
      backdropFilter: "blur(14px) saturate(1.1)",
      WebkitBackdropFilter: "blur(14px) saturate(1.1)",
      border: `1px solid ${C.hairline}`,
      borderRadius: 14,
      boxShadow: `0 20px 60px ${C.rimDark}`,
      padding: "1rem 1.1rem",
      display: "flex", flexDirection: "column", gap: "0.85rem",
      zIndex: 80,
      fontFamily: '"Inter", sans-serif',
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <div>
          <div style={{ fontSize: "0.5rem", color: C.textTertiary, letterSpacing: "0.22em", fontFamily: '"JetBrains Mono", monospace' }}>NYXUS · PANEL</div>
          <div style={{
            fontSize: "1.2rem",
            color: C.textPrimary,
            fontFamily: '"Architects Daughter", "Caveat", cursive',
          }}>The Panel</div>
        </div>
        <button onClick={onClose} style={{
          background: "transparent",
          border: `1px solid ${C.hairline}`,
          color: C.textSecondary,
          padding: "2px 8px",
          fontSize: "0.6rem",
          cursor: "pointer",
          borderRadius: 6,
          fontFamily: '"JetBrains Mono", monospace',
        }}>✕</button>
      </div>

      <Card label="WEATHER">
        <div style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
          <div style={{
            fontSize: "1.7rem",
            color: C.textPrimary,
            fontFamily: '"Architects Daughter", "Caveat", cursive',
          }}>72°F</div>
          <div style={{ fontSize: "0.7rem", color: C.textSecondary }}>Clear · Light breeze</div>
        </div>
      </Card>

      <Card label="NEWS">
        <div style={{ fontSize: "0.72rem", color: C.textSecondary, lineHeight: 1.5 }}>
          NYXUS rev r16 — DARK MIRROR locked. 26 apps mirrored to web preview.
        </div>
      </Card>

      <Card label="CLOCK">
        <div style={{
          fontSize: "1.5rem",
          color: C.textPrimary,
          fontFamily: '"JetBrains Mono", monospace',
          fontWeight: 700,
        }}>
          {String(time.getHours()).padStart(2, "0")}:{String(time.getMinutes()).padStart(2, "0")}
        </div>
        <div style={{ fontSize: "0.65rem", color: C.textTertiary, marginTop: 3 }}>
          {time.toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric", year: "numeric" })}
        </div>
      </Card>

      <Card label="SYSTEM">
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6, fontSize: "0.65rem", color: C.textSecondary }}>
          <div>CPU <span style={{ color: C.textPrimary }}>15%</span></div>
          <div>MEM <span style={{ color: C.textPrimary }}>34%</span></div>
          <div>DISK <span style={{ color: C.textPrimary }}>35%</span></div>
          <div>BAT <span style={{ color: C.textPrimary }}>92%</span></div>
        </div>
      </Card>

      <div style={{ flex: 1 }} />
      <div style={{
        fontSize: "0.5rem",
        color: C.textTertiary,
        letterSpacing: "0.2em",
        textAlign: "center",
        fontFamily: '"JetBrains Mono", monospace',
      }}>
        © 2026 JOSEPH SIERENGOWSKI
      </div>
    </div>
  );
}
