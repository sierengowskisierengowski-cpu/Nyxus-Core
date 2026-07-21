import { useMemo, useState } from "react";
import { Link, useParams } from "wouter";
import { useQuery } from "@tanstack/react-query";
import ReactMarkdown from "react-markdown";
import {
  BookOpen, Search, ArrowLeft, Clock, Terminal as TerminalIcon,
  Play, AlertTriangle, Loader2, ChevronRight,
} from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { DifficultyBadge } from "@/components/DifficultyBadge";
import { apiFetch } from "@/lib/api";

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

export default function Learn() {
  const { toolId } = useParams();
  return toolId ? <LearnDetail toolId={toolId} /> : <LearnIndex />;
}

// ── Index: all tools grouped by category, each links to its learning module ───
function LearnIndex() {
  const [query, setQuery] = useState("");

  const { data: tools = [], isLoading } = useQuery<Tool[]>({
    queryKey: ["learn-tools"],
    queryFn: () => apiFetch<Tool[]>("/api/tools"),
  });

  const grouped = useMemo(() => {
    const q = query.trim().toLowerCase();
    const filtered = q
      ? tools.filter(
          (t) =>
            t.name.toLowerCase().includes(q) ||
            t.description.toLowerCase().includes(q) ||
            t.category.toLowerCase().includes(q) ||
            t.tags.some((tag) => tag.toLowerCase().includes(q)),
        )
      : tools;
    const map = new Map<string, Tool[]>();
    for (const t of filtered) {
      if (!map.has(t.category)) map.set(t.category, []);
      map.get(t.category)!.push(t);
    }
    return [...map.entries()].sort((a, b) => a[0].localeCompare(b[0]));
  }, [tools, query]);

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h2 className="text-3xl font-bold tracking-tight flex items-center gap-3">
            <BookOpen className="h-8 w-8 text-primary" />
            Learn
          </h2>
          <p className="text-muted-foreground mt-2">
            Study guides for every tool in the lab — theory, flags, and real examples.
          </p>
        </div>
        <div className="relative w-full sm:w-72">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search modules..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="pl-9 h-9"
          />
        </div>
      </div>

      {isLoading ? (
        <div className="flex items-center gap-2 text-muted-foreground text-sm">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading modules...
        </div>
      ) : grouped.length === 0 ? (
        <div className="text-muted-foreground text-sm">No modules match "{query}".</div>
      ) : (
        <div className="space-y-8">
          {grouped.map(([category, catTools]) => (
            <section key={category}>
              <h3 className="text-xs font-mono uppercase tracking-wider text-muted-foreground mb-3">
                {category} · {catTools.length}
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                {catTools.map((tool) => (
                  <Link key={tool.id} href={`/learn/${tool.id}`}>
                    <div className="group h-full bg-card border rounded-lg p-4 cursor-pointer transition-colors hover:border-primary/40">
                      <div className="flex items-center justify-between gap-2 mb-1.5">
                        <span className="font-semibold text-sm text-foreground truncate">
                          {tool.name}
                        </span>
                        <ChevronRight className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
                      </div>
                      <p className="text-xs text-muted-foreground line-clamp-2 mb-3">
                        {tool.description}
                      </p>
                      <div className="flex items-center gap-2">
                        <DifficultyBadge difficulty={tool.difficulty} />
                        <span className="flex items-center gap-1 text-[10px] font-mono text-muted-foreground">
                          <Clock className="h-3 w-3" />
                          {tool.estimatedTime}
                        </span>
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Detail: a single tool's learning module, wired to real backend data ───────
function LearnDetail({ toolId }: { toolId: string }) {
  const { data: tool, isLoading, isError } = useQuery<Tool>({
    queryKey: ["learn-tool", toolId],
    queryFn: () => apiFetch<Tool>(`/api/tools/${toolId}`),
    retry: false,
  });

  if (isLoading) {
    return (
      <div className="p-6 max-w-4xl mx-auto">
        <div className="flex items-center gap-2 text-muted-foreground text-sm">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading module...
        </div>
      </div>
    );
  }

  if (isError || !tool) {
    return (
      <div className="p-6 max-w-4xl mx-auto space-y-4">
        <Link href="/learn">
          <Button variant="ghost" size="sm" className="gap-2">
            <ArrowLeft className="h-4 w-4" /> Back to Learn
          </Button>
        </Link>
        <div className="bg-card border rounded-lg p-8 text-center text-muted-foreground">
          Tool "{toolId}" was not found in the registry.
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <Link href="/learn">
        <Button variant="ghost" size="sm" className="gap-2 -ml-2">
          <ArrowLeft className="h-4 w-4" /> Back to Learn
        </Button>
      </Link>

      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="min-w-0">
          <h2 className="text-3xl font-bold tracking-tight flex items-center gap-3">
            <BookOpen className="h-8 w-8 text-primary flex-shrink-0" />
            {tool.name}
          </h2>
          <p className="text-muted-foreground mt-2">{tool.description}</p>
          <div className="flex items-center gap-3 mt-3 flex-wrap">
            <DifficultyBadge difficulty={tool.difficulty} />
            <span className="flex items-center gap-1 text-xs font-mono text-muted-foreground">
              <Clock className="h-3.5 w-3.5" />
              {tool.estimatedTime}
            </span>
            <span className="text-xs font-mono text-muted-foreground">{tool.category}</span>
          </div>
          {tool.tags.length > 0 && (
            <div className="flex items-center gap-1.5 mt-3 flex-wrap">
              {tool.tags.map((tag) => (
                <span
                  key={tag}
                  className="text-[10px] font-mono px-1.5 py-0.5 rounded-sm bg-muted text-muted-foreground"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>
        <Link href={`/tools?tool=${tool.id}`}>
          <Button className="gap-2">
            <Play className="h-4 w-4" /> Open in Tools
          </Button>
        </Link>
      </div>

      {/* Base command */}
      <div className="space-y-1.5">
        <div className="text-xs font-mono uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
          <TerminalIcon className="h-3.5 w-3.5" /> Base command
        </div>
        <div className="p-3 bg-black/70 rounded border border-border font-mono text-xs text-green-400 break-all">
          $ {tool.command}
        </div>
      </div>

      {/* Parameters */}
      {tool.params.length > 0 && (
        <div className="space-y-2">
          <div className="text-xs font-mono uppercase tracking-wider text-muted-foreground">
            Parameters
          </div>
          <div className="bg-card border rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-xs text-muted-foreground">
                  <th className="text-left font-medium px-4 py-2">Name</th>
                  <th className="text-left font-medium px-4 py-2">Description</th>
                  <th className="text-left font-medium px-4 py-2">Default</th>
                </tr>
              </thead>
              <tbody>
                {tool.params.map((p) => (
                  <tr key={p.name} className="border-b last:border-0">
                    <td className="px-4 py-2 font-mono text-xs">
                      {p.name}
                      {p.required && <span className="text-red-500 ml-1">*</span>}
                    </td>
                    <td className="px-4 py-2 text-xs text-muted-foreground">{p.label}</td>
                    <td className="px-4 py-2 font-mono text-xs text-muted-foreground">
                      {p.defaultValue || "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Learn content */}
      <div className="bg-card border rounded-lg p-6">
        {tool.learnContent ? (
          <div className="prose prose-invert prose-sm max-w-none">
            <ReactMarkdown>{tool.learnContent}</ReactMarkdown>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground m-0">
            No study notes are available for this tool yet. Consult the tool's official
            documentation.
          </p>
        )}
      </div>

      <div className="bg-yellow-500/10 border border-yellow-500/20 p-4 rounded-md">
        <h4 className="text-yellow-500 font-bold mb-1.5 flex items-center gap-2 text-sm">
          <AlertTriangle className="h-4 w-4" /> Rules of Engagement
        </h4>
        <p className="text-xs text-yellow-500/80 m-0 leading-relaxed">
          Only run tools against systems you own or have explicit written permission to
          test. This lab is scoped to the GowskiNet network (192.168.0.x). Unauthorized
          access or attacks against third-party systems are illegal.
        </p>
      </div>
    </div>
  );
}
