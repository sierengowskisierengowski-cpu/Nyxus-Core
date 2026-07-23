import { useState, useEffect, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { useLocation } from "wouter";
import { Search, Terminal, ChevronRight, Zap } from "lucide-react";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { DifficultyBadge } from "./DifficultyBadge";
import { apiFetch } from "@/lib/api";

interface Tool {
  id: string;
  name: string;
  description: string;
  category: string;
  difficulty: string;
  estimatedTime: string;
  command: string;
  isFavorite: boolean;
  tags: string[];
  params: unknown[];
  learnContent?: string;
}

interface CommandPaletteProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
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

export function CommandPalette({ open, onOpenChange }: CommandPaletteProps) {
  const [query, setQuery] = useState("");
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [, setLocation] = useLocation();

  const { data: allTools = [] } = useQuery<Tool[]>({
    queryKey: ["tools-all"],
    queryFn: () => apiFetch<Tool[]>("/api/tools"),
    staleTime: 60000,
  });

  const filtered = query.trim().length === 0
    ? allTools.slice(0, 10)
    : allTools.filter((t) => {
        const q = query.toLowerCase();
        return (
          t.name.toLowerCase().includes(q) ||
          t.category.toLowerCase().includes(q) ||
          t.description.toLowerCase().includes(q) ||
          t.tags.some((tag) => tag.toLowerCase().includes(q))
        );
      }).slice(0, 12);

  useEffect(() => { setSelectedIdx(0); }, [query, open]);
  useEffect(() => { if (!open) setQuery(""); }, [open]);

  const launch = useCallback((tool: Tool) => {
    onOpenChange(false);
    setLocation(`/tools?tool=${tool.id}`);
  }, [onOpenChange, setLocation]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") { e.preventDefault(); setSelectedIdx((i) => Math.min(i + 1, filtered.length - 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setSelectedIdx((i) => Math.max(i - 1, 0)); }
    else if (e.key === "Enter") { e.preventDefault(); if (filtered[selectedIdx]) launch(filtered[selectedIdx]); }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="p-0 gap-0 max-w-xl overflow-hidden"
        aria-describedby={undefined}
        style={{
          background: "hsl(235 30% 5.5%)",
          border: "1px solid hsl(263 55% 62% / 0.2)",
          boxShadow: "0 0 40px hsl(263 55% 62% / 0.08), 0 25px 60px rgba(0,0,0,0.8)",
        }}
      >
        {/* Top accent */}
        <div className="h-px" style={{ background: "linear-gradient(90deg, transparent, hsl(263 55% 62% / 0.5), transparent)" }} />

        {/* Search */}
        <div
          className="flex items-center gap-3 px-4 py-3.5"
          style={{ borderBottom: "1px solid hsl(232 18% 11%)" }}
        >
          <Search className="h-4 w-4 flex-shrink-0" style={{ color: "hsl(263 55% 60%)" }} />
          <Input
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Search 83 tools — by name, category, or tag..."
            className="border-0 bg-transparent focus-visible:ring-0 text-sm h-auto p-0"
            style={{ caretColor: "hsl(263 55% 62%)" }}
          />
          <kbd className="flex-shrink-0">ESC</kbd>
        </div>

        {/* Category hints when empty */}
        {query.trim().length === 0 && (
          <div
            className="px-4 py-2 flex items-center gap-2 flex-wrap"
            style={{ borderBottom: "1px solid hsl(232 18% 9%)", background: "hsl(235 28% 5%)" }}
          >
            <span className="text-[9px] font-mono uppercase tracking-wider" style={{ color: "hsl(232 10% 30%)" }}>Quick:</span>
            {["WiFi", "Bluetooth", "Network", "Web", "Password"].map((tag) => (
              <button
                key={tag}
                className="text-[10px] font-mono px-1.5 py-0.5 rounded-sm transition-colors"
                style={{ background: "hsl(235 22% 9%)", border: "1px solid hsl(232 18% 14%)", color: "hsl(232 10% 45%)" }}
                onClick={() => setQuery(tag)}
                onMouseEnter={(e) => {
                  (e.currentTarget as HTMLButtonElement).style.color = "hsl(263 55% 65%)";
                  (e.currentTarget as HTMLButtonElement).style.borderColor = "hsl(263 55% 62% / 0.3)";
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLButtonElement).style.color = "hsl(232 10% 45%)";
                  (e.currentTarget as HTMLButtonElement).style.borderColor = "hsl(232 18% 14%)";
                }}
              >
                {tag}
              </button>
            ))}
          </div>
        )}

        {/* Results */}
        <div className="max-h-[400px] overflow-y-auto">
          {filtered.length === 0 ? (
            <div className="px-4 py-10 text-center">
              <Terminal className="h-8 w-8 mx-auto mb-2" style={{ color: "hsl(232 10% 20%)" }} />
              <p className="text-sm" style={{ color: "hsl(232 10% 38%)" }}>No tools match "{query}"</p>
            </div>
          ) : (
            <div className="py-1">
              {filtered.map((tool, idx) => {
                const catColor = CATEGORY_COLOR[tool.category] ?? "#9b7fef";
                const isSelected = idx === selectedIdx;
                return (
                  <button
                    key={tool.id}
                    className="w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors relative"
                    style={{
                      background: isSelected ? `${catColor}0c` : "transparent",
                      borderLeft: isSelected ? `2px solid ${catColor}` : "2px solid transparent",
                    }}
                    onMouseEnter={() => setSelectedIdx(idx)}
                    onClick={() => launch(tool)}
                  >
                    <div
                      className="w-8 h-8 rounded flex items-center justify-center flex-shrink-0"
                      style={{
                        background: isSelected ? `${catColor}15` : "hsl(235 22% 9%)",
                        border: `1px solid ${isSelected ? catColor + "30" : "hsl(232 18% 13%)"}`,
                      }}
                    >
                      <Terminal className="h-3.5 w-3.5" style={{ color: isSelected ? catColor : "hsl(232 10% 35%)" }} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap mb-0.5">
                        <span className="font-semibold text-sm" style={{ color: isSelected ? "hsl(220 20% 95%)" : "hsl(220 20% 85%)" }}>
                          {tool.name}
                        </span>
                        <DifficultyBadge difficulty={tool.difficulty} />
                      </div>
                      <div className="text-[11px] truncate" style={{ color: "hsl(232 10% 40%)" }}>
                        <span className="font-semibold mr-1" style={{ color: catColor + "cc" }}>{tool.category}</span>
                        · {tool.description.slice(0, 70)}
                      </div>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <code
                        className="text-[10px] font-mono px-1.5 py-0.5 rounded-sm"
                        style={{
                          background: "#020204",
                          border: "1px solid hsl(232 18% 11%)",
                          color: `${catColor}80`,
                        }}
                      >
                        {tool.command}
                      </code>
                      <ChevronRight
                        className="h-3.5 w-3.5 transition-opacity"
                        style={{ color: catColor, opacity: isSelected ? 1 : 0 }}
                      />
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <div
          className="px-4 py-2 flex items-center gap-4"
          style={{ borderTop: "1px solid hsl(232 18% 10%)", background: "hsl(235 28% 4.5%)" }}
        >
          <div className="flex items-center gap-3 text-[10px] font-mono" style={{ color: "hsl(232 10% 30%)" }}>
            <span className="flex items-center gap-1"><kbd>↑↓</kbd> navigate</span>
            <span className="flex items-center gap-1"><kbd>↵</kbd> launch</span>
            <span className="flex items-center gap-1"><kbd>⌘K</kbd> toggle</span>
          </div>
          <div className="ml-auto flex items-center gap-1.5 text-[10px] font-mono" style={{ color: "hsl(263 55% 50%)" }}>
            <Zap className="h-3 w-3" />
            {filtered.length} results
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
