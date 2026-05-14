import { Canvas, useFrame } from "@react-three/fiber";
import { Component, useMemo, useRef, useState, type ReactNode } from "react";
import * as THREE from "three";
import type { BuddyState, Mood } from "./types";

function detectWebGL(): boolean {
  if (typeof window === "undefined") return false;
  try {
    const c = document.createElement("canvas");
    return !!(
      window.WebGLRenderingContext &&
      (c.getContext("webgl2") || c.getContext("webgl") || c.getContext("experimental-webgl"))
    );
  } catch {
    return false;
  }
}

interface CharacterProps {
  state: BuddyState;
  mood: Mood;
  mouthOpen: number;
  facing: 1 | -1;
}

const INK = "#0a0a0e";
const INK_DEEP = "#06060a";
const COPPER_BRIGHT = "#d9a877";
const CREAM = "#f4ead5";

// ---------- Procedural geometries ----------

function useCloakGeometry() {
  return useMemo(() => {
    // Tapered teardrop profile rotated around Y axis
    const pts: THREE.Vector2[] = [
      new THREE.Vector2(0.04, 0.0),
      new THREE.Vector2(0.6, 0.05),
      new THREE.Vector2(0.62, 0.18),
      new THREE.Vector2(0.55, 0.45),
      new THREE.Vector2(0.48, 0.85),
      new THREE.Vector2(0.42, 1.25),
      new THREE.Vector2(0.36, 1.6),
      new THREE.Vector2(0.32, 1.85),
      new THREE.Vector2(0.22, 2.0),
      new THREE.Vector2(0.05, 2.05),
    ];
    return new THREE.LatheGeometry(pts, 64);
  }, []);
}

function useHoodGeometry() {
  return useMemo(() => {
    // Half-dome with opening at front (sphere with phiLength < 2π)
    const g = new THREE.SphereGeometry(
      0.42,
      48,
      32,
      Math.PI * 0.55, // phiStart — rotates the opening toward front
      Math.PI * 1.9, // phiLength — leaves a gap for the face void
      0,
      Math.PI * 0.62, // top portion only
    );
    return g;
  }, []);
}

function useHoodCollarGeometry() {
  // Drape collar that hides the seam between hood and shoulders
  return useMemo(() => {
    const pts: THREE.Vector2[] = [
      new THREE.Vector2(0.32, 0),
      new THREE.Vector2(0.46, 0.04),
      new THREE.Vector2(0.5, 0.18),
      new THREE.Vector2(0.42, 0.32),
      new THREE.Vector2(0.34, 0.36),
    ];
    return new THREE.LatheGeometry(pts, 48);
  }, []);
}

// ---------- Smoke particles ----------

interface SmokeProps {
  count?: number;
}

function Smoke({ count = 220 }: SmokeProps) {
  const ref = useRef<THREE.Points>(null);
  const positions = useMemo(() => {
    const arr = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      const a = Math.random() * Math.PI * 2;
      const r = 0.3 + Math.random() * 0.9;
      arr[i * 3 + 0] = Math.cos(a) * r;
      arr[i * 3 + 1] = Math.random() * 1.6;
      arr[i * 3 + 2] = Math.sin(a) * r * 0.6;
    }
    return arr;
  }, [count]);

  const speeds = useMemo(() => {
    const arr = new Float32Array(count);
    for (let i = 0; i < count; i++) arr[i] = 0.04 + Math.random() * 0.12;
    return arr;
  }, [count]);

  useFrame((_, dt) => {
    if (!ref.current) return;
    const attr = ref.current.geometry.attributes.position as THREE.BufferAttribute;
    const a = attr.array as Float32Array;
    for (let i = 0; i < count; i++) {
      a[i * 3 + 1] += speeds[i] * dt;
      // gentle drift
      a[i * 3 + 0] += Math.sin(performance.now() * 0.0005 + i) * 0.0008;
      if (a[i * 3 + 1] > 2.4) {
        a[i * 3 + 1] = 0;
        const ang = Math.random() * Math.PI * 2;
        const r = 0.3 + Math.random() * 0.9;
        a[i * 3 + 0] = Math.cos(ang) * r;
        a[i * 3 + 2] = Math.sin(ang) * r * 0.6;
      }
    }
    attr.needsUpdate = true;
  });

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          args={[positions, 3]}
          count={count}
        />
      </bufferGeometry>
      <pointsMaterial
        color="#2a2520"
        size={0.045}
        transparent
        opacity={0.35}
        sizeAttenuation
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}

// ---------- VEIL rig ----------

interface VeilRigProps extends CharacterProps {}

function VeilRig({ state, mood, mouthOpen, facing }: VeilRigProps) {
  const root = useRef<THREE.Group>(null);
  const lift = useRef<THREE.Group>(null);
  const body = useRef<THREE.Group>(null);
  const hood = useRef<THREE.Group>(null);
  const eyeL = useRef<THREE.Mesh>(null);
  const eyeR = useRef<THREE.Mesh>(null);
  const lightL = useRef<THREE.PointLight>(null);
  const lightR = useRef<THREE.PointLight>(null);
  const cloakHem = useRef<THREE.Mesh>(null);

  const cloakGeom = useCloakGeometry();
  const hoodGeom = useHoodGeometry();
  const collarGeom = useHoodCollarGeometry();

  // Targets that smoothly damp toward state-driven values
  const target = useRef({
    bodyY: 0,
    bodyScaleY: 1,
    bodyRotZ: 0,
    hoodRotX: 0,
    hoodRotZ: 0,
    hoodPosY: 0,
    liftY: 0,
    eyeIntensity: 1,
    eyeScaleY: 1,
  });

  const setTargets = () => {
    const t = target.current;
    // defaults
    t.bodyY = 0;
    t.bodyScaleY = 1;
    t.bodyRotZ = 0;
    t.hoodRotX = -0.08;
    t.hoodRotZ = 0;
    t.hoodPosY = 0;
    t.liftY = 0;
    t.eyeIntensity = 1.6;
    t.eyeScaleY = 1;

    if (mood === "smug") t.eyeScaleY = 0.45;
    if (mood === "sleepy") t.eyeScaleY = 0.3;
    if (mood === "excited") t.eyeIntensity = 2.4;

    switch (state) {
      case "laugh":
        t.hoodRotX = -0.55; // throw head back
        t.hoodPosY = 0.05;
        t.eyeIntensity = 3.2;
        break;
      case "curious":
        t.hoodRotZ = 0.32; // tilt
        t.eyeScaleY = 0.4;
        t.eyeIntensity = 2.0;
        break;
      case "float":
        t.liftY = 0.35;
        t.eyeIntensity = 2.4;
        break;
      case "sleep":
        t.bodyScaleY = 0.78;
        t.bodyY = -0.18;
        t.hoodRotZ = 0.18;
        t.hoodPosY = -0.1;
        t.eyeScaleY = 0.15;
        t.eyeIntensity = 0.45;
        break;
      case "sit":
        t.bodyScaleY = 0.86;
        t.bodyY = -0.12;
        break;
      case "talk":
        t.eyeIntensity = 1.4 + mouthOpen * 1.6;
        break;
      case "dance":
        t.eyeIntensity = 2.2;
        break;
      case "wave":
        t.eyeIntensity = 2.4;
        break;
    }
  };

  useFrame((_, dt) => {
    setTargets();
    const time = performance.now() * 0.001;
    const t = target.current;

    if (root.current) {
      root.current.rotation.y = facing === -1 ? Math.PI : 0;
    }

    // Damp helper
    const damp = (cur: number, tgt: number, lambda = 4) =>
      cur + (tgt - cur) * (1 - Math.exp(-lambda * dt));

    if (lift.current) {
      // Float bob = lerp + sine
      const bob =
        state === "float" ? Math.sin(time * 1.6) * 0.07 : 0;
      lift.current.position.y = damp(lift.current.position.y, t.liftY + bob);
    }

    if (body.current) {
      // Idle sway
      const sway = state === "idle" ? Math.sin(time * 0.9) * 0.02 : 0;
      const danceRot =
        state === "dance" ? Math.sin(time * 6) * 0.15 : 0;
      const walkBob =
        state === "walk-left" || state === "walk-right"
          ? Math.abs(Math.sin(time * 6)) * 0.04
          : 0;
      body.current.rotation.z = damp(body.current.rotation.z, t.bodyRotZ + sway + danceRot);
      body.current.position.y = damp(body.current.position.y, t.bodyY + walkBob);
      body.current.scale.y = damp(body.current.scale.y, t.bodyScaleY);
    }

    if (hood.current) {
      const talkSway =
        state === "talk" ? Math.sin(time * 4) * 0.04 : 0;
      const danceTwist =
        state === "dance" ? Math.sin(time * 6) * 0.2 : 0;
      hood.current.rotation.x = damp(hood.current.rotation.x, t.hoodRotX + talkSway);
      hood.current.rotation.z = damp(hood.current.rotation.z, t.hoodRotZ + danceTwist);
      hood.current.position.y = damp(hood.current.position.y, t.hoodPosY);
    }

    // Eye glow + shape
    const intensityPulse =
      state === "sleep"
        ? 0.5 + Math.sin(time * 1.3) * 0.3
        : state === "idle"
          ? 0.95 + Math.sin(time * 1.7) * 0.1
          : 1;

    if (eyeL.current && eyeR.current) {
      const mat = eyeL.current.material as THREE.MeshStandardMaterial;
      const matR = eyeR.current.material as THREE.MeshStandardMaterial;
      const targetIntensity = t.eyeIntensity * intensityPulse;
      mat.emissiveIntensity = damp(mat.emissiveIntensity, targetIntensity, 8);
      matR.emissiveIntensity = mat.emissiveIntensity;

      const sy = damp(eyeL.current.scale.y, t.eyeScaleY, 8);
      eyeL.current.scale.y = sy;
      eyeR.current.scale.y = sy;
    }

    if (lightL.current && lightR.current) {
      const li = (eyeL.current?.material as THREE.MeshStandardMaterial | undefined)
        ?.emissiveIntensity ?? 1;
      lightL.current.intensity = li * 0.9;
      lightR.current.intensity = li * 0.9;
    }

    // Cloak hem subtle ripple via vertex jitter on rotation
    if (cloakHem.current) {
      cloakHem.current.rotation.y = Math.sin(time * 0.6) * 0.04;
    }
  });

  // Eye color tint based on mood
  const eyeColor =
    mood === "sleepy" ? "#9c8f73" : mood === "smug" ? COPPER_BRIGHT : COPPER_BRIGHT;

  return (
    <group ref={root}>
      <group ref={lift}>
        {/* CLOAK BODY */}
        <group ref={body}>
          <mesh ref={cloakHem} geometry={cloakGeom}>
            <meshStandardMaterial
              color={INK}
              roughness={0.95}
              metalness={0.05}
            />
          </mesh>

          {/* Inner copper rim line at hem */}
          <mesh position={[0, 0.02, 0]} rotation={[Math.PI / 2, 0, 0]}>
            <ringGeometry args={[0.59, 0.62, 64]} />
            <meshBasicMaterial color={COPPER_BRIGHT} side={THREE.DoubleSide} transparent opacity={0.35} />
          </mesh>

          {/* Collar drape */}
          <group position={[0, 1.7, 0]}>
            <mesh geometry={collarGeom}>
              <meshStandardMaterial color={INK_DEEP} roughness={0.95} />
            </mesh>
          </group>

          {/* HOOD */}
          <group ref={hood} position={[0, 2.05, 0]}>
            {/* Outer hood shell */}
            <mesh
              geometry={hoodGeom}
              rotation={[0, Math.PI * 0.5, 0]}
            >
              <meshStandardMaterial
                color={INK}
                roughness={0.95}
                metalness={0.05}
                side={THREE.DoubleSide}
              />
            </mesh>

            {/* Hood inner void — pure black ellipsoid filling the head cavity */}
            <mesh position={[0, 0.05, 0.02]}>
              <sphereGeometry args={[0.32, 32, 24]} />
              <meshBasicMaterial color="#000000" />
            </mesh>

            {/* Eye-socket recess (black disk facing forward) */}
            <mesh position={[0, 0.02, 0.36]}>
              <circleGeometry args={[0.22, 32]} />
              <meshBasicMaterial color="#000000" />
            </mesh>

            {/* EYES — emissive ovoid spheres */}
            <mesh
              ref={eyeL}
              position={[-0.11, 0.02, 0.38]}
              scale={[1, 1, 0.35]}
            >
              <sphereGeometry args={[0.04, 24, 16]} />
              <meshStandardMaterial
                color={CREAM}
                emissive={eyeColor}
                emissiveIntensity={1.6}
                toneMapped={false}
              />
            </mesh>
            <mesh
              ref={eyeR}
              position={[0.11, 0.02, 0.38]}
              scale={[1, 1, 0.35]}
            >
              <sphereGeometry args={[0.04, 24, 16]} />
              <meshStandardMaterial
                color={CREAM}
                emissive={eyeColor}
                emissiveIntensity={1.6}
                toneMapped={false}
              />
            </mesh>

            {/* Point lights at the eyes — illuminate the hood interior */}
            <pointLight
              ref={lightL}
              position={[-0.11, 0.02, 0.38]}
              color={COPPER_BRIGHT}
              intensity={1.2}
              distance={1.6}
              decay={2}
            />
            <pointLight
              ref={lightR}
              position={[0.11, 0.02, 0.38]}
              color={COPPER_BRIGHT}
              intensity={1.2}
              distance={1.6}
              decay={2}
            />

            {/* Hood front lip — copper rim (thin torus arc) */}
            <mesh position={[0, -0.05, 0.3]} rotation={[Math.PI * 0.5, 0, 0]}>
              <torusGeometry args={[0.32, 0.012, 12, 48, Math.PI]} />
              <meshStandardMaterial
                color={COPPER_BRIGHT}
                emissive={COPPER_BRIGHT}
                emissiveIntensity={0.4}
                roughness={0.4}
                metalness={0.7}
              />
            </mesh>
          </group>
        </group>
      </group>

      {/* SMOKE — drifting particles around the figure */}
      <Smoke count={180} />

      {/* Float halo (only when floating) */}
      {state === "float" && (
        <mesh position={[0, 0.01, 0]} rotation={[-Math.PI / 2, 0, 0]}>
          <ringGeometry args={[0.4, 0.95, 48]} />
          <meshBasicMaterial
            color={CREAM}
            transparent
            opacity={0.18}
            side={THREE.DoubleSide}
            blending={THREE.AdditiveBlending}
          />
        </mesh>
      )}

      {/* Ground shadow disc */}
      <mesh position={[0, -0.01, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <circleGeometry args={[0.7, 48]} />
        <meshBasicMaterial color="#000000" transparent opacity={state === "float" ? 0.25 : 0.55} />
      </mesh>
    </group>
  );
}

// ---------- Error boundary for WebGL-less environments ----------

class WebGLBoundary extends Component<
  { children: ReactNode; fallback: ReactNode },
  { hasError: boolean }
> {
  state = { hasError: false };
  static getDerivedStateFromError() {
    return { hasError: true };
  }
  componentDidCatch() {
    /* swallow */
  }
  render() {
    if (this.state.hasError) return this.props.fallback;
    return this.props.children;
  }
}

function VeilFallback() {
  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flexDirection: "column",
        gap: 12,
        color: CREAM,
        fontFamily: "serif",
        textAlign: "center",
        padding: 16,
      }}
    >
      <div
        style={{
          width: 18,
          height: 8,
          borderRadius: 4,
          background: COPPER_BRIGHT,
          boxShadow: `0 0 18px ${COPPER_BRIGHT}, 0 0 36px ${COPPER_BRIGHT}88`,
        }}
      />
      <div style={{ fontSize: 13, opacity: 0.8, fontStyle: "italic" }}>
        the night needs a window. enable hardware acceleration to see VEIL.
      </div>
    </div>
  );
}

// ---------- Outer Canvas wrapper ----------

export function Character({ state, mood, mouthOpen, facing }: CharacterProps) {
  const [webglOk] = useState(() => detectWebGL());

  return (
    <div
      style={{
        width: 320,
        height: 460,
        filter: "drop-shadow(0 22px 28px rgba(0,0,0,0.65))",
      }}
    >
      {!webglOk ? (
        <VeilFallback />
      ) : (
      <WebGLBoundary fallback={<VeilFallback />}>
        <Canvas
          dpr={[1, 2]}
          camera={{ position: [0, 1.3, 4.2], fov: 32 }}
          gl={{
            antialias: true,
            alpha: true,
            powerPreference: "high-performance",
            failIfMajorPerformanceCaveat: false,
          }}
          onCreated={({ gl }) => {
            gl.setClearColor(0x000000, 0);
          }}
          style={{ background: "transparent" }}
        >
          {/* Warm dark ambient — barely there */}
          <ambientLight intensity={0.18} color="#1a1612" />
          {/* Cream key light from upper-left */}
          <directionalLight position={[-3, 4, 2]} intensity={0.45} color={CREAM} />
          {/* Copper rim from behind */}
          <directionalLight position={[2, 3, -3]} intensity={0.3} color={COPPER_BRIGHT} />
          {/* Subtle copper fill */}
          <pointLight position={[2, 1, 2]} intensity={0.15} color="#8a7a5a" />

          <VeilRig state={state} mood={mood} mouthOpen={mouthOpen} facing={facing} />
        </Canvas>
      </WebGLBoundary>
      )}
    </div>
  );
}
