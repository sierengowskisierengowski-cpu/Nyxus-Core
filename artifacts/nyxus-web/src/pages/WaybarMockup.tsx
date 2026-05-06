import { useEffect, useRef, useState } from "react";

const BASE = "/api/download/nyxus";
const v = `?v=${Date.now()}`;

const CREAM_BASE      = "#f5f3ef";
const CREAM_RAISED    = "#fbfaf6";
const CHARCOAL        = "#1a1816";
const PENCIL_LIGHT    = "#58524c";
const GOLD            = "#d4a73a";
const GOLD_GLOW       = "rgba(212,167,58,0.55)";

const STRIPES = [
  { name: "pink",   rgb: "236, 72,153" },
  { name: "orange", rgb: "234,126, 60" },
  { name: "gold",   rgb: "212,167, 58" },
  { name: "green",  rgb: "106,168,114" },
  { name: "blue",   rgb: " 90,138,171" },
  { name: "purple", rgb: "138,106,170" },
];

const EMBOSS_OUT =
  "inset 1px 1px 0 rgba(255,255,255,0.95), inset -1px -1px 0 rgba(26,24,22,0.06), inset 0 -2px 0 rgba(26,24,22,0.06), 4px 4px 10px rgba(26,24,22,0.18), -3px -3px 8px rgba(255,255,255,0.90)";
const EMBOSS_BORDER = "1px solid rgba(26,24,22,0.22)";
const EMBOSS_IN =
  "inset 2px 2px 6px rgba(26,24,22,0.18), inset -2px -2px 6px rgba(255,255,255,0.90)";
const ENGRAVED =
  "0 1px 0 rgba(255,255,255,0.85), 0 -1px 0 rgba(26,24,22,0.18)";
const GOLD_ENGRAVED =
  `0 1px 0 rgba(255,255,255,0.85), 0 -1px 0 rgba(26,24,22,0.35), 0 0 12px ${GOLD_GLOW}, 0 0 24px ${GOLD_GLOW}`;

function ClayButton({
  children,
  active,
  stripe,
  style,
}: {
  children: React.ReactNode;
  active?: boolean;
  stripe?: string;
  style?: React.CSSProperties;
}) {
  return (
    <div
      style={{
        background: CREAM_RAISED,
        margin: "8px 5px",
        padding: "6px 14px",
        borderRadius: 12,
        border: EMBOSS_BORDER,
        boxShadow: active ? EMBOSS_IN : EMBOSS_OUT,
        color: CHARCOAL,
        fontFamily: "'Inter', sans-serif",
        fontSize: 13,
        textShadow: ENGRAVED,
        position: "relative",
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        ...style,
      }}
    >
      {stripe && (
        <span
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            bottom: 0,
            height: 3,
            borderBottomLeftRadius: 12,
            borderBottomRightRadius: 12,
            background: `rgba(${stripe}, ${active ? 0.95 : 0.55})`,
          }}
        />
      )}
      {children}
    </div>
  );
}

function RainbowText({ text, size = 14 }: { text: string; size?: number }) {
  return (
    <span
      style={{
        fontFamily: "'Architects Daughter', 'Caveat', cursive",
        fontSize: size,
        textShadow: ENGRAVED,
      }}
    >
      {text.split("").map((ch, i) => (
        <span
          key={i}
          style={{
            color: `rgba(${STRIPES[i % STRIPES.length].rgb}, 0.95)`,
          }}
        >
          {ch}
        </span>
      ))}
    </span>
  );
}

// Live fog waybars (rev 2026-05-06j). Canvas particle fog mirrors
// nyxus-fog.py 1:1 — same blob count (14/bar), same palette weights,
// same speed/radius ranges, same wobble. Render path: HTMLCanvas →
// radial-gradient blobs that drift, wobble, wrap edges. Stays exactly
// in sync with what the Python daemon paints under the real waybar.
const MISTY_GLOW =
  "inset 0 0 2px 0 rgba(255,255,255,1.0), inset 0 0 6px 1px rgba(255,255,255,0.85), inset 0 0 14px 3px rgba(255,255,255,0.60), inset 0 0 28px 6px rgba(255,255,255,0.40), inset 0 0 56px 12px rgba(255,255,255,0.22)";

// ── PALETTE (mirror nyxus-fog.py COLOR_BAG weights) ──
type RGB = [number, number, number];
const COLOR_WHITE: RGB      = [255, 255, 255];
const COLOR_OFFWHITE: RGB   = [251, 250, 246];
const COLOR_CREAM_BASE: RGB = [245, 243, 239];
const COLOR_GOLD: RGB       = [212, 167, 58];
const COLOR_BAG: RGB[] = [
  ...Array(5).fill(COLOR_WHITE),
  ...Array(4).fill(COLOR_OFFWHITE),
  ...Array(2).fill(COLOR_CREAM_BASE),
  ...Array(2).fill(COLOR_GOLD),
];

const BLOBS_PER_BAR = 14;
const FPS_TARGET    = 30;

interface Blob {
  x: number; y: number;
  vx: number; vy: number;
  wPhase: number; wSpeed: number;
  radius: number; alpha: number;
  color: RGB;
  isGold: boolean;
}

function makeBlob(w: number, h: number): Blob {
  const speed = 0.18 + Math.random() * 0.47;
  const angle = Math.random() * Math.PI * 2;
  const color = COLOR_BAG[Math.floor(Math.random() * COLOR_BAG.length)];
  const isGold = color === COLOR_GOLD;
  const scale = Math.max(28, Math.min(w, h));
  return {
    x: Math.random() * w,
    y: Math.random() * h,
    vx: Math.cos(angle) * speed,
    vy: Math.sin(angle) * speed,
    wPhase: Math.random() * Math.PI * 2,
    wSpeed: 0.006 + Math.random() * 0.016,
    radius: scale * (1.4 + Math.random() * 1.8),
    alpha: isGold
      ? 0.10 + Math.random() * 0.12
      : 0.22 + Math.random() * 0.33,
    color,
    isGold,
  };
}

function FogCanvas({ width, height }: { width: number; height: number }) {
  const ref = useRef<HTMLCanvasElement | null>(null);
  const blobsRef = useRef<Blob[]>([]);
  const rafRef = useRef<number | null>(null);
  const lastTickRef = useRef<number>(0);

  useEffect(() => {
    const cvs = ref.current;
    if (!cvs) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    cvs.width  = Math.max(1, Math.floor(width  * dpr));
    cvs.height = Math.max(1, Math.floor(height * dpr));
    const ctx = cvs.getContext("2d");
    if (!ctx) return;
    ctx.scale(dpr, dpr);
    blobsRef.current = Array.from({ length: BLOBS_PER_BAR },
                                  () => makeBlob(width, height));

    const frameMs = 1000 / FPS_TARGET;
    const loop = (now: number) => {
      if (now - lastTickRef.current >= frameMs) {
        lastTickRef.current = now;
        // Update
        for (const b of blobsRef.current) {
          b.wPhase += b.wSpeed;
          const wob = Math.sin(b.wPhase) * 0.20;
          b.x += b.vx + wob;
          b.y += b.vy + wob * 0.4;
          const m = b.radius;
          if (b.x < -m) b.x = width  + m;
          else if (b.x > width  + m) b.x = -m;
          if (b.y < -m) b.y = height + m;
          else if (b.y > height + m) b.y = -m;
        }
        // Draw
        ctx.clearRect(0, 0, width, height);
        ctx.globalCompositeOperation = "source-over";
        for (const b of blobsRef.current) {
          const grad = ctx.createRadialGradient(b.x, b.y, 0, b.x, b.y, b.radius);
          const [r, g, bl] = b.color;
          grad.addColorStop(0.00, `rgba(${r},${g},${bl},${b.alpha.toFixed(3)})`);
          grad.addColorStop(0.45, `rgba(${r},${g},${bl},${(b.alpha * 0.40).toFixed(3)})`);
          grad.addColorStop(1.00, `rgba(${r},${g},${bl},0)`);
          ctx.fillStyle = grad;
          ctx.fillRect(b.x - b.radius, b.y - b.radius, b.radius * 2, b.radius * 2);
        }
      }
      rafRef.current = requestAnimationFrame(loop);
    };
    rafRef.current = requestAnimationFrame(loop);
    return () => {
      if (rafRef.current != null) cancelAnimationFrame(rafRef.current);
    };
  }, [width, height]);

  return (
    <canvas
      ref={ref}
      style={{
        position: "absolute",
        inset: 0,
        width:  "100%",
        height: "100%",
        pointerEvents: "none",
      }}
      aria-hidden
    />
  );
}

function BarShell({
  position,
  style,
  children,
}: {
  position: "top" | "bottom" | "left" | "right";
  bg?: string;
  style?: React.CSSProperties;
  children?: React.ReactNode;
}) {
  // Read width/height from style (numeric) so the canvas can size itself.
  const w = Number(style?.width  ?? 0) || 0;
  const h = Number(style?.height ?? 0) || 0;
  return (
    <div
      style={{
        position: "absolute",
        backgroundColor: "rgba(255,255,255,0.18)",
        backdropFilter: "blur(12px) saturate(110%)",
        WebkitBackdropFilter: "blur(12px) saturate(110%)",
        display: "flex",
        alignItems: "center",
        border: "1px solid rgba(255,255,255,1.0)",
        boxShadow: MISTY_GLOW,
        overflow: "hidden",   // clip fog to bar bounds (matches layer-shell)
        ...style,
      }}
      data-bar={position}
    >
      {w > 0 && h > 0 && <FogCanvas width={w} height={h} />}
      <div style={{ position: "relative", display: "flex", alignItems: "center", width: "100%", height: "100%" }}>
        {children}
      </div>
    </div>
  );
}

export default function WaybarMockup() {
  const [showLabels, setShowLabels] = useState(true);
  const [topMode, setTopMode] = useState<"gold" | "rainbow">("gold");

  return (
    <div
      style={{
        minHeight: "100vh",
        background: CREAM_BASE,
        padding: "32px 24px 64px",
        fontFamily: "'Inter', sans-serif",
        color: CHARCOAL,
      }}
    >
      <header style={{ maxWidth: 1376, margin: "0 auto 20px" }}>
        <h1
          style={{
            fontFamily: "'Architects Daughter', 'Caveat', cursive",
            fontSize: 42,
            margin: 0,
            color: GOLD,
            textShadow: GOLD_ENGRAVED,
            letterSpacing: 1,
          }}
        >
          NYXUS Waybar Mockup
        </h1>
        <p style={{ color: PENCIL_LIGHT, marginTop: 6, fontSize: 14 }}>
          Live reference of the embossed-cream-paper desktop. Pulls real
          textures + wallpaper from the API server. Edit{" "}
          <code>artifacts/nyxus-web/src/pages/WaybarMockup.tsx</code> to iterate.
        </p>

        <div style={{ display: "flex", gap: 12, marginTop: 16, flexWrap: "wrap" }}>
          <button
            onClick={() => setTopMode(topMode === "gold" ? "rainbow" : "gold")}
            style={{
              ...buttonStyle,
              boxShadow: EMBOSS_OUT,
            }}
          >
            Top wordmark: <strong>{topMode === "gold" ? "GOLD" : "RAINBOW"}</strong>
          </button>
          <button
            onClick={() => setShowLabels(!showLabels)}
            style={{
              ...buttonStyle,
              boxShadow: EMBOSS_OUT,
            }}
          >
            Module labels: <strong>{showLabels ? "ON" : "OFF"}</strong>
          </button>
          <a
            href="#/"
            style={{
              ...buttonStyle,
              boxShadow: EMBOSS_OUT,
              textDecoration: "none",
              color: CHARCOAL,
            }}
          >
            ← Back to portal
          </a>
        </div>
      </header>

      {/* DESKTOP CANVAS — 1376x768 (16:9 native res) */}
      <div
        style={{
          position: "relative",
          width: "100%",
          maxWidth: 1376,
          margin: "0 auto",
          aspectRatio: "1376 / 768",
          backgroundImage: `url(${BASE}/nyxus-frost-sierengowski.png${v})`,
          backgroundSize: "cover",
          backgroundPosition: "center",
          borderRadius: 16,
          overflow: "hidden",
          boxShadow:
            "0 12px 32px rgba(26,24,22,0.25), inset 1px 1px 0 rgba(255,255,255,0.6)",
          border: "1px solid rgba(26,24,22,0.18)",
        }}
      >
        {/* TOP BAR — NYXUS gold wordmark */}
        <BarShell
          position="top"
          bg="nyxus-waybar-top.png"
          style={{
            top: 0,
            left: 0,
            right: 0,
            height: "10.5%", // ~80px @ 768
            justifyContent: "space-between",
            padding: "0 16px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <ClayButton>󰣇</ClayButton>
            {showLabels &&
              ["Files", "Term", "Code", "Web"].map((t) => (
                <ClayButton key={t}>
                  <RainbowText text={t} />
                </ClayButton>
              ))}
          </div>

          {/* GOLD NYXUS WORDMARK */}
          <div
            style={{
              fontFamily: "'Architects Daughter', 'Caveat', cursive",
              fontSize: 32,
              fontWeight: 700,
              letterSpacing: 6,
              color: topMode === "gold" ? GOLD : "transparent",
              textShadow:
                topMode === "gold"
                  ? GOLD_ENGRAVED
                  : "0 1px 0 rgba(255,255,255,0.85), 0 -1px 0 rgba(26,24,22,0.35)",
              backgroundImage:
                topMode === "rainbow"
                  ? `linear-gradient(90deg, rgba(${STRIPES[0].rgb},1), rgba(${STRIPES[1].rgb},1), rgba(${STRIPES[2].rgb},1), rgba(${STRIPES[3].rgb},1), rgba(${STRIPES[4].rgb},1), rgba(${STRIPES[5].rgb},1))`
                  : "none",
              WebkitBackgroundClip: topMode === "rainbow" ? "text" : "border-box",
              WebkitTextFillColor:
                topMode === "rainbow" ? "transparent" : "currentColor",
            }}
          >
            NYXUS
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
            {showLabels && (
              <>
                <ClayButton>
                  <RainbowText text="84°" />
                </ClayButton>
                <ClayButton>
                  <RainbowText text="WiFi" />
                </ClayButton>
                <ClayButton>
                  <RainbowText text="Bat 92%" />
                </ClayButton>
              </>
            )}
            <ClayButton>
              <span style={{ color: GOLD, textShadow: GOLD_ENGRAVED }}>●</span>
            </ClayButton>
          </div>
        </BarShell>

        {/* LEFT BAR */}
        <BarShell
          position="left"
          bg="nyxus-waybar-left.png"
          style={{
            top: "12%",
            bottom: "12%",
            left: 0,
            width: "4.6%", // ~64px @ 1376
            flexDirection: "column",
            justifyContent: "flex-start",
            paddingTop: 12,
            gap: 4,
          }}
        >
          {STRIPES.slice(0, 6).map((s, i) => (
            <ClayButton
              key={s.name}
              active={i === 0}
              stripe={s.rgb}
              style={{ margin: "4px 0", padding: "8px 0", width: 36, justifyContent: "center" }}
            >
              <span
                style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 11,
                }}
              >
                {i + 1}
              </span>
            </ClayButton>
          ))}
        </BarShell>

        {/* RIGHT BAR */}
        <BarShell
          position="right"
          bg="nyxus-waybar-right.png"
          style={{
            top: "12%",
            bottom: "12%",
            right: 0,
            width: "5.2%", // ~72px @ 1376
            flexDirection: "column",
            justifyContent: "flex-start",
            paddingTop: 12,
            gap: 4,
          }}
        >
          {["", "", "", "", "", ""].map((ic, i) => (
            <ClayButton
              key={i}
              style={{ margin: "4px 0", padding: "8px 0", width: 44, justifyContent: "center" }}
            >
              <span style={{ fontSize: 14 }}>{ic}</span>
            </ClayButton>
          ))}
        </BarShell>

        {/* BOTTOM BAR — hyprland glow wordmark */}
        <BarShell
          position="bottom"
          bg="nyxus-waybar-bottom.png"
          style={{
            bottom: 0,
            left: 0,
            right: 0,
            height: "9.5%", // ~73px @ 768
            justifyContent: "space-between",
            padding: "0 16px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
            {showLabels && (
              <>
                <ClayButton>
                  <RainbowText text="CPU 12%" size={12} />
                </ClayButton>
                <ClayButton>
                  <RainbowText text="MEM 4.2G" size={12} />
                </ClayButton>
                <ClayButton>
                  <RainbowText text="GPU 38°" size={12} />
                </ClayButton>
              </>
            )}
          </div>

          {/* HYPRLAND GOLD GLOW WORDMARK */}
          <div
            style={{
              fontFamily: "'Architects Daughter', 'Caveat', cursive",
              fontSize: 22,
              fontWeight: 700,
              letterSpacing: 4,
              color: GOLD,
              textShadow: GOLD_ENGRAVED,
            }}
          >
            hyprland
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
            {showLabels && (
              <>
                <ClayButton>
                  <RainbowText text="♪ Music" size={12} />
                </ClayButton>
                <ClayButton>
                  <RainbowText text="14:32" size={12} />
                </ClayButton>
              </>
            )}
          </div>
        </BarShell>
      </div>

      {/* CHEAT SHEET */}
      <section
        style={{
          maxWidth: 1376,
          margin: "32px auto 0",
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
          gap: 16,
        }}
      >
        {[
          {
            title: "Cream palette",
            body: (
              <Swatches
                items={[
                  ["base", CREAM_BASE],
                  ["raised", CREAM_RAISED],
                  ["highlight", "#ffffff"],
                  ["shadow", "#ebe8e2"],
                  ["deep shadow", "#ddd9d3"],
                ]}
              />
            ),
          },
          {
            title: "Ink palette",
            body: (
              <Swatches
                items={[
                  ["pencil ink", CHARCOAL],
                  ["pencil light", PENCIL_LIGHT],
                  ["pencil faint", "#9e948a"],
                ]}
              />
            ),
          },
          {
            title: "Workspace stripes",
            body: (
              <Swatches
                items={STRIPES.map((s) => [s.name, `rgba(${s.rgb},0.95)`])}
              />
            ),
          },
          {
            title: "Gold accent (LOCKED)",
            body: (
              <div>
                <Swatches items={[["gold", GOLD]]} />
                <p style={{ fontSize: 11, color: PENCIL_LIGHT, marginTop: 8 }}>
                  Wordmarks, focused-ws ring, notif dot, now-playing.
                  Never on surfaces or fills.
                </p>
              </div>
            ),
          },
          {
            title: "Fonts",
            body: (
              <ul style={{ fontSize: 12, color: PENCIL_LIGHT, paddingLeft: 18, margin: 0 }}>
                <li><span style={{ fontFamily: "'Architects Daughter', cursive", color: CHARCOAL }}>Architects Daughter</span> — labels, wordmarks</li>
                <li><span style={{ color: CHARCOAL }}>Inter</span> — system text, stats</li>
                <li><span style={{ fontFamily: "'JetBrains Mono', monospace", color: CHARCOAL }}>JetBrains Mono</span> — workspace nums, code</li>
              </ul>
            ),
          },
          {
            title: "Bar dimensions",
            body: (
              <ul style={{ fontSize: 12, color: PENCIL_LIGHT, paddingLeft: 18, margin: 0 }}>
                <li>Top: 80px tall × full width</li>
                <li>Bottom: 73px tall × full width</li>
                <li>Left: 64px wide × center 75%</li>
                <li>Right: 72px wide × center 75%</li>
                <li>All shells transparent + per-bar bg image + 0.35 white veil</li>
              </ul>
            ),
          },
        ].map((card) => (
          <div
            key={card.title}
            style={{
              background: CREAM_RAISED,
              padding: 16,
              borderRadius: 12,
              boxShadow: EMBOSS_OUT,
            }}
          >
            <h3
              style={{
                fontFamily: "'Architects Daughter', 'Caveat', cursive",
                fontSize: 18,
                margin: "0 0 12px",
                color: CHARCOAL,
                textShadow: ENGRAVED,
              }}
            >
              {card.title}
            </h3>
            {card.body}
          </div>
        ))}
      </section>
    </div>
  );
}

function Swatches({ items }: { items: [string, string][] }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      {items.map(([name, hex]) => (
        <div key={name} style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span
            style={{
              width: 24,
              height: 24,
              background: hex,
              borderRadius: 6,
              border: "1px solid rgba(26,24,22,0.22)",
              boxShadow: "inset 1px 1px 0 rgba(255,255,255,0.6)",
              flexShrink: 0,
            }}
          />
          <span style={{ fontSize: 11, color: CHARCOAL }}>{name}</span>
          <span style={{ fontSize: 10, color: PENCIL_LIGHT, fontFamily: "'JetBrains Mono', monospace", marginLeft: "auto" }}>
            {hex}
          </span>
        </div>
      ))}
    </div>
  );
}

const buttonStyle: React.CSSProperties = {
  background: CREAM_RAISED,
  border: "none",
  padding: "8px 14px",
  borderRadius: 10,
  fontFamily: "'Inter', sans-serif",
  fontSize: 12,
  color: CHARCOAL,
  cursor: "pointer",
  textShadow: ENGRAVED,
};
