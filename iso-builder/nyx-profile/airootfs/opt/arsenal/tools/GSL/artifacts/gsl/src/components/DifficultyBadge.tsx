export function DifficultyBadge({ difficulty }: { difficulty: string }) {
  const diff = difficulty?.toLowerCase() || "beginner";

  const styles: Record<string, { color: string; bg: string; border: string; glow: string }> = {
    beginner:     { color: "#4ade80", bg: "rgba(74,222,128,0.07)",  border: "rgba(74,222,128,0.2)",  glow: "" },
    intermediate: { color: "#fbbf24", bg: "rgba(251,191,36,0.07)",  border: "rgba(251,191,36,0.2)",  glow: "" },
    advanced:     { color: "#fb923c", bg: "rgba(249,115,22,0.07)",  border: "rgba(249,115,22,0.2)",  glow: "" },
    expert:       { color: "#f87171", bg: "rgba(248,113,113,0.07)", border: "rgba(248,113,113,0.25)", glow: "0 0 8px rgba(248,113,113,0.3)" },
  };

  const s = styles[diff] ?? styles.beginner;

  return (
    <span
      className="inline-flex items-center font-mono uppercase tracking-wider rounded-sm px-1.5 py-0.5"
      style={{
        fontSize: "0.6rem",
        color: s.color,
        background: s.bg,
        border: `1px solid ${s.border}`,
        boxShadow: s.glow || undefined,
        letterSpacing: "0.1em",
        fontWeight: 600,
      }}
    >
      {difficulty}
    </span>
  );
}
