import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import { Character } from "@/components/buddy/Character";
import { useBuddy } from "@/components/buddy/useBuddy";
import type { Mood } from "@/components/buddy/types";

const MOODS: { id: Mood; label: string }[] = [
  { id: "happy", label: "Happy" },
  { id: "neutral", label: "Neutral" },
  { id: "excited", label: "Excited" },
  { id: "smug", label: "Smug" },
  { id: "sleepy", label: "Sleepy" },
];

export default function BuddyPage() {
  const buddy = useBuddy();
  const [pos, setPos] = useState({ x: 0, y: 0 });
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [text, setText] = useState("welcome to NYXUS. i am your buddy.");
  const [useTTS, setUseTTS] = useState(false);
  const walkRef = useRef<number | null>(null);

  // Walk: when state is walk-left/right, slide buddy across the canvas
  useEffect(() => {
    if (buddy.state !== "walk-left" && buddy.state !== "walk-right") {
      if (walkRef.current) cancelAnimationFrame(walkRef.current);
      walkRef.current = null;
      return;
    }
    const dir = buddy.state === "walk-right" ? 1 : -1;
    const speed = 1.2;
    const step = () => {
      setPos((p) => {
        const cw = containerRef.current?.clientWidth ?? 800;
        const half = 110;
        let nx = p.x + dir * speed;
        if (nx > cw / 2 - half) nx = cw / 2 - half;
        if (nx < -cw / 2 + half) nx = -cw / 2 + half;
        return { ...p, x: nx };
      });
      walkRef.current = requestAnimationFrame(step);
    };
    walkRef.current = requestAnimationFrame(step);
    return () => {
      if (walkRef.current) cancelAnimationFrame(walkRef.current);
    };
  }, [buddy.state]);

  return (
    <div className="min-h-screen w-full bg-gradient-to-br from-[#06060a] via-[#0a0a0e] to-[#10101a] text-[#f4ead5] selection:bg-[#b8865a]/30">
      <div className="mx-auto max-w-7xl px-6 py-8">
        {/* Header */}
        <div className="mb-6 flex items-baseline justify-between">
          <div>
            <h1 className="font-serif text-4xl font-light tracking-wide">
              NYXUS <span className="text-[#b8865a]">VEIL</span>
            </h1>
            <p className="mt-1 text-sm text-[#bdb39e]">
              the night has eyes. shadow given form.
            </p>
          </div>
          <div className="rounded-full border border-[#b8865a]/40 bg-[#0a0a0e]/60 px-3 py-1.5 text-xs uppercase tracking-[0.2em] text-[#b8865a] backdrop-blur">
            rev r17b · prototype
          </div>
        </div>

        {/* Stage */}
        <div
          ref={containerRef}
          className="relative h-[520px] w-full overflow-hidden rounded-2xl border border-[#b8865a]/25 bg-[#0a0a0e]/60 shadow-[0_30px_80px_rgba(0,0,0,0.55)] backdrop-blur"
        >
          {/* Eclipse backdrop */}
          <div className="pointer-events-none absolute inset-0">
            <div
              className="absolute left-1/2 top-1/2 h-[420px] w-[420px] -translate-x-1/2 -translate-y-1/2 rounded-full"
              style={{
                background:
                  "radial-gradient(circle at center, rgba(244,234,213,0.10) 0%, rgba(244,234,213,0.04) 35%, transparent 70%)",
              }}
            />
            {/* horizon line */}
            <div className="absolute bottom-[88px] left-0 right-0 h-px bg-gradient-to-r from-transparent via-[#b8865a]/30 to-transparent" />
          </div>

          {/* Buddy — draggable, walkable */}
          <motion.div
            drag
            dragConstraints={containerRef}
            dragElastic={0.15}
            dragMomentum={false}
            className="absolute left-1/2 top-1/2 cursor-grab active:cursor-grabbing"
            style={{ x: pos.x, y: pos.y, translateX: "-50%", translateY: "-50%" }}
            onDrag={(_, info) => setPos({ x: pos.x + info.delta.x, y: pos.y + info.delta.y })}
          >
            <Character
              state={buddy.state}
              mood={buddy.mood}
              mouthOpen={buddy.mouthOpen}
              facing={buddy.facing}
            />

            {/* Speech bubble */}
            <AnimatePresence>
              {buddy.bubble && (
                <motion.div
                  initial={{ opacity: 0, y: 6, scale: 0.9 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -6, scale: 0.95 }}
                  className="absolute -top-10 left-1/2 max-w-[260px] -translate-x-1/2 rounded-2xl border border-[#b8865a]/50 bg-[#0a0a0e]/85 px-4 py-2 text-center text-sm text-[#f4ead5] shadow-[0_10px_30px_rgba(0,0,0,0.6)] backdrop-blur"
                >
                  {buddy.bubble}
                  <div className="absolute -bottom-1.5 left-1/2 h-3 w-3 -translate-x-1/2 rotate-45 border-b border-r border-[#b8865a]/50 bg-[#0a0a0e]/85" />
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        </div>

        {/* Control panel */}
        <div className="mt-6 grid gap-4 lg:grid-cols-3">
          {/* Actions */}
          <div className="rounded-2xl border border-[#b8865a]/25 bg-[#0a0a0e]/60 p-5 backdrop-blur">
            <div className="mb-3 text-[11px] uppercase tracking-[0.22em] text-[#b8865a]">
              Actions
            </div>
            <div className="grid grid-cols-2 gap-2">
              {([
                ["idle", "Idle"],
                ["wave", "Wave"],
                ["walk-left", "Glide ←"],
                ["walk-right", "Glide →"],
                ["curious", "Curious"],
                ["laugh", "Laugh"],
                ["float", "Float"],
                ["dance", "Dance"],
                ["sit", "Sit"],
                ["sleep", "Sleep"],
              ] as const).map(([id, label]) => (
                <button
                  key={id}
                  onClick={() => buddy.trigger(id)}
                  className={`rounded-lg border px-3 py-2 text-sm transition ${
                    buddy.state === id
                      ? "border-[#b8865a] bg-[#b8865a]/15 text-[#f4ead5]"
                      : "border-[#b8865a]/25 bg-transparent text-[#bdb39e] hover:border-[#b8865a]/60 hover:text-[#f4ead5]"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Talk */}
          <div className="rounded-2xl border border-[#b8865a]/25 bg-[#0a0a0e]/60 p-5 backdrop-blur">
            <div className="mb-3 text-[11px] uppercase tracking-[0.22em] text-[#b8865a]">
              Talk
            </div>
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={3}
              className="w-full rounded-lg border border-[#b8865a]/25 bg-[#06060a] px-3 py-2 text-sm text-[#f4ead5] outline-none focus:border-[#b8865a]/70"
              placeholder="type something for VEIL to say…"
            />
            <label className="mt-2 flex items-center gap-2 text-xs text-[#bdb39e]">
              <input
                type="checkbox"
                checked={useTTS}
                onChange={(e) => setUseTTS(e.target.checked)}
                className="accent-[#b8865a]"
              />
              also speak out loud (browser TTS)
            </label>
            <button
              onClick={() => buddy.speak(text || "...", { useTTS })}
              className="mt-3 w-full rounded-lg border border-[#b8865a] bg-[#b8865a]/10 px-3 py-2 text-sm font-medium text-[#f4ead5] transition hover:bg-[#b8865a]/25"
            >
              Make VEIL speak
            </button>
          </div>

          {/* Mood + autonomy */}
          <div className="rounded-2xl border border-[#b8865a]/25 bg-[#0a0a0e]/60 p-5 backdrop-blur">
            <div className="mb-3 text-[11px] uppercase tracking-[0.22em] text-[#b8865a]">
              Mood
            </div>
            <div className="flex flex-wrap gap-2">
              {MOODS.map((m) => (
                <button
                  key={m.id}
                  onClick={() => buddy.setMood(m.id)}
                  className={`rounded-full border px-3 py-1 text-xs transition ${
                    buddy.mood === m.id
                      ? "border-[#b8865a] bg-[#b8865a]/15 text-[#f4ead5]"
                      : "border-[#b8865a]/25 text-[#bdb39e] hover:border-[#b8865a]/60 hover:text-[#f4ead5]"
                  }`}
                >
                  {m.label}
                </button>
              ))}
            </div>

            <div className="mt-5 flex items-center justify-between">
              <div>
                <div className="text-sm text-[#f4ead5]">Autonomy</div>
                <div className="text-xs text-[#bdb39e]">
                  VEIL acts on its own every 8–18s
                </div>
              </div>
              <button
                onClick={() => buddy.setAutonomy(!buddy.autonomy)}
                className={`relative h-7 w-12 rounded-full border transition ${
                  buddy.autonomy
                    ? "border-[#b8865a] bg-[#b8865a]/30"
                    : "border-[#b8865a]/30 bg-transparent"
                }`}
                aria-label="toggle autonomy"
              >
                <span
                  className={`absolute top-0.5 h-5 w-5 rounded-full bg-[#f4ead5] transition-all ${
                    buddy.autonomy ? "left-6" : "left-0.5"
                  }`}
                />
              </button>
            </div>

            <div className="mt-5 flex items-center justify-between">
              <div>
                <div className="text-sm text-[#f4ead5]">Facing</div>
                <div className="text-xs text-[#bdb39e]">flip VEIL</div>
              </div>
              <button
                onClick={() => buddy.setFacing((buddy.facing === 1 ? -1 : 1) as 1 | -1)}
                className="rounded-lg border border-[#b8865a]/40 px-3 py-1.5 text-xs text-[#f4ead5] hover:border-[#b8865a]"
              >
                {buddy.facing === 1 ? "→ facing right" : "← facing left"}
              </button>
            </div>
          </div>
        </div>

        <div className="mt-6 text-center text-[11px] uppercase tracking-[0.22em] text-[#bdb39e]/60">
          drag VEIL · click actions · the night has eyes
        </div>
      </div>
    </div>
  );
}
