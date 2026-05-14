import { motion, useAnimationControls } from "framer-motion";
import { useEffect, useMemo } from "react";
import type { BuddyState, Mood } from "./types";

interface CharacterProps {
  state: BuddyState;
  mood: Mood;
  mouthOpen: number; // reused as "talk intensity" → drives eye-glow pulse
  facing: 1 | -1;
}

const INK = "#0a0a0e";
const INK_DEEP = "#06060a";
const COPPER = "#b8865a";
const COPPER_BRIGHT = "#d9a877";
const CREAM = "#f4ead5";

export function Character({ state, mood, mouthOpen, facing }: CharacterProps) {
  const hood = useAnimationControls();
  const body = useAnimationControls();
  const lift = useAnimationControls();
  const eyeGlow = useAnimationControls();
  const eyeShape = useAnimationControls();
  const hem = useAnimationControls();
  const sleeveL = useAnimationControls();
  const sleeveR = useAnimationControls();

  // Idle ambient — slow sway + faint cloak ripple + slow eye-glow pulse
  const breath = useMemo(
    () => ({
      rotate: [-1.5, 1.5, -1.5],
      transition: { duration: 5.5, repeat: Infinity, ease: "easeInOut" as const },
    }),
    [],
  );
  const hemWaveIdle = useMemo(
    () => ({
      skewX: [-2, 2, -2],
      transition: { duration: 4.2, repeat: Infinity, ease: "easeInOut" as const },
    }),
    [],
  );
  const glowIdle = useMemo(
    () => ({
      opacity: [0.75, 1, 0.75],
      transition: { duration: 3.6, repeat: Infinity, ease: "easeInOut" as const },
    }),
    [],
  );

  useEffect(() => {
    body.start(breath);
    hem.start(hemWaveIdle);
    eyeGlow.start(glowIdle);
    eyeShape.start({ scaleY: 1, transition: { duration: 0.3 } });
  }, [body, hem, eyeGlow, breath, hemWaveIdle, glowIdle, eyeShape]);

  useEffect(() => {
    switch (state) {
      case "wave":
        sleeveR.start({
          rotate: [0, -120, -100, -120, -100, 0],
          x: [0, 4, 4, 4, 4, 0],
          transition: { duration: 1.9, ease: "easeInOut" as const },
        });
        hood.start({
          rotate: [0, -6, 0],
          transition: { duration: 1.9, ease: "easeInOut" as const },
        });
        eyeGlow.start({
          opacity: [0.85, 1.1, 0.85],
          transition: { duration: 0.8, repeat: 2, ease: "easeInOut" as const },
        });
        break;

      case "walk-left":
      case "walk-right": {
        // VEIL glides — no leg cycle, just hover-bob and hem flow
        body.start({
          y: [0, -3, 0, -3, 0],
          transition: { duration: 0.8, repeat: Infinity, ease: "easeInOut" as const },
        });
        hem.start({
          skewX: [-6, 6, -6],
          transition: { duration: 0.8, repeat: Infinity, ease: "easeInOut" as const },
        });
        sleeveL.start({
          rotate: [0, -8, 0],
          transition: { duration: 0.8, repeat: Infinity, ease: "easeInOut" as const },
        });
        sleeveR.start({
          rotate: [0, 8, 0],
          transition: { duration: 0.8, repeat: Infinity, ease: "easeInOut" as const },
        });
        break;
      }

      case "dance":
        body.start({
          rotate: [-8, 8, -8],
          y: [0, -10, 0, -10, 0],
          transition: { duration: 0.7, repeat: Infinity, ease: "easeInOut" as const },
        });
        hood.start({
          rotate: [10, -10, 10],
          transition: { duration: 0.7, repeat: Infinity, ease: "easeInOut" as const },
        });
        sleeveL.start({
          rotate: [-50, 50, -50],
          transition: { duration: 0.7, repeat: Infinity, ease: "easeInOut" as const },
        });
        sleeveR.start({
          rotate: [50, -50, 50],
          transition: { duration: 0.7, repeat: Infinity, ease: "easeInOut" as const },
        });
        hem.start({
          skewX: [-12, 12, -12],
          transition: { duration: 0.7, repeat: Infinity, ease: "easeInOut" as const },
        });
        break;

      case "laugh":
        // Throws hood back, eyes flash bright
        hood.start({
          rotate: [0, -22, -18, -22, 0],
          y: [0, -6, -4, -6, 0],
          transition: { duration: 1.6, ease: "easeInOut" as const },
        });
        body.start({
          rotate: [0, 4, -2, 4, 0],
          transition: { duration: 1.6, ease: "easeInOut" as const },
        });
        eyeGlow.start({
          opacity: [1, 1.4, 1.1, 1.4, 1],
          transition: { duration: 1.6, ease: "easeInOut" as const },
        });
        sleeveL.start({
          rotate: [0, -30, -20, -30, 0],
          transition: { duration: 1.6, ease: "easeInOut" as const },
        });
        sleeveR.start({
          rotate: [0, 30, 20, 30, 0],
          transition: { duration: 1.6, ease: "easeInOut" as const },
        });
        break;

      case "curious":
        // Head tilt, eyes narrow
        hood.start({
          rotate: 14,
          x: 6,
          transition: { duration: 0.5, ease: "easeOut" as const },
        });
        eyeShape.start({
          scaleY: 0.35,
          transition: { duration: 0.4, ease: "easeOut" as const },
        });
        eyeGlow.start({
          opacity: [0.95, 1.15, 0.95],
          transition: { duration: 1.4, repeat: Infinity, ease: "easeInOut" as const },
        });
        body.start({ rotate: -2, transition: { duration: 0.4 } });
        break;

      case "float":
        // Levitates — soft halo + slow vertical drift
        lift.start({
          y: [-12, -22, -12],
          transition: { duration: 2.6, repeat: Infinity, ease: "easeInOut" as const },
        });
        hem.start({
          skewX: [-9, 9, -9],
          transition: { duration: 2.6, repeat: Infinity, ease: "easeInOut" as const },
        });
        eyeGlow.start({
          opacity: [1, 1.2, 1],
          transition: { duration: 2.6, repeat: Infinity, ease: "easeInOut" as const },
        });
        break;

      case "sleep":
        // Cross-legged — body shrinks into seated pile, eye glow dims to slow pulse
        hood.start({
          rotate: 10,
          y: 18,
          transition: { duration: 0.6, ease: "easeOut" as const },
        });
        body.start({
          y: 28,
          scaleY: 0.78,
          rotate: 0,
          transition: { duration: 0.6, ease: "easeOut" as const },
        });
        eyeShape.start({ scaleY: 0.18, transition: { duration: 0.6 } });
        eyeGlow.start({
          opacity: [0.18, 0.42, 0.18],
          transition: { duration: 4.5, repeat: Infinity, ease: "easeInOut" as const },
        });
        sleeveL.start({ rotate: -10, x: -2, transition: { duration: 0.6 } });
        sleeveR.start({ rotate: 10, x: 2, transition: { duration: 0.6 } });
        break;

      case "sit":
        body.start({
          y: 24,
          scaleY: 0.85,
          transition: { duration: 0.5, ease: "easeOut" as const },
        });
        sleeveL.start({ rotate: -10, transition: { duration: 0.4 } });
        sleeveR.start({ rotate: 10, transition: { duration: 0.4 } });
        break;

      case "talk":
        // Hood shifts subtly, eyes glow brighter — driven by mouthOpen
        hood.start({
          rotate: [0, 2.5, -2.5, 0],
          transition: { duration: 1.4, repeat: Infinity, ease: "easeInOut" as const },
        });
        sleeveR.start({
          rotate: [0, -12, 0, -8, 0],
          transition: { duration: 2.2, repeat: Infinity, ease: "easeInOut" as const },
        });
        // glow intensity is set inline via eyeShineOpacity below
        break;

      case "idle":
      default:
        hood.start({ rotate: 0, x: 0, y: 0, transition: { duration: 0.5 } });
        body.start({ y: 0, scaleY: 1, rotate: 0, transition: { duration: 0.5 } });
        body.start(breath);
        lift.start({ y: 0, transition: { duration: 0.6 } });
        eyeShape.start({ scaleY: 1, transition: { duration: 0.4 } });
        eyeGlow.start(glowIdle);
        sleeveL.start({ rotate: 0, x: 0, transition: { duration: 0.4 } });
        sleeveR.start({ rotate: 0, x: 0, transition: { duration: 0.4 } });
        hem.start(hemWaveIdle);
        break;
    }
  }, [
    state,
    hood,
    body,
    lift,
    eyeGlow,
    eyeShape,
    hem,
    sleeveL,
    sleeveR,
    breath,
    hemWaveIdle,
    glowIdle,
  ]);

  // Mood-driven eye color tint
  const eyeTint =
    mood === "excited"
      ? CREAM
      : mood === "smug"
        ? COPPER_BRIGHT
        : mood === "sleepy"
          ? "#9c8f73"
          : CREAM;

  // While talking, mouthOpen (0..1) modulates eye glow brightness
  const talkBoost = state === "talk" ? 0.6 + mouthOpen * 0.6 : 1;

  // Mood-narrow on smug
  const baseEyeScale =
    mood === "smug" ? 0.55 : mood === "sleepy" ? 0.3 : state === "curious" ? 0.35 : 1;

  return (
    <svg
      viewBox="-90 -10 180 240"
      width="200"
      height="270"
      style={{
        overflow: "visible",
        filter: `drop-shadow(0 18px 22px rgba(0,0,0,0.6))`,
        transform: `scaleX(${facing})`,
      }}
    >
      <defs>
        <radialGradient id="cloakGrad" cx="0.5" cy="0.2" r="0.95">
          <stop offset="0%" stopColor="#1a1a22" />
          <stop offset="55%" stopColor={INK} />
          <stop offset="100%" stopColor={INK_DEEP} />
        </radialGradient>
        <radialGradient id="hoodVoid" cx="0.5" cy="0.5" r="0.6">
          <stop offset="0%" stopColor="#000" />
          <stop offset="75%" stopColor="#000" stopOpacity="0.95" />
          <stop offset="100%" stopColor="#000" stopOpacity="0" />
        </radialGradient>
        {/* Gold speckle pattern — tiny copper flecks like the reference */}
        <pattern id="goldFleck" x="0" y="0" width="22" height="22" patternUnits="userSpaceOnUse">
          <circle cx="3" cy="5" r="0.45" fill={COPPER_BRIGHT} opacity="0.55" />
          <circle cx="15" cy="9" r="0.3" fill={COPPER} opacity="0.4" />
          <circle cx="8" cy="17" r="0.55" fill={COPPER_BRIGHT} opacity="0.5" />
          <circle cx="19" cy="3" r="0.35" fill={COPPER} opacity="0.45" />
          <circle cx="11" cy="11" r="0.25" fill={COPPER_BRIGHT} opacity="0.3" />
        </pattern>
        {/* Smoke wisps */}
        <radialGradient id="smokeGrad" cx="0.5" cy="0.5" r="0.5">
          <stop offset="0%" stopColor="#3a3a44" stopOpacity="0.5" />
          <stop offset="100%" stopColor="#3a3a44" stopOpacity="0" />
        </radialGradient>
        <radialGradient id="eyeGrad" cx="0.5" cy="0.5" r="0.5">
          <stop offset="0%" stopColor={CREAM} />
          <stop offset="55%" stopColor={CREAM} stopOpacity="0.9" />
          <stop offset="100%" stopColor={CREAM} stopOpacity="0" />
        </radialGradient>
        <radialGradient id="floatHalo" cx="0.5" cy="0.5" r="0.5">
          <stop offset="0%" stopColor={CREAM} stopOpacity="0.4" />
          <stop offset="60%" stopColor={CREAM} stopOpacity="0.08" />
          <stop offset="100%" stopColor={CREAM} stopOpacity="0" />
        </radialGradient>
        <linearGradient id="copperRim" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={COPPER_BRIGHT} />
          <stop offset="100%" stopColor={COPPER} />
        </linearGradient>
        <filter id="eyeBlur" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="2.4" />
        </filter>
        <filter id="eyeBlurSoft" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="5.5" />
        </filter>
      </defs>

      {/* Float halo at base (only visible when floating) */}
      {state === "float" && (
        <motion.g
          animate={{ opacity: [0.4, 0.85, 0.4], scale: [0.85, 1.1, 0.85] }}
          transition={{ duration: 2.6, repeat: Infinity, ease: "easeInOut" as const }}
          style={{ transformOrigin: "0px 220px", transformBox: "fill-box" }}
        >
          <ellipse cx="0" cy="220" rx="58" ry="10" fill="url(#floatHalo)" />
        </motion.g>
      )}

      {/* Ground shadow — fades when floating */}
      <motion.g
        animate={{ opacity: state === "float" ? 0.18 : 0.5, scaleY: state === "float" ? 0.6 : 1 }}
        transition={{ duration: 0.8 }}
        style={{ transformOrigin: "0px 222px", transformBox: "fill-box" }}
      >
        <ellipse cx="0" cy="222" rx="44" ry="5" fill="#000" />
      </motion.g>

      {/* Smoke wisps drifting up around the cloak base */}
      <motion.g
        animate={{ opacity: [0.35, 0.6, 0.35], y: [0, -10, 0] }}
        transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" as const }}
      >
        <ellipse cx="-58" cy="200" rx="22" ry="34" fill="url(#smokeGrad)" />
        <ellipse cx="62" cy="195" rx="20" ry="38" fill="url(#smokeGrad)" />
        <ellipse cx="-32" cy="218" rx="30" ry="14" fill="url(#smokeGrad)" />
        <ellipse cx="38" cy="220" rx="28" ry="14" fill="url(#smokeGrad)" />
      </motion.g>

      {/* LIFT layer — applies vertical hover for `float` state */}
      <motion.g animate={lift}>
        {/* BODY (cloak silhouette) — anchor for hood + sleeves + hem */}
        <motion.g animate={body} style={{ transformOrigin: "0px 130px" }}>
          {/* Cloak silhouette: tapered teardrop from hood to ground.
              Wider at the base for that flowing-pile-of-shadow look. */}
          <path
            d="
              M -32 50
              Q -44 90 -52 150
              Q -66 200 -58 220
              L 58 220
              Q 66 200 52 150
              Q 44 90 32 50
              Q 0 36 -32 50
              Z
            "
            fill="url(#cloakGrad)"
            stroke={COPPER}
            strokeOpacity="0.32"
            strokeWidth="1"
          />
          {/* Gold speckle wash over cloak */}
          <path
            d="
              M -32 50
              Q -44 90 -52 150
              Q -66 200 -58 220
              L 58 220
              Q 66 200 52 150
              Q 44 90 32 50
              Q 0 36 -32 50
              Z
            "
            fill="url(#goldFleck)"
            opacity="0.7"
          />
          {/* Wrapped scarf folds across the chest — like the reference */}
          <path
            d="M -50 110 Q -20 132 30 118 Q 50 114 56 130 Q 30 150 -10 148 Q -42 146 -54 132 Z"
            fill={INK_DEEP}
            stroke={COPPER}
            strokeOpacity="0.35"
            strokeWidth="0.8"
          />
          <path
            d="M -42 140 Q 0 158 48 142 Q 36 168 -6 168 Q -38 166 -42 140 Z"
            fill={INK}
            stroke={COPPER}
            strokeOpacity="0.25"
            strokeWidth="0.6"
            opacity="0.85"
          />

          {/* Inner cloak fold — vertical seam catching cream highlight */}
          <path
            d="M 0 70 Q -2 140 0 215"
            fill="none"
            stroke={CREAM}
            strokeOpacity="0.06"
            strokeWidth="1.5"
          />

          {/* SLEEVES (subtle — show when waving / dancing / laughing) */}
          <motion.g animate={sleeveL} style={{ transformOrigin: "-32px 95px" }}>
            <path
              d="M -32 90 Q -52 120 -48 152 Q -42 156 -36 152 Q -30 120 -28 92 Z"
              fill="url(#cloakGrad)"
              stroke={COPPER}
              strokeOpacity="0.3"
              strokeWidth="0.8"
            />
            {/* sleeve cuff — copper trim hint */}
            <path
              d="M -50 150 Q -42 156 -36 152"
              fill="none"
              stroke={COPPER}
              strokeOpacity="0.55"
              strokeWidth="0.8"
            />
          </motion.g>
          <motion.g animate={sleeveR} style={{ transformOrigin: "32px 95px" }}>
            <path
              d="M 32 90 Q 52 120 48 152 Q 42 156 36 152 Q 30 120 28 92 Z"
              fill="url(#cloakGrad)"
              stroke={COPPER}
              strokeOpacity="0.3"
              strokeWidth="0.8"
            />
            <path
              d="M 50 150 Q 42 156 36 152"
              fill="none"
              stroke={COPPER}
              strokeOpacity="0.55"
              strokeWidth="0.8"
            />
          </motion.g>

          {/* HEM — torn, jagged bottom edge that flows */}
          <motion.g animate={hem} style={{ transformOrigin: "0px 220px" }}>
            <path
              d="
                M -58 220
                L -52 232 L -46 222 L -40 234 L -34 224
                L -26 236 L -20 226 L -14 234 L -8 224
                L 0 236 L 8 226 L 16 234 L 22 224
                L 30 236 L 38 226 L 46 234 L 52 224 L 58 232
                L 58 240 L -58 240 Z
              "
              fill={INK_DEEP}
              stroke={COPPER}
              strokeOpacity="0.4"
              strokeWidth="0.7"
            />
            {/* Loose threads dangling */}
            <path d="M -28 232 L -29 240" stroke={COPPER} strokeOpacity="0.4" strokeWidth="0.5" />
            <path d="M 12 234 L 11 242" stroke={COPPER} strokeOpacity="0.4" strokeWidth="0.5" />
            <path d="M 36 230 L 38 240" stroke={COPPER} strokeOpacity="0.4" strokeWidth="0.5" />
          </motion.g>

          {/* Cross-legged hint when sitting / sleeping */}
          {(state === "sleep" || state === "sit") && (
            <g>
              <ellipse
                cx="-14"
                cy="218"
                rx="14"
                ry="6"
                fill={INK_DEEP}
                stroke={COPPER}
                strokeOpacity="0.5"
                strokeWidth="0.8"
              />
              <ellipse
                cx="14"
                cy="218"
                rx="14"
                ry="6"
                fill={INK_DEEP}
                stroke={COPPER}
                strokeOpacity="0.5"
                strokeWidth="0.8"
              />
            </g>
          )}

          {/* HOOD — large draped fabric that hides the head, torn front edge */}
          <motion.g animate={hood} style={{ transformOrigin: "0px 70px" }}>
            {/* Hood shell — slightly asymmetric, draped */}
            <path
              d="
                M -42 52
                Q -54 30 -46 6
                Q -38 -8 -22 -12
                Q 0 -14 22 -12
                Q 40 -8 46 8
                Q 52 32 40 54
                Q 32 64 14 62
                L -14 62
                Q -30 62 -42 52 Z
              "
              fill="url(#cloakGrad)"
              stroke={COPPER}
              strokeOpacity="0.55"
              strokeWidth="1.1"
            />
            {/* Gold flecks on hood */}
            <path
              d="
                M -42 52
                Q -54 30 -46 6
                Q -38 -8 -22 -12
                Q 0 -14 22 -12
                Q 40 -8 46 8
                Q 52 32 40 54
                Q 32 64 14 62
                L -14 62
                Q -30 62 -42 52 Z
              "
              fill="url(#goldFleck)"
              opacity="0.75"
            />
            {/* Hood opening — deep void where face should be */}
            <ellipse cx="0" cy="42" rx="24" ry="18" fill="url(#hoodVoid)" />
            {/* Inner solid void — pure black so eyes pop */}
            <ellipse cx="0" cy="42" rx="18" ry="13" fill="#000" />
            {/* Torn front edge of hood — jagged drape over forehead */}
            <path
              d="
                M -28 32
                L -22 38 L -16 30 L -10 36 L -2 28
                L 4 36 L 12 30 L 20 38 L 28 32
                L 28 24 L -28 24 Z
              "
              fill={INK_DEEP}
              opacity="0.95"
            />

            {/* EYES — the ONLY visible face feature.
                Outer soft glow + inner bright slit. Amber-cream like the reference. */}
            <motion.g animate={eyeGlow} style={{ opacity: talkBoost }}>
              {/* outer halo (blurred) */}
              <g filter="url(#eyeBlurSoft)">
                <ellipse cx="-8" cy="44" rx="9" ry="5" fill={eyeTint} opacity="0.6" />
                <ellipse cx="8" cy="44" rx="9" ry="5" fill={eyeTint} opacity="0.6" />
              </g>
              {/* mid glow — copper-amber tint */}
              <g filter="url(#eyeBlur)">
                <ellipse cx="-8" cy="44" rx="6" ry="3.2" fill={COPPER_BRIGHT} opacity="0.9" />
                <ellipse cx="8" cy="44" rx="6" ry="3.2" fill={COPPER_BRIGHT} opacity="0.9" />
              </g>
              {/* sharp eye shape — narrows for curious / smug / sleepy / sleep */}
              <motion.g animate={eyeShape} style={{ transformOrigin: "0px 44px" }}>
                <g style={{ transform: `scaleY(${baseEyeScale})`, transformOrigin: "center" }}>
                  <ellipse
                    cx="-8"
                    cy="44"
                    rx="4.2"
                    ry="2.1"
                    fill={CREAM}
                  />
                  <ellipse
                    cx="8"
                    cy="44"
                    rx="4.2"
                    ry="2.1"
                    fill={CREAM}
                  />
                </g>
              </motion.g>
              {/* hot core */}
              <ellipse cx="-8" cy="44" rx="1.4" ry="0.9" fill="#fffaea" />
              <ellipse cx="8" cy="44" rx="1.4" ry="0.9" fill="#fffaea" />
            </motion.g>

            {/* Hood front lip — torn, frayed edge with copper glint */}
            <path
              d="M -42 52 Q -20 62 0 60 Q 20 62 42 54"
              fill="none"
              stroke="url(#copperRim)"
              strokeOpacity="0.5"
              strokeWidth="0.9"
            />
            {/* Loose threads dangling from hood edge */}
            <path d="M -22 60 L -23 68" stroke={COPPER} strokeOpacity="0.45" strokeWidth="0.5" />
            <path d="M 18 60 L 19 67" stroke={COPPER} strokeOpacity="0.45" strokeWidth="0.5" />
            <path d="M 4 62 L 5 69" stroke={COPPER} strokeOpacity="0.4" strokeWidth="0.5" />
          </motion.g>

          {/* Subtle sleep mark — slow Z fades in */}
          {state === "sleep" && (
            <motion.g
              initial={{ y: 0, opacity: 0 }}
              animate={{ y: -28, opacity: [0, 0.7, 0] }}
              transition={{ duration: 3.5, repeat: Infinity, ease: "easeOut" as const }}
            >
              <text
                x="40"
                y="20"
                fill={CREAM}
                fontSize="20"
                fontStyle="italic"
                fontFamily="serif"
                opacity="0.7"
              >
                z
              </text>
            </motion.g>
          )}
        </motion.g>
      </motion.g>
    </svg>
  );
}
