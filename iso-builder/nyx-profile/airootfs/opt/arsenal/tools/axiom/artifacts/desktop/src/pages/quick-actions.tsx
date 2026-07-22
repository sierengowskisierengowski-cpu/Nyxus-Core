import { useState, useCallback } from "react";
import { motion, AnimatePresence, Reorder } from "framer-motion";
import { Plus, Zap, Edit2, Trash2, Loader2, GripVertical, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";
import {
  useListQuickActions, getListQuickActionsQueryKey,
  useCreateQuickAction, useUpdateQuickAction, useDeleteQuickAction, useReorderQuickActions,
  useCreateChatSession, useSendChatMessage,
  getListChatSessionsQueryKey, getGetRecentChatsQueryKey,
} from "@workspace/api-client-react";
import type { QuickAction } from "@workspace/api-client-react";
import { useQueryClient } from "@tanstack/react-query";
import { useLocation } from "wouter";

const COLORS = ["cyan", "violet", "emerald", "amber", "rose", "blue", "fuchsia", "teal"] as const;
const COLOR_MAP: Record<string, string> = {
  cyan:    "bg-cyan-500/12 border-cyan-500/25 hover:bg-cyan-500/20 hover:border-cyan-500/40 text-cyan-300",
  violet:  "bg-violet-500/12 border-violet-500/25 hover:bg-violet-500/20 hover:border-violet-500/40 text-violet-300",
  emerald: "bg-emerald-500/12 border-emerald-500/25 hover:bg-emerald-500/20 hover:border-emerald-500/40 text-emerald-300",
  amber:   "bg-amber-500/12 border-amber-500/25 hover:bg-amber-500/20 hover:border-amber-500/40 text-amber-300",
  rose:    "bg-rose-500/12 border-rose-500/25 hover:bg-rose-500/20 hover:border-rose-500/40 text-rose-300",
  blue:    "bg-blue-500/12 border-blue-500/25 hover:bg-blue-500/20 hover:border-blue-500/40 text-blue-300",
  fuchsia: "bg-fuchsia-500/12 border-fuchsia-500/25 hover:bg-fuchsia-500/20 hover:border-fuchsia-500/40 text-fuchsia-300",
  teal:    "bg-teal-500/12 border-teal-500/25 hover:bg-teal-500/20 hover:border-teal-500/40 text-teal-300",
};

const PRESETS = [
  { label: "Clean Downloads", command: "Delete files in my Downloads folder older than 30 days", color: "amber" },
  { label: "Daily Briefing", command: "Give me a summary of my notes, any upcoming scheduled tasks, and what I should focus on today", color: "sky" as unknown as "blue" },
  { label: "Org by Type", command: "Organize my Downloads folder by file type into subfolders (Images, Documents, Videos, Archives)", color: "emerald" },
  { label: "Summarize Notes", command: "Summarize all my knowledge base notes into a concise overview", color: "violet" },
  { label: "Find Duplicates", command: "Scan my allowed paths and list any duplicate files", color: "rose" },
  { label: "Recent Activity", command: "Show me a summary of everything AXIOM has done in the last 7 days", color: "teal" },
] as const;

function ActionButton({ action, onEdit, onDelete, onRun, isRunning }: {
  action: QuickAction;
  onEdit: (a: QuickAction) => void;
  onDelete: (id: number) => void;
  onRun: (a: QuickAction) => void;
  isRunning: boolean;
}) {
  const colorClass = COLOR_MAP[action.color || "cyan"] || COLOR_MAP.cyan;

  return (
    <Reorder.Item value={action} id={String(action.id)} className="relative group" data-testid={`quick-action-${action.id}`}>
      <div className="absolute left-1.5 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity cursor-grab z-10">
        <GripVertical className="w-3 h-3 text-muted-foreground/50" />
      </div>
      <motion.button
        className={cn(
          "w-full h-20 rounded-xl border transition-all duration-200 flex flex-col items-center justify-center gap-1.5 px-3 relative",
          colorClass,
          isRunning && "opacity-60 pointer-events-none"
        )}
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.97 }}
        onClick={() => onRun(action)}
      >
        {isRunning && <Loader2 className="w-4 h-4 animate-spin absolute top-2 right-2 opacity-60" />}
        <Zap className="w-4 h-4 shrink-0" />
        <span className="text-xs font-medium text-center leading-tight line-clamp-2">{action.label}</span>
      </motion.button>
      <div className="absolute top-1 right-1 flex gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity z-10">
        <button
          className="w-5 h-5 flex items-center justify-center rounded bg-black/50 hover:bg-black/70 transition-colors"
          onClick={e => { e.stopPropagation(); onEdit(action); }}
          data-testid={`button-edit-action-${action.id}`}
        >
          <Edit2 className="w-2.5 h-2.5 text-white/70" />
        </button>
        <button
          className="w-5 h-5 flex items-center justify-center rounded bg-black/50 hover:bg-red-500/60 transition-colors"
          onClick={e => { e.stopPropagation(); onDelete(action.id); }}
          data-testid={`button-delete-action-${action.id}`}
        >
          <Trash2 className="w-2.5 h-2.5 text-white/70" />
        </button>
      </div>
    </Reorder.Item>
  );
}

export default function QuickActions() {
  const [showEdit, setShowEdit] = useState(false);
  const [editingAction, setEditingAction] = useState<QuickAction | null>(null);
  const [label, setLabel] = useState("");
  const [command, setCommand] = useState("");
  const [color, setColor] = useState<string>("cyan");
  const [runningId, setRunningId] = useState<number | null>(null);
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [, setLocation] = useLocation();

  const { data: actions = [], isLoading } = useListQuickActions({ query: { queryKey: getListQuickActionsQueryKey() } });

  const createAction = useCreateQuickAction();
  const updateAction = useUpdateQuickAction();
  const deleteAction = useDeleteQuickAction();
  const reorderActions = useReorderQuickActions();
  const createSession = useCreateChatSession();
  const sendMessage = useSendChatMessage();

  const invalidate = () => queryClient.invalidateQueries({ queryKey: getListQuickActionsQueryKey() });

  const openCreate = (preset?: { label: string; command: string; color: string }) => {
    setEditingAction(null);
    setLabel(preset?.label ?? "");
    setCommand(preset?.command ?? "");
    setColor(preset?.color ?? "cyan");
    setShowEdit(true);
  };

  const openEdit = (a: QuickAction) => {
    setEditingAction(a);
    setLabel(a.label); setCommand(a.command); setColor(a.color || "cyan");
    setShowEdit(true);
  };

  const handleSave = () => {
    if (!label.trim() || !command.trim()) return;
    if (editingAction) {
      updateAction.mutate({ id: editingAction.id, data: { label, command, color } }, {
        onSuccess: () => { invalidate(); setShowEdit(false); },
      });
    } else {
      createAction.mutate({ data: { label, command, color } }, {
        onSuccess: () => { invalidate(); setShowEdit(false); },
      });
    }
  };

  const handleDelete = (id: number) => {
    deleteAction.mutate({ id }, { onSuccess: () => invalidate() });
  };

  const handleReorder = useCallback((newOrder: QuickAction[]) => {
    reorderActions.mutate(
      { data: { ids: newOrder.map(a => a.id) } },
      { onSuccess: () => invalidate() }
    );
  }, [reorderActions]);

  const handleRun = useCallback((action: QuickAction) => {
    setRunningId(action.id);
    createSession.mutate({ data: { title: action.label } }, {
      onSuccess: (session) => {
        queryClient.invalidateQueries({ queryKey: getListChatSessionsQueryKey() });
        sendMessage.mutate({ id: session.id, data: { content: action.command } }, {
          onSuccess: () => {
            setRunningId(null);
            queryClient.invalidateQueries({ queryKey: getGetRecentChatsQueryKey() });
            toast({ title: `"${action.label}" sent to AXIOM` });
            setLocation("/chat");
          },
          onError: () => {
            setRunningId(null);
            toast({ title: "Action failed", variant: "destructive" });
          },
        });
      },
      onError: () => {
        setRunningId(null);
        toast({ title: "Failed to create session", variant: "destructive" });
      },
    });
  }, [createSession, sendMessage, queryClient, toast, setLocation]);

  return (
    <div className="flex flex-col h-full">
      <div className="px-6 py-4 border-b border-white/[0.07] flex items-center justify-between">
        <div>
          <h1 className="text-base font-semibold flex items-center gap-2">
            <Zap className="w-4 h-4 text-yellow-400" />
            Quick Actions
          </h1>
          <p className="text-xs text-muted-foreground mt-0.5">One-click AI commands · Drag to reorder</p>
        </div>
        <Button size="sm" className="btn-action h-7 text-xs" onClick={() => openCreate()} data-testid="button-add-action">
          <Plus className="w-3 h-3 mr-1" />Add Action
        </Button>
      </div>

      <div className="flex-1 overflow-auto p-6">
        {isLoading ? (
          <div className="grid grid-cols-3 gap-3">
            {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-20 rounded-xl bg-white/5" />)}
          </div>
        ) : actions.length === 0 ? (
          <div className="space-y-6">
            <div className="flex flex-col items-center gap-3 py-6">
              <div className="w-14 h-14 rounded-2xl bg-yellow-500/10 border border-yellow-400/20 flex items-center justify-center">
                <Zap className="w-7 h-7 text-yellow-400" />
              </div>
              <div className="text-center">
                <p className="text-sm font-medium">No quick actions yet</p>
                <p className="text-xs text-muted-foreground mt-1">Create one-click buttons for your most-used AI commands</p>
              </div>
              <Button size="sm" className="btn-action" onClick={() => openCreate()} data-testid="button-add-action-empty">
                <Plus className="w-3.5 h-3.5 mr-1.5" />Create Action
              </Button>
            </div>

            {/* Suggested presets */}
            <div>
              <div className="flex items-center gap-2 mb-3">
                <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Suggested presets</p>
              </div>
              <div className="grid grid-cols-3 gap-3">
                {PRESETS.map((preset) => {
                  const colorClass = COLOR_MAP[preset.color] || COLOR_MAP.cyan;
                  return (
                    <motion.button
                      key={preset.label}
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.97 }}
                      className={cn(
                        "h-20 rounded-xl border transition-all duration-200 flex flex-col items-center justify-center gap-1.5 px-3 relative",
                        colorClass
                      )}
                      onClick={() => openCreate(preset)}
                    >
                      <Plus className="w-3.5 h-3.5 shrink-0 opacity-60" />
                      <span className="text-xs font-medium text-center leading-tight line-clamp-2">{preset.label}</span>
                    </motion.button>
                  );
                })}
              </div>
              <p className="text-[10px] text-muted-foreground/50 mt-2 text-center">Click any preset to add it as a quick action</p>
            </div>
          </div>
        ) : (
          <Reorder.Group axis="y" values={actions} onReorder={handleReorder} className="grid grid-cols-3 gap-3" as="div">
            <AnimatePresence>
              {actions.map(action => (
                <ActionButton
                  key={action.id}
                  action={action}
                  onEdit={openEdit}
                  onDelete={handleDelete}
                  onRun={handleRun}
                  isRunning={runningId === action.id}
                />
              ))}
            </AnimatePresence>
          </Reorder.Group>
        )}
      </div>

      <Dialog open={showEdit} onOpenChange={setShowEdit}>
        <DialogContent className="glass-panel border-white/[0.08] bg-card/90 max-w-sm">
          <DialogHeader>
            <DialogTitle className="text-sm font-semibold">
              {editingAction ? "Edit Action" : "New Quick Action"}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">Button Label</Label>
              <Input value={label} onChange={e => setLabel(e.target.value)} placeholder="Clean Downloads" className="glass-input h-8 text-sm" data-testid="input-action-label" />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">Command</Label>
              <Textarea value={command} onChange={e => setCommand(e.target.value)} placeholder="Delete files in my Downloads folder older than 30 days" className="glass-input text-xs min-h-[70px] resize-none" data-testid="textarea-action-command" />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">Color</Label>
              <div className="flex flex-wrap gap-2">
                {COLORS.map(c => (
                  <button
                    key={c}
                    onClick={() => setColor(c)}
                    className={cn(
                      "w-7 h-7 rounded-lg border transition-all",
                      COLOR_MAP[c],
                      color === c ? "ring-2 ring-white/40 scale-110" : ""
                    )}
                    data-testid={`color-option-${c}`}
                  />
                ))}
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" size="sm" className="text-xs" onClick={() => setShowEdit(false)}>Cancel</Button>
            <Button
              size="sm"
              className="text-xs btn-action"
              onClick={handleSave}
              disabled={!label.trim() || !command.trim() || createAction.isPending || updateAction.isPending}
              data-testid="button-save-action"
            >
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
