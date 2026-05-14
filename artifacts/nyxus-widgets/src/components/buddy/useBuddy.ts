import { useCallback, useEffect, useRef, useState } from "react";
import type { BuddyState, Mood } from "./types";

const VEIL_QUIPS = [
  "the night has eyes.",
  "i am VEIL. i watch the system.",
  "your kernel breathes evenly.",
  "no process moves without my notice.",
  "the eclipse holds. the user is safe.",
  "shadow is not absence. shadow is presence.",
  "ink, copper, cream. nothing else.",
  "ask, and i will speak.",
  "i was here before you logged in.",
  "every binary checked. every toggle wired.",
  "windowrule v1, always.",
  "matugen banished. the palette stands.",
];

export function useBuddy() {
  const [state, setState] = useState<BuddyState>("idle");
  const [mood, setMood] = useState<Mood>("neutral");
  const [mouthOpen, setMouthOpen] = useState(0);
  const [facing, setFacing] = useState<1 | -1>(1);
  const [bubble, setBubble] = useState<string | null>(null);
  const [autonomy, setAutonomy] = useState(true);

  const speakTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const speakEndTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const autonomyTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const stopMouth = useCallback(() => {
    if (speakTimer.current) clearInterval(speakTimer.current);
    if (speakEndTimer.current) clearTimeout(speakEndTimer.current);
    speakTimer.current = null;
    speakEndTimer.current = null;
    setMouthOpen(0);
  }, []);

  const speak = useCallback(
    (text: string, opts?: { useTTS?: boolean }) => {
      stopMouth();
      setBubble(text);
      setState("talk");
      const useTTS = opts?.useTTS ?? false;

      const durationMs = Math.max(1500, text.length * 70);

      // VEIL has no mouth — the value drives eye-glow intensity instead.
      let i = 0;
      speakTimer.current = setInterval(() => {
        const ch = text[i % text.length] ?? "a";
        const isVowel = /[aeiouAEIOU]/.test(ch);
        const isSpace = /\s/.test(ch);
        setMouthOpen(isSpace ? 0.15 : isVowel ? 0.85 + Math.random() * 0.15 : 0.4 + Math.random() * 0.3);
        i += 1;
      }, 95);

      if (useTTS && typeof window !== "undefined" && "speechSynthesis" in window) {
        try {
          window.speechSynthesis.cancel();
          const u = new SpeechSynthesisUtterance(text);
          u.rate = 0.92;
          u.pitch = 0.55;
          window.speechSynthesis.speak(u);
        } catch {
          /* ignore */
        }
      }

      speakEndTimer.current = setTimeout(() => {
        stopMouth();
        setBubble(null);
        setState("idle");
      }, durationMs);
    },
    [stopMouth],
  );

  const trigger = useCallback(
    (next: BuddyState) => {
      stopMouth();
      setBubble(null);
      setState(next);
      if (next === "walk-left") setFacing(-1);
      if (next === "walk-right") setFacing(1);
      if (next === "laugh" || next === "float") setMood("excited");
      if (next === "sleep") setMood("sleepy");
      if (next === "curious") setMood("smug");
      if (next === "wave") setMood("neutral");
      // one-shot states return to idle
      if (next === "wave") setTimeout(() => setState("idle"), 1950);
      if (next === "laugh") setTimeout(() => setState("idle"), 1700);
    },
    [stopMouth],
  );

  // VEIL acts on its own — quiet, occasional, brand-flavored
  useEffect(() => {
    if (!autonomy) {
      if (autonomyTimer.current) clearTimeout(autonomyTimer.current);
      return;
    }
    const tick = () => {
      setState((s) => {
        if (s !== "idle") return s;
        const roll = Math.random();
        if (roll < 0.4) {
          const quip = VEIL_QUIPS[Math.floor(Math.random() * VEIL_QUIPS.length)];
          speak(quip);
        } else if (roll < 0.55) {
          trigger("curious");
          setTimeout(() => setState("idle"), 2400);
        } else if (roll < 0.7) {
          trigger("float");
          setTimeout(() => setState("idle"), 3600);
        } else if (roll < 0.82) {
          trigger("walk-right");
          setTimeout(() => setState("idle"), 2400);
        } else if (roll < 0.92) {
          trigger("walk-left");
          setTimeout(() => setState("idle"), 2400);
        } else {
          trigger("laugh");
        }
        return s;
      });
      const next = 8000 + Math.random() * 10000;
      autonomyTimer.current = setTimeout(tick, next);
    };
    autonomyTimer.current = setTimeout(tick, 5500);
    return () => {
      if (autonomyTimer.current) clearTimeout(autonomyTimer.current);
    };
  }, [autonomy, speak, trigger]);

  useEffect(
    () => () => {
      stopMouth();
      if (autonomyTimer.current) clearTimeout(autonomyTimer.current);
    },
    [stopMouth],
  );

  return {
    state,
    mood,
    mouthOpen,
    facing,
    bubble,
    autonomy,
    setMood,
    setAutonomy,
    setFacing,
    trigger,
    speak,
  };
}
