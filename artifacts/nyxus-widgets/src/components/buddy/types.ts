export type BuddyState =
  | "idle"
  | "wave"
  | "walk-left"
  | "walk-right"
  | "dance"
  | "sleep"
  | "talk"
  | "laugh"
  | "curious"
  | "float"
  | "sit";

export type Mood = "happy" | "neutral" | "sleepy" | "excited" | "smug";

export interface BuddyConfig {
  scale: number;
  autonomy: boolean;
  speechBubble: boolean;
}
