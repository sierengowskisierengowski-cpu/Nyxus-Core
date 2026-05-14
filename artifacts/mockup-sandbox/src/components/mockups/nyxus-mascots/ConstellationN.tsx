import './_group.css';

const CREAM = '#f4ead5';

// Star coordinates that trace the letter N (top-left, bottom-left, top-right, bottom-right + diagonal star)
// Plus a "guardian" star outside the form for celestial richness
const STARS = [
  { x: 50,  y: 50,  r: 5,   key: 'tl' },     // top-left
  { x: 50,  y: 190, r: 4.5, key: 'bl' },     // bottom-left
  { x: 190, y: 50,  r: 4.5, key: 'tr' },     // top-right
  { x: 190, y: 190, r: 5,   key: 'br' },     // bottom-right
  { x: 120, y: 120, r: 3,   key: 'mid' },    // diagonal midpoint (subtle)
];

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
        <radialGradient id="constGlow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor={CREAM} stopOpacity="0.25" />
          <stop offset="60%" stopColor={CREAM} stopOpacity="0.04" />
          <stop offset="100%" stopColor={CREAM} stopOpacity="0" />
        </radialGradient>
        <radialGradient id="starGlow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#fff" />
          <stop offset="40%" stopColor={CREAM} />
          <stop offset="100%" stopColor={CREAM} stopOpacity="0" />
        </radialGradient>
      </defs>

      {glow && <circle cx="120" cy="120" r="120" fill="url(#constGlow)" />}

      {/* Hairline connection lines tracing the letter N */}
      <g
        stroke={CREAM}
        strokeWidth={Math.max(0.6, size / 240)}
        strokeOpacity="0.55"
        fill="none"
        strokeLinecap="round"
        style={{
          strokeDasharray: animate ? 100 : undefined,
          animation: animate ? 'nyxus-line-draw 1.6s ease-out 0.4s both' : undefined,
        }}
      >
        {/* Left vertical of N */}
        <line x1="50" y1="50" x2="50" y2="190" />
        {/* Diagonal of N */}
        <line x1="50" y1="50" x2="190" y2="190" />
        {/* Right vertical of N */}
        <line x1="190" y1="50" x2="190" y2="190" />
      </g>

      {/* Stars */}
      {STARS.map((s, i) => {
        const r = (s.r / 240) * size;
        return (
          <g
            key={s.key}
            style={{
              transformOrigin: `${s.x}px ${s.y}px`,
              animation: animate ? `nyxus-star-in 0.5s ease-out ${i * 0.15}s both` : undefined,
            }}
          >
            {/* Soft halo */}
            <circle cx={s.x} cy={s.y} r={s.r * 3.2} fill="url(#starGlow)" opacity="0.7" />
            {/* Solid star */}
            <circle cx={s.x} cy={s.y} r={s.r} fill={CREAM} />
            {/* Pulse for the brightest stars */}
            {(s.key === 'tl' || s.key === 'br') && (
              <circle
                cx={s.x}
                cy={s.y}
                r={s.r}
                fill={CREAM}
                style={{ transformOrigin: `${s.x}px ${s.y}px`, animation: 'nyxus-pulse 3s ease-in-out infinite' }}
              />
            )}
          </g>
        );
      })}
    </svg>
  );
}

function MiniMark({ size }: { size: number }) {
  // Simplified for tiny sizes — drop the midpoint star, keep only 4 corners + lines
  return (
    <svg width={size} height={size} viewBox="0 0 240 240">
      <g stroke={CREAM} strokeWidth={Math.max(2, size / 32)} strokeOpacity="0.5" strokeLinecap="round">
        <line x1="50" y1="50" x2="50" y2="190" />
        <line x1="50" y1="50" x2="190" y2="190" />
        <line x1="190" y1="50" x2="190" y2="190" />
      </g>
      {[[50, 50], [50, 190], [190, 50], [190, 190]].map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r={Math.max(8, size / 6)} fill={CREAM} />
      ))}
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
            {s <= 32 ? <MiniMark size={s} /> : <Mark size={s} glow={false} />}
          </div>
          <div className="nyxus-eyebrow" style={{ marginTop: 12 }}>{s}px</div>
        </div>
      ))}
    </div>
  );
}

export function ConstellationN() {
  return (
    <div className="nyxus-stage" style={{ padding: '64px 72px' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 56 }}>
        <div>
          <div className="nyxus-eyebrow">NYXUS · Mascot Concept · 03</div>
          <h1 style={{ fontSize: 64, fontWeight: 800, margin: '12px 0 4px', letterSpacing: '-0.03em' }}>
            The Constellation N
          </h1>
          <div className="nyxus-script" style={{ fontSize: 32, color: 'rgba(244,234,213,0.7)' }}>
            a letter written in stars.
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
      <section className="nyxus-card" style={{ padding: '80px 0', marginBottom: 48, display: 'flex', justifyContent: 'center', alignItems: 'center', flexDirection: 'column', gap: 32, position: 'relative', overflow: 'hidden' }}>
        {/* Faint background star field */}
        <svg style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', opacity: 0.18 }}>
          {Array.from({ length: 60 }).map((_, i) => (
            <circle
              key={i}
              cx={`${(i * 137.5) % 100}%`}
              cy={`${(i * 73.3) % 100}%`}
              r={Math.random() > 0.85 ? 1.4 : 0.6}
              fill={CREAM}
              opacity={0.4 + (i % 5) * 0.12}
            />
          ))}
        </svg>
        <Mark size={320} glow />
        <div style={{ textAlign: 'center', maxWidth: 580, position: 'relative' }}>
          <div style={{ fontSize: 14, lineHeight: 1.7, color: 'rgba(244,234,213,0.75)' }}>
            The letter N drawn as four cream stars connected by hairline strokes — like a chart from
            an astronomer's notebook. Letter-mark and celestial sign in one. Ownable forever.
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
              <g stroke="#0a0a0a" strokeWidth="1.2" strokeOpacity="0.7" strokeLinecap="round">
                <line x1="50" y1="50" x2="50" y2="190" />
                <line x1="50" y1="50" x2="190" y2="190" />
                <line x1="190" y1="50" x2="190" y2="190" />
              </g>
              {STARS.map((s) => (
                <circle key={s.key} cx={s.x} cy={s.y} r={s.r} fill="#0a0a0a" />
              ))}
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
            navigate by the stars.
          </div>
        </div>
        <div style={{ textAlign: 'right', fontFamily: 'JetBrains Mono', fontSize: 11, color: 'var(--cream-dim)', letterSpacing: '0.1em', lineHeight: 1.8 }}>
          PRIMARY LOCKUP<br />
          HORIZONTAL · L
        </div>
      </section>

      {/* Size matrix */}
      <section className="nyxus-card" style={{ padding: '32px 48px', marginBottom: 48 }}>
        <div className="nyxus-eyebrow" style={{ marginBottom: 8 }}>Below 32px the simplified 4-star version takes over · automatic</div>
        <SizeRow />
      </section>

      {/* Boot animation */}
      <section className="nyxus-card" style={{ padding: 40, marginBottom: 48 }}>
        <div className="nyxus-eyebrow" style={{ marginBottom: 24 }}>Plymouth boot reveal — stars appear, then connect</div>
        <div style={{ background: '#000', borderRadius: 3, padding: '64px 0', display: 'flex', justifyContent: 'center', position: 'relative', overflow: 'hidden' }}>
          <svg style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', opacity: 0.25 }}>
            {Array.from({ length: 80 }).map((_, i) => (
              <circle key={i} cx={`${(i * 53.7) % 100}%`} cy={`${(i * 91.1) % 100}%`} r={Math.random() > 0.8 ? 1.2 : 0.5} fill={CREAM} opacity={0.5} />
            ))}
          </svg>
          <Mark size={200} glow animate />
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
            <li>Letter-mark + celestial sign in one. <em style={{ color: CREAM }}>Two ideas, one shape.</em></li>
            <li>Reads as N at any size — but also as a constellation, a navigation aid, a star chart.</li>
            <li>Reinforces the night theme without being literal (no moons, no owls).</li>
            <li>Plymouth boot is breathtaking: stars fade in one by one, then lines connect them. Premium product opening.</li>
            <li>Auto-simplifies below 32px to a chunky 4-corner glyph — favicon-safe.</li>
          </ul>
        </div>
        <div className="nyxus-card" style={{ padding: 32, fontFamily: 'JetBrains Mono', fontSize: 12, lineHeight: 2, color: 'rgba(244,234,213,0.7)' }}>
          <div className="nyxus-eyebrow" style={{ marginBottom: 18, fontFamily: 'JetBrains Mono' }}>Build spec</div>
          <div>geometry  &nbsp;→&nbsp; 5 stars + 3 lines (N)</div>
          <div>fill      &nbsp;→&nbsp; #f4ead5 dots + hairlines</div>
          <div>radius    &nbsp;→&nbsp; n/a (point geometry)</div>
          <div>min size  &nbsp;→&nbsp; 16×16 (4-star simplified)</div>
          <div>animation &nbsp;→&nbsp; star-in 0.5s · line-draw 1.6s</div>
          <div>files     &nbsp;→&nbsp; svg · png 16/32/64/128/256/512</div>
        </div>
      </section>

      <footer style={{ marginTop: 56, paddingTop: 24, borderTop: '1px solid var(--cream-line)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div className="nyxus-script" style={{ fontSize: 22, color: 'rgba(244,234,213,0.55)' }}>look up. that's us.</div>
        <div className="nyxus-eyebrow">CONCEPT 03 · CONSTELLATION N</div>
      </footer>
    </div>
  );
}
