import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Search, Play, BookOpen, Terminal as TerminalIcon, AlertTriangle, Star, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

import { ToolCard } from "@/components/ToolCard";
import { Terminal } from "@/components/Terminal";
import { DifficultyBadge } from "@/components/DifficultyBadge";
import { apiFetch } from "@/lib/api";
import ReactMarkdown from "react-markdown";

interface ToolParam {
  name: string;
  label: string;
  type: string;
  defaultValue: string;
  placeholder?: string;
  required?: boolean;
}

interface Tool {
  id: string;
  name: string;
  description: string;
  category: string;
  difficulty: string;
  estimatedTime: string;
  command: string;
  params: ToolParam[];
  learnContent?: string;
  isFavorite: boolean;
  tags: string[];
}

const ALL_CATEGORIES = [
  "All",
  "Network Scanning",
  "WiFi Security",
  "Web Application Testing",
  "Password & Hash Testing",
  "Exploitation Framework",
  "Honeypot Testing",
  "Packet Analysis",
  "Bluetooth & RF",
  "Stress Testing",
  "Forensics & Analysis",
  "OSINT",
  "Vulnerability Scanning",
  "Cryptography",
  "Steganography",
  "Reverse Engineering",
  "Docker & Container Security",
  "Social Engineering",
  "IoT & Hardware",
  "GowskiNet Specific",
  "CTF & Practice",
];

function buildCommand(tool: Tool, params: Record<string, string>): string {
  // tools_data has commandTemplate — but we don't expose it via the API
  // We fetch the full tool and look for template-style substitution
  // The backend returns command as the base command; params build the args
  // For the real command, we POST to /api/execute with params and get back the resolved command
  // For the preview, replicate the template substitution client-side
  // We call /api/tools/{id} which returns the tool but not commandTemplate
  // So we build using a simple heuristic or ask the server
  // Actually the proper approach: resolve via the API
  return `[preview pending...]`;
}

export default function Tools() {
  const [selectedCategory, setSelectedCategory] = useState("All");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedTool, setSelectedTool] = useState<Tool | null>(null);
  const [activeRunId, setActiveRunId] = useState<number | null>(null);
  const [paramsData, setParamsData] = useState<Record<string, string>>({});
  const [showConfirm, setShowConfirm] = useState(false);
  const [resolvedCommand, setResolvedCommand] = useState("");
  const qc = useQueryClient();

  const { data: tools = [], isLoading } = useQuery<Tool[]>({
    queryKey: ["tools", selectedCategory, searchQuery],
    queryFn: () => {
      const params = new URLSearchParams();
      if (selectedCategory !== "All") params.set("category", selectedCategory);
      if (searchQuery) params.set("search", searchQuery);
      return apiFetch<Tool[]>(`/api/tools?${params}`);
    },
  });

  const favoriteMutation = useMutation({
    mutationFn: ({ toolId, favorite }: { toolId: string; favorite: boolean }) =>
      apiFetch(`/api/tools/${toolId}/favorites`, {
        method: "POST",
        body: JSON.stringify({ favorite }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tools"] }),
  });

  const executeMutation = useMutation({
    mutationFn: ({ toolId, params, command }: { toolId: string; params: Record<string, string>; command: string }) =>
      apiFetch<{ runId: number }>(`/api/execute`, {
        method: "POST",
        body: JSON.stringify({ toolId, params, command }),
      }),
  });

  const handleToolSelect = (tool: Tool) => {
    setSelectedTool(tool);
    setActiveRunId(null);
    const initial: Record<string, string> = {};
    tool.params?.forEach((p) => {
      initial[p.name] = p.defaultValue ?? "";
    });
    setParamsData(initial);
  };

  // Resolve command preview from the server
  useEffect(() => {
    if (!selectedTool) return;
    const timer = setTimeout(async () => {
      try {
        const result = await apiFetch<{ command: string }>(`/api/tools/${selectedTool.id}/preview-command`, {
          method: "POST",
          body: JSON.stringify({ params: paramsData }),
        });
        setResolvedCommand(result.command);
      } catch {
        // Fallback: client-side naive substitution
        setResolvedCommand(buildClientCommand(selectedTool, paramsData));
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [selectedTool, paramsData]);

  const handleDeploy = async () => {
    if (!selectedTool) return;
    setShowConfirm(false);
    try {
      const { runId } = await executeMutation.mutateAsync({
        toolId: selectedTool.id,
        params: paramsData,
        command: resolvedCommand,
      });
      setActiveRunId(runId);
      qc.invalidateQueries({ queryKey: ["runs"] });
    } catch (e: any) {
      console.error("Execute failed:", e);
    }
  };

  return (
    <div className="flex h-[calc(100vh-40px)] overflow-hidden">
      {/* Left Sidebar - Categories */}
      <div className="w-56 border-r bg-card/30 flex-col hidden lg:flex flex-shrink-0">
        <div className="p-3 border-b">
          <div className="relative">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search tools..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-background pl-9 h-8 text-sm"
            />
          </div>
        </div>
        <ScrollArea className="flex-1">
          <div className="p-2 space-y-0.5">
            {ALL_CATEGORIES.map((cat) => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`w-full text-left px-3 py-1.5 rounded text-xs transition-colors ${
                  selectedCategory === cat
                    ? "bg-primary text-primary-foreground font-medium"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                }`}
              >
                {cat}
              </button>
            ))}
          </div>
        </ScrollArea>
      </div>

      {/* Main Content - Tool Grid */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="p-4 border-b bg-card/20 flex items-center justify-between flex-shrink-0">
          <h2 className="text-xl font-bold flex items-center gap-2">
            <TerminalIcon className="h-5 w-5 text-primary" />
            {selectedCategory === "All" ? "All Tools" : selectedCategory}
            <span className="text-sm font-normal text-muted-foreground ml-1">({tools.length})</span>
          </h2>
        </div>
        <ScrollArea className="flex-1">
          <div className="p-4">
            {isLoading ? (
              <div className="text-muted-foreground text-sm font-mono animate-pulse">Loading tools...</div>
            ) : tools.length === 0 ? (
              <div className="text-muted-foreground text-sm">No tools found.</div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                {tools.map((tool) => (
                  <ToolCard
                    key={tool.id}
                    tool={tool}
                    onClick={handleToolSelect}
                    onToggleFavorite={(id, fav) => favoriteMutation.mutate({ toolId: id, favorite: fav })}
                    isSelected={selectedTool?.id === tool.id}
                  />
                ))}
              </div>
            )}
          </div>
        </ScrollArea>
      </div>

      {/* Right Panel - Config & Terminal */}
      {selectedTool && (
        <div className="w-[440px] border-l bg-card flex flex-col shadow-2xl z-10 flex-shrink-0">
          <div className="p-4 border-b bg-card flex-shrink-0">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <h3 className="text-lg font-bold text-primary truncate">{selectedTool.name}</h3>
                  <DifficultyBadge difficulty={selectedTool.difficulty} />
                </div>
                <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{selectedTool.description}</p>
              </div>
              <div className="flex gap-1 flex-shrink-0">
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7"
                  onClick={() => favoriteMutation.mutate({ toolId: selectedTool.id, favorite: !selectedTool.isFavorite })}
                >
                  <Star className={`h-4 w-4 ${selectedTool.isFavorite ? "fill-yellow-500 text-yellow-500" : ""}`} />
                </Button>
                <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setSelectedTool(null)}>
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>

          <Tabs defaultValue="config" className="flex-1 flex flex-col overflow-hidden">
            <div className="border-b px-4 flex-shrink-0">
              <TabsList className="w-full bg-transparent p-0 mt-2 h-auto gap-4 justify-start">
                <TabsTrigger
                  value="config"
                  className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent px-2 py-2 text-sm"
                >
                  Configuration
                </TabsTrigger>
                <TabsTrigger
                  value="learn"
                  className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent px-2 py-2 text-sm"
                >
                  <BookOpen className="h-3.5 w-3.5 mr-1" />
                  Learn
                </TabsTrigger>
              </TabsList>
            </div>

            <TabsContent value="config" className="flex-1 flex flex-col m-0 p-0 overflow-hidden">
              <ScrollArea className="flex-1 p-4">
                <div className="space-y-4">
                  {selectedTool.params?.length === 0 && (
                    <p className="text-sm text-muted-foreground italic">No parameters required.</p>
                  )}
                  {selectedTool.params?.map((param) => (
                    <div key={param.name} className="space-y-1.5">
                      <Label htmlFor={param.name} className="text-xs font-medium">
                        {param.label}
                        {param.required && <span className="text-red-500 ml-1">*</span>}
                      </Label>
                      {param.type === "select" ? (
                        <Select
                          value={paramsData[param.name] ?? param.defaultValue}
                          onValueChange={(v) => setParamsData((prev) => ({ ...prev, [param.name]: v }))}
                        >
                          <SelectTrigger className="font-mono text-xs h-8">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {getSelectOptions(param.name, param.defaultValue).map((opt) => (
                              <SelectItem key={opt.value} value={opt.value} className="font-mono text-xs">
                                {opt.label}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      ) : (
                        <Input
                          id={param.name}
                          value={paramsData[param.name] ?? ""}
                          onChange={(e) => setParamsData((prev) => ({ ...prev, [param.name]: e.target.value }))}
                          placeholder={param.placeholder || param.defaultValue || ""}
                          className="font-mono text-xs h-8"
                        />
                      )}
                    </div>
                  ))}

                  <div className="pt-4 space-y-1.5 border-t border-border/50">
                    <Label className="text-muted-foreground uppercase text-xs tracking-wider">Command Preview</Label>
                    <div className="p-3 bg-black/70 rounded border border-border font-mono text-xs text-green-400 break-all leading-relaxed">
                      $ {resolvedCommand || buildClientCommand(selectedTool, paramsData)}
                    </div>
                  </div>

                  <Dialog open={showConfirm} onOpenChange={setShowConfirm}>
                    <DialogTrigger asChild>
                      <Button className="w-full h-10 font-bold shadow-lg" disabled={executeMutation.isPending}>
                        <Play className="mr-2 h-4 w-4" />
                        {executeMutation.isPending ? "LAUNCHING..." : "EXECUTE"}
                      </Button>
                    </DialogTrigger>
                    <DialogContent>
                      <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                          <AlertTriangle className="h-5 w-5 text-yellow-500" />
                          Confirm Execution
                        </DialogTitle>
                        <DialogDescription>
                          You are about to execute a live security tool on the GowskiNet network (192.168.0.x). Only run against systems you own or have explicit permission to test.
                        </DialogDescription>
                      </DialogHeader>
                      <div className="p-4 bg-black rounded border border-border font-mono text-xs text-green-400 break-all my-2">
                        $ {resolvedCommand || buildClientCommand(selectedTool, paramsData)}
                      </div>
                      <DialogFooter>
                        <Button variant="outline" onClick={() => setShowConfirm(false)}>
                          Cancel
                        </Button>
                        <Button onClick={handleDeploy} className="bg-red-600 hover:bg-red-700 text-white">
                          Execute Now
                        </Button>
                      </DialogFooter>
                    </DialogContent>
                  </Dialog>
                </div>
              </ScrollArea>

              {activeRunId && (
                <div className="h-72 border-t border-border flex-shrink-0">
                  <Terminal
                    runId={activeRunId}
                    command={resolvedCommand || buildClientCommand(selectedTool, paramsData)}
                    onKill={async () => {
                      try {
                        await apiFetch(`/api/runs/${activeRunId}/kill`, { method: "POST" });
                      } catch (e) {
                        console.error("Kill failed:", e);
                      }
                      setActiveRunId(null);
                    }}
                  />
                </div>
              )}
            </TabsContent>

            <TabsContent value="learn" className="flex-1 overflow-auto p-4 m-0">
              {selectedTool.learnContent ? (
                <div className="prose prose-invert prose-sm max-w-none">
                  <ReactMarkdown>{selectedTool.learnContent}</ReactMarkdown>
                </div>
              ) : (
                <div className="flex items-start gap-3 p-4 bg-muted/50 rounded-lg border border-border">
                  <BookOpen className="h-5 w-5 text-primary shrink-0 mt-0.5" />
                  <p className="text-sm text-muted-foreground m-0">
                    No learn content available for this tool yet. Check the tool's official documentation.
                  </p>
                </div>
              )}
            </TabsContent>
          </Tabs>
        </div>
      )}
    </div>
  );
}

function buildClientCommand(tool: Tool, params: Record<string, string>): string {
  // Simple template substitution used as preview fallback
  let cmd = tool.command;
  // Build args
  const parts: string[] = [cmd];
  tool.params?.forEach((p) => {
    const val = params[p.name];
    if (val && val !== "") {
      parts.push(val);
    }
  });
  return parts.join(" ");
}

function getSelectOptions(paramName: string, defaultValue: string) {
  const maps: Record<string, Array<{ value: string; label: string }>> = {
    scan_type: [
      { value: "-sV", label: "-sV (Version Detection)" },
      { value: "-sS", label: "-sS (SYN Scan)" },
      { value: "-sT", label: "-sT (TCP Connect)" },
      { value: "-sU", label: "-sU (UDP Scan)" },
      { value: "-A", label: "-A (Aggressive)" },
      { value: "-sn", label: "-sn (Ping Scan)" },
    ],
    protocol: [
      { value: "ssh", label: "SSH" },
      { value: "ftp", label: "FTP" },
      { value: "http-get", label: "HTTP GET" },
      { value: "smb", label: "SMB" },
      { value: "rdp", label: "RDP" },
      { value: "telnet", label: "Telnet" },
      { value: "mysql", label: "MySQL" },
    ],
    severity: [
      { value: "critical", label: "Critical only" },
      { value: "high,critical", label: "High + Critical" },
      { value: "medium,high,critical", label: "Medium/High/Critical" },
      { value: "low,medium,high,critical", label: "All severities" },
    ],
    action: [
      { value: "start", label: "start" },
      { value: "stop", label: "stop" },
      { value: "check", label: "check" },
    ],
    algorithm: [
      { value: "md5sum", label: "MD5" },
      { value: "sha1sum", label: "SHA1" },
      { value: "sha256sum", label: "SHA256" },
      { value: "sha512sum", label: "SHA512" },
      { value: "b2sum", label: "BLAKE2" },
    ],
  };
  return maps[paramName] ?? [{ value: defaultValue, label: defaultValue }];
}
