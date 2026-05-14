import { motion, useAnimationControls } from "framer-motion";
import { useEffect, useMemo } from "react";
import veilPng from "@/assets/veil.png";
import type { BuddyState, Mood } from "./types";

interface CharacterProps {
  state: BuddyState;
  mood: Mood;
  mouthOpen: number; // talk intensity → eye-glow brightness modulation
  facing: 1 | -1;
}

const COPPER_BRIGHT = "#d9a877";
const CREAM = "#f4ead5";

// Render container (photo aspect 816×1456 ≈ 0.56)
const W = 260;
const H = 464;

// Eye positions in container coordinates (centered horizontally, ~22% from top)
const EYE_Y = 118;
const EYE_DX = 13;

export function Character({ state, mood, mouthOpen, facing }: CharacterProps) {
  const body = useAnimationControls();
  const lift = useAnimationControls();
  const tilt = useAnimationControls();
  const eyeGlow = useAnimationControls();
  const eyeShape = useAnimationControls();

  const breath = useMemo(
    () => ({
      rotate: [-1.4, 1.4, -1.4],
      transition: { duration: 5.5, repeat: Infinity, ease: "easeInOut" as const },
    }),
    [],
  );
  const glowIdle = useMemo(
    () => ({
      opacity: [0.8, 1, 0.8],
      transition: { duration: 3.6, repeat: Infinity, ease: "easeInOut" as const },
    }),
    [],
  );

  useEffect(() => {
    body.start(breath);
    eyeGlow.start(glowIdle);
    eyeShape.start({ scaleY: 1, transition: { duration: 0.3 } });
  }, [body, eyeGlow, eyeShape, breath, glowIdle]);

  useEffect(() => {
    switch (state) {
      case "wave":
        tilt.start({
          rotate: [0, -6, 0, -4, 0],
          transition: { duration: 1.9, ease: "easeInOut" as const },
        });
        eyeGlow.start({
          opacity: [0.9, 1.4, 0.9],
          transition: { duration: 0.8, repeat: 2, ease: "easeInOut" as const },
        });
        break;

      case "walk-left":
      case "walk-right":
        body.start({
          y: [0, -4, 0, -4, 0],
          transition: { duration: 0.85, repeat: Infinity, ease: "easeInOut" as const },
        });
        tilt.start({
          rotate: [-1, 1, -1],
          transition: { duration: 0.85, repeat: Infinity, ease: "easeInOut" as const },
        });
        break;

      case "dance":
        body.start({
          rotate: [-8, 8, -8],
          y: [0, -10, 0, -10, 0],
          transition: { duration: 0.7, repeat: Infinity, ease: "easeInOut" as const },
        });
        tilt.start({
          rotate: [10, -10, 10],
          transition: { duration: 0.7, repeat: Infinity, ease: "easeInOut" as const },
        });
        break;

      case "laugh":
        // Throws head/hood back: tilt back + slight lift, eyes flare
        tilt.start({
          rotate: [0, -16, -10, -16, 0],
          y: [0, -8, -6, -8, 0],
          transition: { duration: 1.6, ease: "easeInOut" as const },
        });
        body.start({
          rotate: [0, 4, -2, 4, 0],
          transition: { duration: 1.6, ease: "easeInOut" as const },
        });
        eyeGlow.start({
          opacity: [1, 1.5, 1.2, 1.5, 1],
          transition: { duration: 1.6, ease: "easeInOut" as const },
        });
        break;

      case "curious":
        tilt.start({
          rotate: 14,
          x: 6,
          transition: { duration: 0.5, ease: "easeOut" as const },
        });
        eyeShape.start({
          scaleY: 0.4,
          transition: { duration: 0.4, ease: "easeOut" as const },
        });
        eyeGlow.start({
          opacity: [0.95, 1.2, 0.95],
          transition: { duration: 1.4, repeat: Infinity, ease: "easeInOut" as const },
        });
        body.start({ rotate: -2, transition: { duration: 0.4 } });
        break;

      case "float":
        lift.start({
          y: [-14, -26, -14],
          transition: { duration: 2.6, repeat: Infinity, ease: "easeInOut" as const },
        });
        eyeGlow.start({
          opacity: [1, 1.25, 1],
          transition: { duration: 2.6, repeat: Infinity, ease: "easeInOut" as const },
        });
        break;

      case "sleep":
        tilt.start({ rotate: 8, y: 14, transition: { duration: 0.6, ease: "easeOut" as const } });
        body.start({
          y: 30,
          scaleY: 0.78,
          rotate: 0,
          transition: { duration: 0.6, ease: "easeOut" as const },
        });
        eyeShape.start({ scaleY: 0.16, transition: { duration: 0.6 } });
        eyeGlow.start({
          opacity: [0.18, 0.45, 0.18],
          transition: { duration: 4.5, repeat: Infinity, ease: "easeInOut" as const },
        });
        break;

      case "sit":
        body.start({
          y: 26,
          scaleY: 0.86,
          transition: { duration: 0.5, ease: "easeOut" as const },
        });
        break;

      case "talk":
        tilt.start({
          rotate: [0, 2.2, -2.2, 0],
          transition: { duration: 1.4, repeat: Infinity, ease: "easeInOut" as const },
        });
        // eye glow brightness driven by talkBoost below
        break;

      case "idle":
      default:
        tilt.start({ rotate: 0, x: 0, y: 0, transition: { duration: 0.5 } });
        body.start({ y: 0, scaleY: 1, rotate: 0, transition: { duration: 0.5 } });
        body.start(breath);
        lift.start({ y: 0, transition: { duration: 0.6 } });
        eyeShape.start({ scaleY: 1, transition: { duration: 0.4 } });
        eyeGlow.start(glowIdle);
        break;
    }
  }, [state, body, lift, tilt, eyeGlow, eyeShape, breath, glowIdle]);

  // Mood-driven eye color tint
  const eyeTint =
    mood === "excited"
      ? CREAM
      : mood === "smug"
        ? COPPER_BRIGHT
        : mood === "sleepy"
          ? "#9c8f73"
          : COPPER_BRIGHT;

  const talkBoost = state === "talk" ? 0.6 + mouthOpen * 0.6 : 1;
  const baseEyeScaleY =
    mood === "smug" ? 0.55 : mood === "sleepy" ? 0.3 : state === "curious" ? 0.4 : 1;

  return (
    <div
      style={{
        position: "relative",
        width: W,
        height: H,
        transform: `scaleX(${facing})`,
        filter: "drop-shadow(0 22px 28px rgba(0,0,0,0.65))",
      }}
    >
      {/* Float halo */}
      {state === "float" && (
        <motion.div
          animate={{ opacity: [0.35, 0.75, 0.35], scale: [0.8, 1.15, 0.8] }}
          transition={{ duration: 2.6, repeat: Infinity, ease: "easeInOut" as const }}
          style={{
            position: "absolute",
            left: "50%",
            bottom: -8,
            width: 180,
            height: 38,
            transform: "translateX(-50%)",
            borderRadius: "50%",
            background:
              "radial-gradient(ellipse at center, rgba(244,234,213,0.45) 0%, rgba(244,234,213,0.08) 55%, rgba(244,234,213,0) 100%)",
            pointerEvents: "none",
          }}
        />
      )}

      {/* Ground shadow */}
      <motion.div
        animate={{
          opacity: state === "float" ? 0.18 : 0.55,
          scaleY: state === "float" ? 0.6 : 1,
        }}
        transition={{ duration: 0.8 }}
        style={{
          position: "absolute",
          left: "50%",
          bottom: -2,
          width: 150,
          height: 16,
          transform: "translateX(-50%)",
          borderRadius: "50%",
          background:
            "radial-gradient(ellipse at center, rgba(0,0,0,0.85) 0%, rgba(0,0,0,0) 70%)",
          pointerEvents: "none",
        }}
      />

      {/* Smoke wisps */}
      <motion.div
        animate={{ opacity: [0.4, 0.7, 0.4], y: [0, -12, 0] }}
        transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" as const }}
        style={{
          position: "absolute",
          inset: 0,
          pointerEvents: "none",
          background:
            "radial-gradient(ellipse 60% 40% at 18% 88%, rgba(180,180,200,0.18), transparent 60%)," +
            "radial-gradient(ellipse 60% 45% at 82% 90%, rgba(180,180,200,0.16), transparent 60%)," +
            "radial-gradient(ellipse 50% 30% at 50% 96%, rgba(180,180,200,0.14), transparent 65%)",
          filter: "blur(6px)",
        }}
      />

      {/* LIFT layer (float vertical drift) */}
      <motion.div
        animate={lift}
        style={{ position: "absolute", inset: 0 }}
      >
        {/* BODY (sway / sit-compress / dance rotate) */}
        <motion.div
          animate={body}
          style={{
            position: "absolute",
            inset: 0,
            transformOrigin: "50% 95%",
          }}
        >
          {/* TILT (head-back laugh, head-tilt curious, talk sway) */}
          <motion.div
            animate={tilt}
            style={{
              position: "absolute",
              inset: 0,
              transformOrigin: "50% 30%",
            }}
          >
            <img
              src={veilPng}
              alt="VEIL"
              draggable={false}
              style={{
                width: "100%",
                height: "100%",
                objectFit: "contain",
                userSelect: "none",
                pointerEvents: "none",
              }}
            />

            {/* EYE GLOW LAYER — positioned over the photo's eye area */}
            <motion.div
              animate={eyeGlow}
              style={{
                position: "absolute",
                inset: 0,
                pointerEvents: "none",
                opacity: talkBoost,
              }}
            >
              {/* Outer wide halo */}
              <div
                style={{
                  position: "absolute",
                  left: `calc(50% - ${EYE_DX + 26}px)`,
                  top: EYE_Y - 18,
                  width: 52,
                  height: 36,
                  borderRadius: "50%",
                  background: `radial-gradient(ellipse at center, ${eyeTint}cc 0%, ${eyeTint}55 35%, transparent 70%)`,
                  filter: "blur(6px)",
                  mixBlendMode: "screen",
                }}
              />
              <div
                style={{
                  position: "absolute",
                  left: `calc(50% + ${EYE_DX - 26}px)`,
                  top: EYE_Y - 18,
                  width: 52,
                  height: 36,
                  borderRadius: "50%",
                  background: `radial-gradient(ellipse at center, ${eyeTint}cc 0%, ${eyeTint}55 35%, transparent 70%)`,
                  filter: "blur(6px)",
                  mixBlendMode: "screen",
                }}
              />

              {/* Mid copper glow */}
              <div
                style={{
                  position: "absolute",
                  left: `calc(50% - ${EYE_DX + 11}px)`,
                  top: EYE_Y - 6,
                  width: 22,
                  height: 12,
                  borderRadius: "50%",
                  background: `radial-gradient(ellipse at center, ${COPPER_BRIGHT} 0%, ${COPPER_BRIGHT}aa 40%, transparent 75%)`,
                  filter: "blur(2.5px)",
                  mixBlendMode: "screen",
                }}
              />
              <div
                style={{
                  position: "absolute",
                  left: `calc(50% + ${EYE_DX - 11}px)`,
                  top: EYE_Y - 6,
                  width: 22,
                  height: 12,
                  borderRadius: "50%",
                  background: `radial-gradient(ellipse at center, ${COPPER_BRIGHT} 0%, ${COPPER_BRIGHT}aa 40%, transparent 75%)`,
                  filter: "blur(2.5px)",
                  mixBlendMode: "screen",
                }}
              />

              {/* Sharp inner eye shape (narrows for curious / sleepy / smug) */}
              <motion.div animate={eyeShape} style={{ position: "absolute", inset: 0 }}>
                <div
                  style={{
                    position: "absolute",
                    left: `calc(50% - ${EYE_DX + 5}px)`,
                    top: EYE_Y - 2,
                    width: 10,
                    height: 5,
                    borderRadius: "50%",
                    background: CREAM,
                    transform: `scaleY(${baseEyeScaleY})`,
                    transformOrigin: "center",
                    boxShadow: `0 0 6px ${CREAM}, 0 0 12px ${COPPER_BRIGHT}`,
                  }}
                />
                <div
                  style={{
                    position: "absolute",
                    left: `calc(50% + ${EYE_DX - 5}px)`,
                    top: EYE_Y - 2,
                    width: 10,
                    height: 5,
                    borderRadius: "50%",
                    background: CREAM,
                    transform: `scaleY(${baseEyeScaleY})`,
                    transformOrigin: "center",
                    boxShadow: `0 0 6px ${CREAM}, 0 0 12px ${COPPER_BRIGHT}`,
                  }}
                />
              </motion.div>

              {/* Hot core */}
              <div
                style={{
                  position: "absolute",
                  left: `calc(50% - ${EYE_DX + 1}px)`,
                  top: EYE_Y,
                  width: 3,
                  height: 1.6,
                  borderRadius: "50%",
                  background: "#fffaea",
                }}
              />
              <div
                style={{
                  position: "absolute",
                  left: `calc(50% + ${EYE_DX - 1}px)`,
                  top: EYE_Y,
                  width: 3,
                  height: 1.6,
                  borderRadius: "50%",
                  background: "#fffaea",
                }}
              />
            </motion.div>

            {/* Sleep Z */}
            {state === "sleep" && (
              <motion.div
                initial={{ y: 0, opacity: 0 }}
                animate={{ y: -36, opacity: [0, 0.7, 0] }}
                transition={{ duration: 3.5, repeat: Infinity, ease: "easeOut" as const }}
                style={{
                  position: "absolute",
                  left: "62%",
                  top: 30,
                  fontFamily: "serif",
                  fontStyle: "italic",
                  color: CREAM,
                  fontSize: 22,
                  pointerEvents: "none",
                }}
              >
                z
              </motion.div>
            )}
          </motion.div>
        </motion.div>
      </motion.div>
    </div>
  );
}
