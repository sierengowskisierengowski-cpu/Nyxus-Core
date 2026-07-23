import { Star, Clock } from "lucide-react";
import { DifficultyBadge } from "./DifficultyBadge";

export interface ToolCardProps {
  tool: {
    id: string;
    name: string;
    description: string;
    category: string;
    difficulty: string;
    estimatedTime: string;
    command: string;
    isFavorite: boolean;
    tags: string[];
    params: Array<{ name: string; label: string; type: string; defaultValue: string; placeholder?: string; required?: boolean }>;
    learnContent?: string;
  };
  onClick: (tool: ToolCardProps["tool"]) => void;
  onToggleFavorite: (id: string, isFav: boolean) => void;
  isSelected?: boolean;
}

const CATEGORY_COLOR: Record<string, string> = {
  "Network Scanning":           "#3b82f6",
  "WiFi Security":              "#f59e0b",
  "Web Application Testing":    "#10b981",
  "Password & Hash Testing":    "#f97316",
  "Exploitation Framework":     "#ef4444",
  "Honeypot Testing":           "#ec4899",
  "Packet Analysis":            "#06b6d4",
  "Bluetooth & RF":             "#8b5cf6",
  "Stress Testing":             "#14b8a6",
  "Forensics & Analysis":       "#a855f7",
  "OSINT":                      "#6366f1",
  "Vulnerability Scanning":     "#f43f5e",
  "Cryptography":               "#84cc16",
  "Steganography":              "#d946ef",
  "Reverse Engineering":        "#fb923c",
  "Docker & Container Security":"#22d3ee",
  "Social Engineering":         "#ff2d55",
  "IoT & Hardware":             "#4ade80",
  "GowskiNet Specific":         "#9b7fef",
  "CTF & Practice":             "#34d399",
};

export function ToolCard({ tool, onClick, onToggleFavorite, isSelected }: ToolCardProps) {
  const catColor = CATEGORY_COLOR[tool.category] ?? "#7B6FD4";
  const paramCount = tool.params?.length ?? 0;

  return (
    <div
      className="group relative cursor-pointer rounded-sm transition-all duration-150 overflow-hidden"
      style={{
        background: isSelected ? "hsl(235 28% 7.5%)" : "hsl(235 28% 6%)",
        border: `1px solid ${isSelected ? `${catColor}50` : "hsl(232 18% 12%)"}`,
        boxShadow: isSelected
          ? `0 0 0 1px ${catColor}20, 0 0 16px ${catColor}08, 0 4px 20px rgba(0,0,0,0.4)`
          : "0 2px 8px rgba(0,0,0,0.2)",
      }}
      onClick={() => onClick(tool)}
      onMouseEnter={(e) => {
        if (!isSelected) {
          const el = e.currentTarget as HTMLDivElement;
          el.style.borderColor = `${catColor}35`;
          el.style.boxShadow = `0 0 12px ${catColor}08, 0 4px 20px rgba(0,0,0,0.4)`;
        }
      }}
      onMouseLeave={(e) => {
        if (!isSelected) {
          const el = e.currentTarget as HTMLDivElement;
          el.style.borderColor = "hsl(232 18% 12%)";
          el.style.boxShadow = "0 2px 8px rgba(0,0,0,0.2)";
        }
      }}
    >
      {/* Category accent bar */}
      <div
        className="cat-bar"
        style={{
          background: `linear-gradient(180deg, ${catColor}, ${catColor}60)`,
          boxShadow: isSelected ? `2px 0 8px ${catColor}40` : undefined,
        }}
      />

      <div className="pl-4 pr-3 pt-3 pb-3">
        {/* Top row */}
        <div className="flex items-start justify-between gap-2 mb-2">
          <div className="flex-1 min-w-0">
            <div
              className="font-semibold text-[13px] truncate transition-colors leading-tight"
              style={{ color: isSelected ? catColor : "hsl(220 20% 92%)" }}
            >
              {tool.name}
            </div>
            <div className="flex items-center gap-2 mt-1.5 flex-wrap">
              <DifficultyBadge difficulty={tool.difficulty} />
              <span className="flex items-center gap-1 text-[10px] font-mono" style={{ color: "hsl(232 10% 42%)" }}>
                <Clock className="h-2.5 w-2.5" />
                {tool.estimatedTime}
              </span>
              {paramCount > 0 && (
                <span
                  className="text-[9px] font-mono px-1.5 py-0.5 rounded-sm"
                  style={{
                    background: `${catColor}10`,
                    border: `1px solid ${catColor}20`,
                    color: `${catColor}cc`,
                  }}
                >
                  {paramCount}p
                </span>
              )}
            </div>
          </div>
          <button
            className="h-7 w-7 flex items-center justify-center rounded-sm flex-shrink-0 transition-all"
            style={{
              color: tool.isFavorite ? "#fbbf24" : "hsl(232 10% 35%)",
              background: tool.isFavorite ? "rgba(251,191,36,0.08)" : "transparent",
              border: tool.isFavorite ? "1px solid rgba(251,191,36,0.2)" : "1px solid transparent",
            }}
            onClick={(e) => {
              e.stopPropagation();
              onToggleFavorite(tool.id, !tool.isFavorite);
            }}
            onMouseEnter={(e) => {
              if (!tool.isFavorite) {
                (e.currentTarget as HTMLButtonElement).style.color = "#fbbf24";
                (e.currentTarget as HTMLButtonElement).style.borderColor = "rgba(251,191,36,0.2)";
              }
            }}
            onMouseLeave={(e) => {
              if (!tool.isFavorite) {
                (e.currentTarget as HTMLButtonElement).style.color = "hsl(232 10% 35%)";
                (e.currentTarget as HTMLButtonElement).style.borderColor = "transparent";
              }
            }}
          >
            <Star className={`h-3.5 w-3.5 ${tool.isFavorite ? "fill-current" : ""}`} />
          </button>
        </div>

        {/* Description */}
        <p
          className="text-[11px] line-clamp-2 leading-relaxed mb-2.5"
          style={{ color: "hsl(232 10% 45%)" }}
        >
          {tool.description}
        </p>

        {/* Command pill */}
        <div
          className="flex items-center gap-1.5 rounded-sm px-2.5 py-1.5 mb-2.5"
          style={{
            background: "#020204",
            border: "1px solid hsl(232 18% 11%)",
            fontFamily: "'JetBrains Mono', monospace",
          }}
        >
          <span style={{ color: `${catColor}70`, fontSize: "0.6rem" }}>›</span>
          <code
            className="truncate"
            style={{ fontSize: "0.65rem", color: `${catColor}cc` }}
          >
            {tool.command}
          </code>
        </div>

        {/* Tags */}
        <div className="flex gap-1 flex-wrap">
          {tool.tags?.slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="font-mono uppercase rounded-sm px-1.5 py-0.5"
              style={{
                fontSize: "0.58rem",
                letterSpacing: "0.08em",
                color: "hsl(232 10% 38%)",
                background: "hsl(235 22% 9%)",
                border: "1px solid hsl(232 18% 13%)",
              }}
            >
              {tag}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
