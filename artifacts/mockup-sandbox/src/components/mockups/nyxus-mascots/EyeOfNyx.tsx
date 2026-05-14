import './_group.css';

const CREAM = '#f4ead5';

function Mark({ size = 240, glow = true, blink = false }: { size?: number; glow?: boolean; blink?: boolean }) {
  const stroke = Math.max(1, size / 80);
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 240 240"
      style={{
        animation: glow ? 'nyxus-breathe 4s ease-in-out infinite' : undefined,
        overflow: 'visible',
      }}
    >
      <defs>
        <radialGradient id="eyeGlow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor={CREAM} stopOpacity="0.35" />
          <stop offset="60%" stopColor={CREAM} stopOpacity="0.05" />
          <stop offset="100%" stopColor={CREAM} stopOpacity="0" />
        </radialGradient>
        <linearGradient id="irisGrad" x1="50%" y1="0%" x2="50%" y2="100%">
          <stop offset="0%" stopColor="#0a0a0a" />
          <stop offset="100%" stopColor="#1a1a1a" />
        </linearGradient>
      </defs>

      {glow && <circle cx="120" cy="120" r="118" fill="url(#eyeGlow)" />}

      <g
        style={{
          transformOrigin: '120px 120px',
          animation: blink ? 'nyxus-blink 5s ease-in-out infinite' : undefined,
        }}
      >
        {/* The almond eye outline — primordial geometry */}
        <path
          d="M 20 120 Q 120 30 220 120 Q 120 210 20 120 Z"
          fill="none"
          stroke={CREAM}
          strokeWidth={stroke * 1.4}
          strokeLinejoin="round"
        />
        {/* Inner iris orb (deep void) */}
        <circle cx="120" cy="120" r="58" fill="url(#irisGrad)" stroke={CREAM} strokeWidth={stroke * 0.8} />
        {/* Vertical slit pupil — what makes it Nyx, not a generic eye */}
        <ellipse cx="120" cy="120" rx={stroke * 2.2} ry="48" fill={CREAM} />
        {/* Single specular highlight — the spark of consciousness */}
        <circle cx="105" cy="100" r={stroke * 1.2} fill={CREAM} opacity="0.9" />
        {/* Brow accent — gives it intent */}
        <path
          d="M 50 95 Q 120 70 190 95"
          fill="none"
          stroke={CREAM}
          strokeWidth={stroke * 0.6}
          strokeLinecap="round"
          opacity="0.5"
        />
      </g>
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

export function EyeOfNyx() {
  return (
    <div className="nyxus-stage" style={{ padding: '64px 72px' }}>
      {/* Header lockup */}
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 56 }}>
        <div>
          <div className="nyxus-eyebrow">NYXUS · Mascot Concept · 01</div>
          <h1 style={{ fontSize: 64, fontWeight: 800, margin: '12px 0 4px', letterSpacing: '-0.03em' }}>
            The Eye of Nyx
          </h1>
          <div className="nyxus-script" style={{ fontSize: 32, color: 'rgba(244,234,213,0.7)' }}>
            primordial · intelligent · always awake
          </div>
        </div>
        <div className="nyxus-eyebrow" style={{ textAlign: 'right', lineHeight: 2 }}>
          rev r15 · 2026.05.14<br />
          <span style={{ color: 'var(--cream)', fontFamily: 'Inter', fontWeight: 600, letterSpacing: '0.05em' }}>
            for review
          </span>
        </div>
      </header>

      {/* Hero mark with breathing glow */}
      <section className="nyxus-card" style={{ padding: '80px 0', marginBottom: 48, display: 'flex', justifyContent: 'center', alignItems: 'center', flexDirection: 'column', gap: 32 }}>
        <Mark size={320} glow blink />
        <div style={{ textAlign: 'center', maxWidth: 540 }}>
          <div style={{ fontSize: 14, lineHeight: 1.7, color: 'rgba(244,234,213,0.75)' }}>
            A single elongated eye with a vertical slit pupil. Reads as a watching presence at any size.
            Animates with a slow breath and an occasional blink — not decoration, recognition.
          </div>
        </div>
      </section>

      {/* Three context tiles */}
      <section style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 24, marginBottom: 48 }}>
        {/* On black */}
        <div className="nyxus-card" style={{ padding: 40, textAlign: 'center' }}>
          <div className="nyxus-eyebrow" style={{ marginBottom: 24 }}>On triple-black</div>
          <div style={{ display: 'flex', justifyContent: 'center', padding: '24px 0' }}>
            <Mark size={140} />
          </div>
        </div>
        {/* On cream */}
        <div style={{ background: CREAM, padding: 40, textAlign: 'center', borderRadius: 3 }}>
          <div className="nyxus-eyebrow" style={{ color: 'rgba(10,10,10,0.55)', marginBottom: 24 }}>Inverted · on cream</div>
          <div style={{ display: 'flex', justifyContent: 'center', padding: '24px 0' }}>
            <svg width="140" height="140" viewBox="0 0 240 240">
              <path d="M 20 120 Q 120 30 220 120 Q 120 210 20 120 Z" fill="none" stroke="#0a0a0a" strokeWidth="2.5" strokeLinejoin="round" />
              <circle cx="120" cy="120" r="58" fill="#0a0a0a" />
              <ellipse cx="120" cy="120" rx="4.5" ry="48" fill={CREAM} />
              <circle cx="105" cy="100" r="2.5" fill={CREAM} />
              <path d="M 50 95 Q 120 70 190 95" fill="none" stroke="#0a0a0a" strokeWidth="1.8" strokeLinecap="round" opacity="0.5" />
            </svg>
          </div>
        </div>
        {/* On wallpaper through glass */}
        <div className="nyxus-wallpaper" style={{ padding: 12, borderRadius: 3, position: 'relative' }}>
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
        <Mark size={120} blink />
        <div style={{ borderLeft: '1px solid var(--cream-line)', paddingLeft: 48, flex: 1 }}>
          <div style={{ fontSize: 56, fontWeight: 800, letterSpacing: '0.12em', lineHeight: 1 }}>NYXUS</div>
          <div className="nyxus-script" style={{ fontSize: 28, color: 'rgba(244,234,213,0.65)', marginTop: 4 }}>
            see in the dark.
          </div>
        </div>
        <div style={{ textAlign: 'right', fontFamily: 'JetBrains Mono', fontSize: 11, color: 'var(--cream-dim)', letterSpacing: '0.1em', lineHeight: 1.8 }}>
          PRIMARY LOCKUP<br />
          HORIZONTAL · L
        </div>
      </section>

      {/* Size matrix */}
      <section className="nyxus-card" style={{ padding: '32px 48px', marginBottom: 48 }}>
        <div className="nyxus-eyebrow" style={{ marginBottom: 8 }}>Holds at every scale · 16px favicon → 128px dock</div>
        <SizeRow />
      </section>

      {/* Tech specs */}
      <section style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
        <div className="nyxus-card" style={{ padding: 32 }}>
          <div className="nyxus-eyebrow" style={{ marginBottom: 18 }}>Why it works</div>
          <ul style={{ fontSize: 13, lineHeight: 1.85, color: 'rgba(244,234,213,0.78)', paddingLeft: 18, margin: 0 }}>
            <li>NYX = Greek primordial goddess of night. The eye literally <em style={{ color: CREAM }}>is</em> Nyx watching.</li>
            <li>Vertical slit pupil reads instantly as <em style={{ color: CREAM }}>not human</em> — feline, ancient, alert.</li>
            <li>Single specular highlight gives it personhood without crossing into cute.</li>
            <li>Pure 2D geometry. No gradients required at favicon size.</li>
            <li>Animates beautifully: breathe + blink. Static version is just as strong.</li>
          </ul>
        </div>
        <div className="nyxus-card" style={{ padding: 32, fontFamily: 'JetBrains Mono', fontSize: 12, lineHeight: 2, color: 'rgba(244,234,213,0.7)' }}>
          <div className="nyxus-eyebrow" style={{ marginBottom: 18, fontFamily: 'JetBrains Mono' }}>Build spec</div>
          <div>geometry  &nbsp;→&nbsp; almond + circle + slit</div>
          <div>fill      &nbsp;→&nbsp; #f4ead5 stroke on void</div>
          <div>radius    &nbsp;→&nbsp; 3px (brand standard)</div>
          <div>min size  &nbsp;→&nbsp; 16×16 (favicon legible)</div>
          <div>animation &nbsp;→&nbsp; breathe 4s · blink 5s</div>
          <div>files     &nbsp;→&nbsp; svg · png 16/32/64/128/256/512</div>
        </div>
      </section>

      <footer style={{ marginTop: 56, paddingTop: 24, borderTop: '1px solid var(--cream-line)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div className="nyxus-script" style={{ fontSize: 22, color: 'rgba(244,234,213,0.55)' }}>nyx is watching.</div>
        <div className="nyxus-eyebrow">CONCEPT 01 · EYE OF NYX</div>
      </footer>
    </div>
  );
}
