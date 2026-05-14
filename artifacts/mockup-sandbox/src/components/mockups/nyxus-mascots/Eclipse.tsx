import './_group.css';

const CREAM = '#f4ead5';

function Mark({ size = 240, glow = true, animate = false }: { size?: number; glow?: boolean; animate?: boolean }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 240 240"
      style={{
        animation: glow ? 'nyxus-breathe 5s ease-in-out infinite' : undefined,
        overflow: 'visible',
      }}
    >
      <defs>
        <radialGradient id="eclipseGlow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor={CREAM} stopOpacity="0.4" />
          <stop offset="55%" stopColor={CREAM} stopOpacity="0.06" />
          <stop offset="100%" stopColor={CREAM} stopOpacity="0" />
        </radialGradient>
        <radialGradient id="orbBody" cx="40%" cy="35%" r="70%">
          <stop offset="0%" stopColor="#1a1a1a" />
          <stop offset="100%" stopColor="#050505" />
        </radialGradient>
        <mask id="crescentMask">
          <rect width="240" height="240" fill="white" />
          <circle cx="148" cy="108" r="92" fill="black" />
        </mask>
      </defs>

      {glow && <circle cx="120" cy="120" r="120" fill="url(#eclipseGlow)" />}

      {/* The black orb — the void, the night sphere */}
      <circle cx="120" cy="120" r="100" fill="url(#orbBody)" stroke={CREAM} strokeWidth="1.2" strokeOpacity="0.4" />

      {/* The cream crescent — eclipse / closed eye / sliver of moon */}
      <g style={{ transformOrigin: '120px 120px', animation: animate ? 'nyxus-iris 1.4s cubic-bezier(0.2,0.9,0.3,1) both' : undefined }}>
        <circle cx="120" cy="120" r="100" fill={CREAM} mask="url(#crescentMask)" />
      </g>

      {/* Tiniest specular dot at the bright tip — gives it life */}
      <circle cx="48" cy="108" r={Math.max(1, size / 120)} fill="#fff" opacity="0.9" />
    </svg>
  );
}

function SizeRow() {
  const sizes = [16, 24, 32, 48, 64, 96, 128];
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', gap: 32, padding: '24px 0' }}>
      {sizes.map((s) => (
        <div key={s} style={{ textAlign: 'center' }}>
          <div style={{ height: 130, display: 'flex', alignItems: 'flex-end', justifyContent: 'center' }}>
            <Mark size={s} glow={false} />
          </div>
          <div className="nyxus-eyebrow" style={{ marginTop: 12 }}>{s}px</div>
        </div>
      ))}
    </div>
  );
}

export function Eclipse() {
  return (
    <div className="nyxus-stage" style={{ padding: '64px 72px' }}>
      {/* Header */}
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 56 }}>
        <div>
          <div className="nyxus-eyebrow">NYXUS · Mascot Concept · 02</div>
          <h1 style={{ fontSize: 64, fontWeight: 800, margin: '12px 0 4px', letterSpacing: '-0.03em' }}>
            The Eclipse
          </h1>
          <div className="nyxus-script" style={{ fontSize: 32, color: 'rgba(244,234,213,0.7)' }}>
            night made into a single mark.
          </div>
        </div>
        <div className="nyxus-eyebrow" style={{ textAlign: 'right', lineHeight: 2 }}>
          rev r15 · 2026.05.14<br />
          <span style={{ color: 'var(--cream)', fontFamily: 'Inter', fontWeight: 600, letterSpacing: '0.05em' }}>
            for review
          </span>
        </div>
      </header>

      {/* Hero */}
      <section className="nyxus-card" style={{ padding: '80px 0', marginBottom: 48, display: 'flex', justifyContent: 'center', alignItems: 'center', flexDirection: 'column', gap: 32 }}>
        <Mark size={320} glow />
        <div style={{ textAlign: 'center', maxWidth: 580 }}>
          <div style={{ fontSize: 14, lineHeight: 1.7, color: 'rgba(244,234,213,0.75)' }}>
            A perfect black orb with a single cream crescent rising from its edge. Reads as an eclipse,
            a closed eye, the moon, an aperture — all at once. The kind of mark Apple, Stripe, or
            Linear would ship.
          </div>
        </div>
      </section>

      {/* Surface tests */}
      <section style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 24, marginBottom: 48 }}>
        <div className="nyxus-card" style={{ padding: 40, textAlign: 'center' }}>
          <div className="nyxus-eyebrow" style={{ marginBottom: 24 }}>On triple-black</div>
          <div style={{ display: 'flex', justifyContent: 'center', padding: '24px 0' }}>
            <Mark size={140} />
          </div>
        </div>
        <div style={{ background: CREAM, padding: 40, textAlign: 'center', borderRadius: 3 }}>
          <div className="nyxus-eyebrow" style={{ color: 'rgba(10,10,10,0.55)', marginBottom: 24 }}>Inverted · on cream</div>
          <div style={{ display: 'flex', justifyContent: 'center', padding: '24px 0' }}>
            <svg width="140" height="140" viewBox="0 0 240 240">
              <defs>
                <mask id="crescentMaskInv">
                  <rect width="240" height="240" fill="white" />
                  <circle cx="148" cy="108" r="92" fill="black" />
                </mask>
              </defs>
              <circle cx="120" cy="120" r="100" fill={CREAM} stroke="#0a0a0a" strokeWidth="1.2" />
              <circle cx="120" cy="120" r="100" fill="#0a0a0a" mask="url(#crescentMaskInv)" />
              <circle cx="48" cy="108" r="1.5" fill="#0a0a0a" opacity="0.9" />
            </svg>
          </div>
        </div>
        <div className="nyxus-wallpaper" style={{ padding: 12, borderRadius: 3 }}>
          <div className="nyxus-glass" style={{ padding: 28, textAlign: 'center', borderRadius: 3 }}>
            <div className="nyxus-eyebrow" style={{ marginBottom: 18 }}>Through frosted glass</div>
            <div style={{ display: 'flex', justifyContent: 'center', padding: '18px 0' }}>
              <Mark size={120} />
            </div>
          </div>
        </div>
      </section>

      {/* Wordmark lockup */}
      <section className="nyxus-card" style={{ padding: '56px 64px', marginBottom: 48, display: 'flex', alignItems: 'center', gap: 48 }}>
        <Mark size={120} />
        <div style={{ borderLeft: '1px solid var(--cream-line)', paddingLeft: 48, flex: 1 }}>
          <div style={{ fontSize: 56, fontWeight: 800, letterSpacing: '0.12em', lineHeight: 1 }}>NYXUS</div>
          <div className="nyxus-script" style={{ fontSize: 28, color: 'rgba(244,234,213,0.65)', marginTop: 4 }}>
            born of night.
          </div>
        </div>
        <div style={{ textAlign: 'right', fontFamily: 'JetBrains Mono', fontSize: 11, color: 'var(--cream-dim)', letterSpacing: '0.1em', lineHeight: 1.8 }}>
          PRIMARY LOCKUP<br />
          HORIZONTAL · L
        </div>
      </section>

      {/* Size matrix */}
      <section className="nyxus-card" style={{ padding: '32px 48px', marginBottom: 48 }}>
        <div className="nyxus-eyebrow" style={{ marginBottom: 8 }}>Brutally legible — even at 16px the crescent reads</div>
        <SizeRow />
      </section>

      {/* Boot sequence preview */}
      <section className="nyxus-card" style={{ padding: 40, marginBottom: 48 }}>
        <div className="nyxus-eyebrow" style={{ marginBottom: 24 }}>Plymouth boot reveal — crescent waxes from nothing</div>
        <div style={{ background: '#000', borderRadius: 3, padding: '64px 0', display: 'flex', justifyContent: 'center', position: 'relative', overflow: 'hidden' }}>
          <Mark size={180} glow animate />
          <div style={{ position: 'absolute', bottom: 24, left: '50%', transform: 'translateX(-50%)', width: 180, height: 2, background: 'rgba(244,234,213,0.1)', borderRadius: 999, overflow: 'hidden' }}>
            <div style={{ width: '60%', height: '100%', background: CREAM, boxShadow: `0 0 8px ${CREAM}`, animation: 'nyxus-pulse 2s ease-in-out infinite' }} />
          </div>
        </div>
      </section>

      {/* Tech specs */}
      <section style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
        <div className="nyxus-card" style={{ padding: 32 }}>
          <div className="nyxus-eyebrow" style={{ marginBottom: 18 }}>Why it works</div>
          <ul style={{ fontSize: 13, lineHeight: 1.85, color: 'rgba(244,234,213,0.78)', paddingLeft: 18, margin: 0 }}>
            <li>Two shapes. Two colors. <em style={{ color: CREAM }}>That's it.</em> The mark a billion-dollar brand would ship.</li>
            <li>Reads as multiple things at once: eclipse, closed eye, moon sliver, aperture.</li>
            <li>Symbolically perfect for NYX (Greek night) — light emerging from total dark.</li>
            <li>Animates as a waxing crescent on boot — cinematic without being busy.</li>
            <li>Zero detail loss at 16px. The crescent is the silhouette.</li>
          </ul>
        </div>
        <div className="nyxus-card" style={{ padding: 32, fontFamily: 'JetBrains Mono', fontSize: 12, lineHeight: 2, color: 'rgba(244,234,213,0.7)' }}>
          <div className="nyxus-eyebrow" style={{ marginBottom: 18, fontFamily: 'JetBrains Mono' }}>Build spec</div>
          <div>geometry  &nbsp;→&nbsp; circle - circle (mask)</div>
          <div>fill      &nbsp;→&nbsp; #f4ead5 on #050505</div>
          <div>radius    &nbsp;→&nbsp; orb is the radius</div>
          <div>min size  &nbsp;→&nbsp; 16×16 (crescent legible)</div>
          <div>animation &nbsp;→&nbsp; iris-in 1.4s · breathe 5s</div>
          <div>files     &nbsp;→&nbsp; svg · png 16/32/64/128/256/512</div>
        </div>
      </section>

      <footer style={{ marginTop: 56, paddingTop: 24, borderTop: '1px solid var(--cream-line)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div className="nyxus-script" style={{ fontSize: 22, color: 'rgba(244,234,213,0.55)' }}>light at the edge of the void.</div>
        <div className="nyxus-eyebrow">CONCEPT 02 · ECLIPSE</div>
      </footer>
    </div>
  );
}
