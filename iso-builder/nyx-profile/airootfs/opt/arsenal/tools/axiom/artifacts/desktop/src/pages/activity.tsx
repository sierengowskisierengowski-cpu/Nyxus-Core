import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Activity, MessageSquare, FolderOpen, CalendarClock, RotateCcw, Loader2, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useToast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";
import {
  useListActivityLog, getListActivityLogQueryKey,
  useUndoActivity,
  useGetActivitySummary, getGetActivitySummaryQueryKey,
} from "@workspace/api-client-react";
import type { ActivityEntry } from "@workspace/api-client-react";
import { useQueryClient } from "@tanstack/react-query";

const TYPE_META: Record<string, { icon: typeof MessageSquare; badge: string; dot: string }> = {
  chat:      { icon: MessageSquare, badge: "bg-sky-500/12 text-sky-300 border-sky-500/25",     dot: "bg-sky-400" },
  file_op:   { icon: FolderOpen,    badge: "bg-amber-500/12 text-amber-300 border-amber-500/25", dot: "bg-amber-400" },
  scheduled: { icon: CalendarClock, badge: "bg-emerald-500/12 text-emerald-300 border-emerald-500/25", dot: "bg-emerald-400" },
};

function ActivityRow({ entry, onUndo, undoPending }: {
  entry: ActivityEntry;
  onUndo: (id: number) => void;
  undoPending: boolean;
}) {
  const meta = TYPE_META[entry.type] ?? TYPE_META.chat;
  const Icon = meta.icon;
  const files = Array.isArray(entry.filesAffected) ? entry.filesAffected : [];

  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      className={cn(
        "flex items-start gap-3 py-3 px-4 border-b border-white/[0.04] hover:bg-white/[0.02] transition-colors group",
        entry.undone && "opacity-40"
      )}
      data-testid={`activity-row-${entry.id}`}
    >
      <div className="w-7 h-7 rounded-lg bg-white/5 flex items-center justify-center shrink-0 mt-0.5">
        <Icon className="w-3.5 h-3.5 text-muted-foreground" />
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5 flex-wrap">
          <Badge className={cn("text-[10px] h-4 px-1.5 border", meta.badge)}>
            {entry.type.replace("_", " ")}
          </Badge>
          <span className="text-xs text-muted-foreground/50">
            {new Date(entry.createdAt).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
          </span>
          {entry.undone && (
            <Badge className="text-[10px] h-4 px-1.5 bg-white/5 text-muted-foreground border-white/10">Undone</Badge>
          )}
        </div>
        <p className="text-sm text-foreground/80 truncate">{entry.description}</p>
        {entry.detail && <p className="text-xs text-muted-foreground/60 truncate mt-0.5">{entry.detail}</p>}
        {files.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-1.5">
            {files.slice(0, 3).map((f, i) => (
              <span key={i} className="text-[10px] px-1.5 py-0.5 rounded bg-white/5 text-muted-foreground font-mono">
                {typeof f === "string" ? f.split("/").pop() : f}
              </span>
            ))}
            {files.length > 3 && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/5 text-muted-foreground">+{files.length - 3} more</span>
            )}
          </div>
        )}
      </div>

      {entry.undoable && !entry.undone && (
        <Button
          size="sm"
          variant="ghost"
          className="h-7 text-xs text-muted-foreground hover:text-amber-300 hover:bg-amber-500/10 opacity-0 group-hover:opacity-100 transition-all shrink-0"
          onClick={() => onUndo(entry.id)}
          disabled={undoPending}
          data-testid={`button-undo-${entry.id}`}
        >
          {undoPending ? <Loader2 className="w-3 h-3 animate-spin mr-1" /> : <RotateCcw className="w-3 h-3 mr-1" />}
          Undo
        </Button>
      )}
    </motion.div>
  );
}

const FILTER_TABS = [
  { label: "All",       value: "all" },
  { label: "File Ops",  value: "file_op" },
  { label: "Chat",      value: "chat" },
  { label: "Scheduled", value: "scheduled" },
] as const;

export default function ActivityLog() {
  const [filter, setFilter] = useState<"all" | "file_op" | "chat" | "scheduled">("all");
  const [undoingId, setUndoingId] = useState<number | null>(null);
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const { data: activities = [], isLoading, refetch, isFetching } = useListActivityLog(
    filter === "all" ? undefined : { type: filter },
    { query: { queryKey: getListActivityLogQueryKey(filter === "all" ? undefined : { type: filter }) } }
  );

  const { data: summary } = useGetActivitySummary({ query: { queryKey: getGetActivitySummaryQueryKey() } });

  const undoActivity = useUndoActivity();

  const handleUndo = (id: number) => {
    setUndoingId(id);
    undoActivity.mutate({ id }, {
      onSuccess: (r) => {
        setUndoingId(null);
        queryClient.invalidateQueries({ queryKey: getListActivityLogQueryKey() });
        toast({ title: r.success ? "Action undone" : "Cannot undo", description: r.message, variant: r.success ? "default" : "destructive" });
      },
      onError: () => {
        setUndoingId(null);
        toast({ title: "Undo failed", variant: "destructive" });
      },
    });
  };

  return (
    <div className="flex flex-col h-full">
      <div className="px-6 py-4 border-b border-white/[0.07]">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-base font-semibold flex items-center gap-2">
              <Activity className="w-4 h-4 text-emerald-400" />
              Activity Log
            </h1>
            {summary && (
              <div className="flex items-center gap-3 mt-2 flex-wrap">
                <div className="flex items-center gap-1.5">
                  <span className="text-lg font-bold">{summary.total}</span>
                  <span className="text-xs text-muted-foreground">total actions</span>
                </div>
                <div className="h-3 w-px bg-white/10" />
                <div className="flex items-center gap-3 text-xs text-muted-foreground">
                  <span className="flex items-center gap-1"><MessageSquare className="w-3 h-3 text-sky-400" /> {summary.byType.chat} chats</span>
                  <span className="flex items-center gap-1"><FolderOpen className="w-3 h-3 text-amber-400" /> {summary.byType.file_op} file ops</span>
                  <span className="flex items-center gap-1"><CalendarClock className="w-3 h-3 text-emerald-400" /> {summary.byType.scheduled} scheduled</span>
                </div>
                <div className="h-3 w-px bg-white/10" />
                <span className="text-xs text-emerald-400 font-medium">{summary.recentCount} today</span>
              </div>
            )}
          </div>
          <Button
            size="sm"
            variant="ghost"
            className="h-7 text-xs text-muted-foreground hover:text-foreground border border-transparent hover:border-white/15 mt-1"
            onClick={() => refetch()}
            disabled={isFetching}
            title="Refresh"
          >
            <RefreshCw className={cn("w-3 h-3 mr-1.5", isFetching && "animate-spin")} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Filter tabs */}
      <div className="px-6 pt-3 pb-0 flex gap-1">
        {FILTER_TABS.map(tab => (
          <button
            key={tab.value}
            onClick={() => setFilter(tab.value)}
            className={cn(
              "text-xs px-3 py-1.5 rounded-lg transition-all duration-150 border",
              filter === tab.value
                ? "tab-active"
                : "border-transparent text-muted-foreground hover:bg-white/5 hover:text-foreground hover:border-white/10"
            )}
            data-testid={`tab-filter-${tab.value}`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <ScrollArea className="flex-1 mt-2">
        {isLoading ? (
          <div className="space-y-0 px-2">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="flex gap-3 px-4 py-3">
                <Skeleton className="w-7 h-7 rounded-lg bg-white/5 shrink-0" />
                <div className="flex-1 space-y-1.5">
                  <Skeleton className="h-3 w-16 bg-white/5" />
                  <Skeleton className="h-4 w-3/4 bg-white/5" />
                </div>
              </div>
            ))}
          </div>
        ) : activities.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-[300px] gap-3">
            <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-400/20 flex items-center justify-center">
              <Activity className="w-6 h-6 text-emerald-400" />
            </div>
            <p className="text-sm text-muted-foreground">No activity yet</p>
          </div>
        ) : (
          <AnimatePresence initial={false}>
            {activities.map(entry => (
              <ActivityRow key={entry.id} entry={entry} onUndo={handleUndo} undoPending={undoingId === entry.id} />
            ))}
          </AnimatePresence>
        )}
      </ScrollArea>
    </div>
  );
}
