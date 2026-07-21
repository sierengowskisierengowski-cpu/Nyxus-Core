import { useEffect, useRef, useState } from "react";
import { Copy, Download, XCircle, Loader2, CheckCircle2, XOctagon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { wsUrl } from "@/lib/api";

interface TerminalProps {
  runId: number | null;
  command: string;
  onKill?: () => void;
}

interface LogLine {
  id: number;
  text: string;
  type: "default" | "success" | "error" | "warning" | "info" | "cmd";
  ts: string;
}

function classifyLine(text: string): LogLine["type"] {
  const lower = text.toLowerCase();
  if (
    lower.includes("error") || lower.includes("failed") ||
    lower.includes("err:") || text.startsWith("ERR") || text.includes("[!]")
  ) return "error";
  if (lower.includes("warning") || lower.includes("warn")) return "warning";
  if (
    lower.includes("open") || lower.includes("found") ||
    lower.includes("success") || lower.includes(" up ") ||
    text.includes("[+]") || text.startsWith("Host is up")
  ) return "success";
  if (
    text.startsWith("[*]") || text.startsWith("#") ||
    text.startsWith("Nmap scan") || text.startsWith("Starting")
  ) return "info";
  return "default";
}

const COLOR: Record<LogLine["type"], string> = {
  default:  "#b8c4d8",
  cmd:      "#a78bdf",
  success:  "#4ade80",
  error:    "#f87171",
  warning:  "#fbbf24",
  info:     "#67e8f9",
};

export function Terminal({ runId, command, onKill }: TerminalProps) {
  const [lines, setLines] = useState<LogLine[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isDone, setIsDone] = useState(false);
  const [exitCode, setExitCode] = useState<number | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const { toast } = useToast();
  const lineId = useRef(0);

  const now = () => new Date().toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });

  const addLine = (text: string, forceType?: LogLine["type"]) => {
    setLines((prev) => [...prev, {
      id: lineId.current++,
      text,
      type: forceType ?? classifyLine(text),
      ts: now(),
    }]);
  };

  const scrollToBottom = () => {
    setTimeout(() => {
      if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }, 20);
  };

  useEffect(() => {
    if (!runId) return;
    setLines([]);
    setIsConnected(false);
    setIsDone(false);
    setExitCode(null);
    lineId.current = 0;

    const url = wsUrl(`/ws/run/${runId}`);
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      addLine(`$ ${command}`, "cmd");
      ws.send(JSON.stringify({ command }));
      scrollToBottom();
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === "output" || msg.type === "error") {
          addLine(msg.line, msg.type === "error" ? "error" : undefined);
          scrollToBottom();
        } else if (msg.type === "done") {
          setExitCode(msg.exitCode);
          setIsDone(true);
          scrollToBottom();
        }
      } catch {
        addLine(event.data);
        scrollToBottom();
      }
    };

    ws.onerror = () => {
      addLine("[WebSocket error — could not connect to backend]", "error");
      setIsDone(true);
    };

    ws.onclose = () => setIsConnected(false);

    return () => ws.close();
  }, [runId]);

  const handleCopy = () => {
    navigator.clipboard.writeText(lines.map((l) => l.text).join("\n"));
    toast({ title: "Copied to clipboard" });
  };

  const handleDownload = () => {
    const content = lines.map((l) => `[${l.ts}] ${l.text}`).join("\n");
    const blob = new Blob([content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `gsl-run-${runId}-${new Date().toISOString().slice(0,10)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const statusEl = isDone ? (
    exitCode === 0 ? (
      <span className="flex items-center gap-1.5 font-mono text-[10px]" style={{ color: "#4ade80" }}>
        <CheckCircle2 className="h-3 w-3" />
        exit 0 · ok
      </span>
    ) : (
      <span className="flex items-center gap-1.5 font-mono text-[10px]" style={{ color: "#f87171" }}>
        <XOctagon className="h-3 w-3" />
        exit {exitCode}
      </span>
    )
  ) : isConnected ? (
    <span className="flex items-center gap-1.5 font-mono text-[10px]" style={{ color: "#60a5fa" }}>
      <Loader2 className="h-3 w-3 animate-spin" />
      running
    </span>
  ) : (
    <span className="text-[10px] font-mono text-muted-foreground">connecting...</span>
  );

  return (
    <div
      className="flex flex-col h-full overflow-hidden"
      style={{ background: "#030305", fontFamily: "'JetBrains Mono', monospace" }}
    >
      {/* Title bar */}
      <div
        className="flex items-center justify-between px-3 py-1.5 flex-shrink-0"
        style={{ background: "hsl(235 28% 5.5%)", borderBottom: "1px solid hsl(232 18% 11%)" }}
      >
        <div className="flex items-center gap-3">
          {/* Traffic lights */}
          <div className="flex gap-1.5">
            <div className="w-2.5 h-2.5 rounded-full" style={{ background: "#ff5f5780" }} />
            <div className="w-2.5 h-2.5 rounded-full" style={{ background: "#febc2e80" }} />
            <div className="w-2.5 h-2.5 rounded-full" style={{ background: "#28c84080" }} />
          </div>
          <div className="h-3 w-px" style={{ background: "hsl(232 18% 14%)" }} />
          <span className="text-[10px] font-mono" style={{ color: "hsl(232 10% 35%)" }}>
            nyx-cosmic — run #{runId}
          </span>
        </div>

        <div className="flex items-center gap-3">
          {statusEl}
          <div className="h-3 w-px" style={{ background: "hsl(232 18% 14%)" }} />
          <span className="text-[9px] font-mono" style={{ color: "hsl(232 10% 28%)" }}>
            {lines.length} lines
          </span>
          <div className="flex items-center gap-0.5">
            <Button
              variant="ghost" size="icon"
              className="h-5 w-5 hover:text-foreground"
              style={{ color: "hsl(232 10% 35%)" }}
              onClick={handleCopy}
              title="Copy output"
            >
              <Copy className="h-3 w-3" />
            </Button>
            <Button
              variant="ghost" size="icon"
              className="h-5 w-5 hover:text-foreground"
              style={{ color: "hsl(232 10% 35%)" }}
              onClick={handleDownload}
              title="Download log"
            >
              <Download className="h-3 w-3" />
            </Button>
            {onKill && !isDone && (
              <Button
                variant="ghost" size="icon"
                className="h-5 w-5 hover:bg-red-500/10"
                style={{ color: "rgba(248,113,113,0.7)" }}
                onClick={onKill}
                title="Kill process"
              >
                <XCircle className="h-3 w-3" />
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Output area */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto text-[11px] leading-relaxed"
        style={{ padding: "10px 0" }}
      >
        {lines.length === 0 ? (
          <div className="px-4 py-2 italic text-[10px]" style={{ color: "hsl(232 10% 25%)" }}>
            Connecting to backend...
          </div>
        ) : (
          lines.map((line, idx) => (
            <div
              key={line.id}
              className="flex gap-0 px-0 group/line hover:bg-white/[0.015] transition-colors"
            >
              {/* Line number */}
              <span
                className="select-none flex-shrink-0 text-right tabular-nums"
                style={{
                  width: "42px",
                  paddingRight: "10px",
                  paddingLeft: "8px",
                  color: "hsl(232 10% 22%)",
                  fontSize: "0.65rem",
                  paddingTop: "1px",
                }}
              >
                {idx + 1}
              </span>
              {/* Timestamp */}
              <span
                className="select-none flex-shrink-0 text-[9px] tabular-nums opacity-0 group-hover/line:opacity-100 transition-opacity"
                style={{
                  width: "64px",
                  color: "hsl(232 10% 28%)",
                  paddingTop: "1px",
                  paddingRight: "8px",
                }}
              >
                {line.ts}
              </span>
              {/* Content */}
              <span
                className="flex-1 break-all whitespace-pre-wrap pr-4"
                style={{ color: COLOR[line.type] }}
              >
                {line.text}
              </span>
            </div>
          ))
        )}

        {isConnected && !isDone && (
          <div className="flex gap-0 px-0 mt-0.5">
            <span style={{ width: "42px" }} />
            <span style={{ width: "64px" }} />
            <span className="terminal-cursor" />
          </div>
        )}

        {isDone && (
          <div
            className="mx-4 mt-2 px-3 py-1.5 rounded-sm flex items-center gap-2"
            style={{
              background: exitCode === 0 ? "rgba(74,222,128,0.05)" : "rgba(248,113,113,0.05)",
              border: `1px solid ${exitCode === 0 ? "rgba(74,222,128,0.15)" : "rgba(248,113,113,0.15)"}`,
              fontSize: "0.65rem",
            }}
          >
            {exitCode === 0 ? (
              <CheckCircle2 className="h-3 w-3" style={{ color: "#4ade80" }} />
            ) : (
              <XOctagon className="h-3 w-3" style={{ color: "#f87171" }} />
            )}
            <span className="font-mono" style={{ color: exitCode === 0 ? "#4ade80" : "#f87171" }}>
              Process exited with code {exitCode} · {lines.length - 1} output lines
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
