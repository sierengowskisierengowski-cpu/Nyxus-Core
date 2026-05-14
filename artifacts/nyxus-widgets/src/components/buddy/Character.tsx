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
          <stop offset="0%" stopColor="#16161c" />
          <stop offset="55%" stopColor={INK} />
          <stop offset="100%" stopColor={INK_DEEP} />
        </radialGradient>
        <radialGradient id="hoodVoid" cx="0.5" cy="0.45" r="0.55">
          <stop offset="0%" stopColor="#000" />
          <stop offset="60%" stopColor="#000" stopOpacity="0.85" />
          <stop offset="100%" stopColor="#000" stopOpacity="0" />
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

      {/* LIFT layer — applies vertical hover for `float` state */}
      <motion.g animate={lift}>
        {/* BODY (cloak silhouette) — anchor for hood + sleeves + hem */}
        <motion.g animate={body} style={{ transformOrigin: "0px 130px" }}>
          {/* Cloak silhouette: tapered teardrop from hood to ground.
              Wider at the base for that flowing-pile-of-shadow look. */}
          <path
            d="
              M -32 50
              Q -42 90 -50 150
              Q -62 200 -56 220
              L 56 220
              Q 62 200 50 150
              Q 42 90 32 50
              Q 0 36 -32 50
              Z
            "
            fill="url(#cloakGrad)"
            stroke={COPPER}
            strokeOpacity="0.35"
            strokeWidth="1"
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

          {/* HEM — bottom edge wave that flows */}
          <motion.g animate={hem} style={{ transformOrigin: "0px 220px" }}>
            <path
              d="
                M -56 220
                Q -42 214 -28 220
                Q -14 226 0 220
                Q 14 214 28 220
                Q 42 226 56 220
                L 56 224
                L -56 224 Z
              "
              fill={INK_DEEP}
              stroke={COPPER}
              strokeOpacity="0.4"
              strokeWidth="0.8"
            />
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

          {/* HOOD — large rounded drape that hides the head */}
          <motion.g animate={hood} style={{ transformOrigin: "0px 70px" }}>
            {/* Hood shell */}
            <path
              d="
                M -38 50
                Q -50 30 -42 8
                Q -22 -10 0 -10
                Q 22 -10 42 8
                Q 50 30 38 50
                Q 28 62 12 62
                L -12 62
                Q -28 62 -38 50 Z
              "
              fill="url(#cloakGrad)"
              stroke={COPPER}
              strokeOpacity="0.55"
              strokeWidth="1.2"
            />
            {/* Hood opening — void where face should be */}
            <ellipse cx="0" cy="40" rx="26" ry="20" fill="url(#hoodVoid)" />
            <ellipse
              cx="0"
              cy="40"
              rx="26"
              ry="20"
              fill="none"
              stroke="url(#copperRim)"
              strokeOpacity="0.5"
              strokeWidth="1"
            />

            {/* EYES — the ONLY visible face feature.
                Outer soft glow + inner bright slit. */}
            <motion.g animate={eyeGlow} style={{ opacity: talkBoost }}>
              {/* outer halo (blurred) */}
              <g filter="url(#eyeBlurSoft)">
                <ellipse cx="-9" cy="42" rx="9" ry="5" fill={eyeTint} opacity="0.55" />
                <ellipse cx="9" cy="42" rx="9" ry="5" fill={eyeTint} opacity="0.55" />
              </g>
              {/* mid glow */}
              <g filter="url(#eyeBlur)">
                <ellipse cx="-9" cy="42" rx="6" ry="3.2" fill={eyeTint} opacity="0.85" />
                <ellipse cx="9" cy="42" rx="6" ry="3.2" fill={eyeTint} opacity="0.85" />
              </g>
              {/* sharp eye shape — narrows for curious / smug / sleepy / sleep */}
              <motion.g animate={eyeShape} style={{ transformOrigin: "0px 42px" }}>
                <g style={{ transform: `scaleY(${baseEyeScale})`, transformOrigin: "center" }}>
                  <ellipse
                    cx="-9"
                    cy="42"
                    rx="4.2"
                    ry="2.1"
                    fill={CREAM}
                  />
                  <ellipse
                    cx="9"
                    cy="42"
                    rx="4.2"
                    ry="2.1"
                    fill={CREAM}
                  />
                </g>
              </motion.g>
              {/* hot core */}
              <ellipse cx="-9" cy="42" rx="1.4" ry="0.9" fill="#fffaea" />
              <ellipse cx="9" cy="42" rx="1.4" ry="0.9" fill="#fffaea" />
            </motion.g>

            {/* Hood front lip — copper line catching the light */}
            <path
              d="M -38 50 Q 0 60 38 50"
              fill="none"
              stroke="url(#copperRim)"
              strokeOpacity="0.55"
              strokeWidth="1"
            />
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
