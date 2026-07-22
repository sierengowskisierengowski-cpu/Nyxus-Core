import { useState, useRef, useEffect, useCallback } from "react";
import { electron } from "@/lib/electron-api";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Plus, Trash2, MessageSquare, Bot, User, Loader2, AlertCircle, CheckCircle2, XCircle, FileText, ChevronDown, Mic, MicOff, Search, Cloud, Cpu } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { useToast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";
import {
  useListChatSessions, getListChatSessionsQueryKey,
  useGetChatSession, getGetChatSessionQueryKey,
  useCreateChatSession, useDeleteChatSession, useSendChatMessage,
  getGetRecentChatsQueryKey, useExecuteFileOp, usePreviewFileOp,
  useGetSettings, getGetSettingsQueryKey,
  useGetAiStatus, getGetAiStatusQueryKey,
} from "@workspace/api-client-react";
import type { ChatMessage, AiAction, FileOpExecuteInputOperation, FileOpPreview } from "@workspace/api-client-react";
import { useQueryClient } from "@tanstack/react-query";

interface FileOpPayload {
  path?: string;
  operation?: FileOpExecuteInputOperation;
  criteria?: string;
  destination?: string;
}

type ActionStep = "idle" | "previewing" | "preview_ready" | "executing" | "done";

function ActionCard({ action }: { action: AiAction }) {
  const [dismissed, setDismissed] = useState(false);
  const [step, setStep] = useState<ActionStep>("idle");
  const [preview, setPreview] = useState<FileOpPreview | null>(null);
  const [showFiles, setShowFiles] = useState(false);
  const [result, setResult] = useState<{ success: boolean; summary: string } | null>(null);
  const { toast } = useToast();
  const previewFileOp = usePreviewFileOp();
  const executeFileOp = useExecuteFileOp();

  const payload: FileOpPayload = (() => {
    if (!action.payload) return {};
    try { return JSON.parse(action.payload) as FileOpPayload; } catch { return {}; }
  })();

  const isFileOp = !!(payload.path && payload.operation);
  if (dismissed) return null;

  const handlePreview = () => {
    if (!isFileOp || !payload.path || !payload.operation) {
      setResult({ success: true, summary: "Action acknowledged" });
      setStep("done");
      return;
    }
    setStep("previewing");
    previewFileOp.mutate(
      { data: { path: payload.path, operation: payload.operation, criteria: payload.criteria, destination: payload.destination } },
      {
        onSuccess: (r) => { setPreview(r); setStep("preview_ready"); },
        onError: () => {
          toast({ title: "Preview failed", description: "Could not list affected files — check allowed paths in Settings.", variant: "destructive" });
          setStep("idle");
        },
      }
    );
  };

  const handleExecute = () => {
    if (!payload.path || !payload.operation) return;
    setStep("executing");
    executeFileOp.mutate(
      { data: { path: payload.path, operation: payload.operation, criteria: payload.criteria, destination: payload.destination, confirmed: true } },
      {
        onSuccess: (r) => {
          setResult({ success: true, summary: r.summary });
          setStep("done");
          toast({ title: "Action completed", description: r.summary });
        },
        onError: () => {
          setResult({ success: false, summary: "Operation failed — check allowed paths in Settings." });
          setStep("done");
          toast({ title: "Action failed", variant: "destructive" });
        },
      }
    );
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8, scale: 0.96 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      className="mt-3 rounded-xl border border-amber-500/25 bg-amber-500/5 p-3"
    >
      <div className="flex items-start gap-2">
        <AlertCircle className="w-4 h-4 text-amber-400 mt-0.5 shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-amber-300 mb-1">Action Required</p>
          <p className="text-xs text-muted-foreground">{action.description}</p>
          {isFileOp && payload.path && (
            <p className="text-[10px] text-muted-foreground/60 mt-0.5 font-mono">{payload.path}</p>
          )}
        </div>
      </div>

      <AnimatePresence>
        {preview && step !== "done" && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="mt-3 rounded-lg border border-white/10 bg-white/5 overflow-hidden"
          >
            <div className="flex items-center justify-between px-3 py-2 cursor-pointer hover:bg-white/5" onClick={() => setShowFiles(v => !v)}>
              <div className="flex items-center gap-1.5">
                <FileText className="w-3 h-3 text-amber-400" />
                <span className="text-xs font-medium text-amber-300">{preview.summary}</span>
              </div>
              <ChevronDown className={cn("w-3 h-3 text-muted-foreground transition-transform", showFiles && "rotate-180")} />
            </div>
            {showFiles && preview.affectedFiles && preview.affectedFiles.length > 0 && (
              <div className="border-t border-white/10 max-h-36 overflow-y-auto">
                {preview.affectedFiles.slice(0, 30).map((f, i) => (
                  <div key={i} className="flex items-center justify-between px-3 py-1 hover:bg-white/5">
                    <span className="text-[10px] text-muted-foreground font-mono truncate flex-1">{f.name}</span>
                    <span className="text-[10px] text-muted-foreground/50 ml-2 shrink-0">
                      {f.size > 1e6 ? `${(f.size / 1e6).toFixed(1)}MB` : `${Math.round(f.size / 1024)}KB`}
                    </span>
                  </div>
                ))}
                {(preview.affectedFiles?.length ?? 0) > 30 && (
                  <p className="text-[10px] text-muted-foreground/50 px-3 py-1">+{(preview.affectedFiles?.length ?? 0) - 30} more</p>
                )}
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {step !== "done" && (
        <div className="flex gap-2 mt-3">
          {step === "idle" && (
            <>
              <Button size="sm" className="h-7 text-xs btn-amber" onClick={handlePreview} data-testid="button-preview-action">
                <FileText className="w-3 h-3 mr-1" />Preview
              </Button>
              <Button size="sm" variant="ghost" className="h-7 text-xs text-muted-foreground hover:text-foreground" onClick={() => setDismissed(true)} data-testid="button-dismiss-action">
                <XCircle className="w-3 h-3 mr-1" />Cancel
              </Button>
            </>
          )}
          {step === "previewing" && (
            <Button size="sm" disabled className="h-7 text-xs btn-amber opacity-60">
              <Loader2 className="w-3 h-3 mr-1 animate-spin" />Loading preview…
            </Button>
          )}
          {step === "preview_ready" && (
            <>
              <Button size="sm" className="h-7 text-xs btn-emerald" onClick={handleExecute} data-testid="button-confirm-action">
                <CheckCircle2 className="w-3 h-3 mr-1" />Execute
              </Button>
              <Button size="sm" variant="ghost" className="h-7 text-xs text-muted-foreground hover:text-foreground" onClick={() => setDismissed(true)} data-testid="button-dismiss-action">
                <XCircle className="w-3 h-3 mr-1" />Cancel
              </Button>
            </>
          )}
          {step === "executing" && (
            <Button size="sm" disabled className="h-7 text-xs btn-emerald opacity-60">
              <Loader2 className="w-3 h-3 mr-1 animate-spin" />Executing…
            </Button>
          )}
        </div>
      )}

      {step === "done" && result && (
        <div className={cn("flex items-center gap-1 mt-3 text-xs", result.success ? "text-emerald-400" : "text-destructive")}>
          {result.success ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
          {result.summary}
        </div>
      )}
    </motion.div>
  );
}

function MessageBubble({ msg }: { msg: ChatMessage }) {
  const isUser = msg.role === "user";

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className={cn("flex gap-3 mb-4", isUser ? "flex-row-reverse" : "flex-row")}
    >
      <div className={cn(
        "w-7 h-7 rounded-full flex items-center justify-center shrink-0 mt-0.5",
        isUser ? "bg-indigo-500/20 border border-indigo-400/30" : "bg-sky-500/10 border border-sky-400/20"
      )}>
        {isUser
          ? <User className="w-3.5 h-3.5 text-indigo-400" />
          : <Bot className="w-3.5 h-3.5 text-sky-400" />
        }
      </div>

      <div className={cn("max-w-[75%] min-w-0", isUser ? "items-end" : "items-start")}>
        <div className={cn(
          "px-4 py-2.5 rounded-2xl text-sm leading-relaxed",
          isUser
            ? "bg-indigo-500/12 border border-indigo-400/20 text-foreground rounded-tr-sm"
            : "glass-card text-foreground rounded-tl-sm"
        )}>
          <p className="whitespace-pre-wrap break-words">{msg.content}</p>
        </div>

        {msg.actionType && msg.actionData && (
          <ActionCard action={{
            type: msg.actionType as AiAction["type"],
            description: (() => {
              try { return (JSON.parse(msg.actionData) as { description?: string }).description || "File operation pending"; } catch { return "File operation pending"; }
            })(),
            payload: msg.actionData,
            requiresConfirmation: true,
          }} />
        )}

        <p className="text-[10px] text-muted-foreground/50 mt-1 px-1">
          {new Date(msg.createdAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
        </p>
      </div>
    </motion.div>
  );
}

export default function Chat() {
  const [activeSessionId, setActiveSessionId] = useState<number | null>(null);
  const [input, setInput] = useState("");
  const [sessionSearch, setSessionSearch] = useState("");
  const [showSearch, setShowSearch] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const recognitionRef = useRef<any>(null);
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [isListening, setIsListening] = useState(false);

  const { data: sessions = [], isLoading: sessionsLoading } = useListChatSessions({
    query: { queryKey: getListChatSessionsQueryKey() },
  });
  const { data: activeSession, isLoading: messagesLoading } = useGetChatSession(
    activeSessionId ?? 0,
    { query: { enabled: !!activeSessionId, queryKey: getGetChatSessionQueryKey(activeSessionId ?? 0) } }
  );
  const { data: settings } = useGetSettings({ query: { queryKey: getGetSettingsQueryKey() } });
  const { data: aiStatus } = useGetAiStatus({ query: { queryKey: getGetAiStatusQueryKey(), refetchInterval: 15000 } });

  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");

  const createSession = useCreateChatSession();
  const deleteSession = useDeleteChatSession();
  const sendMessage = useSendChatMessage();

  useEffect(() => {
    if (!activeSessionId && sessions.length > 0) setActiveSessionId(sessions[0].id);
  }, [sessions, activeSessionId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [activeSession?.messages?.length]);

  const handleNewSession = useCallback(async () => {
    createSession.mutate(
      { data: { title: "New Chat" } },
      {
        onSuccess: (session) => {
          queryClient.invalidateQueries({ queryKey: getListChatSessionsQueryKey() });
          queryClient.invalidateQueries({ queryKey: getGetRecentChatsQueryKey() });
          setActiveSessionId(session.id);
        },
      }
    );
  }, [createSession, queryClient]);

  const handleDeleteSession = useCallback((id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    deleteSession.mutate({ id }, {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: getListChatSessionsQueryKey() });
        if (activeSessionId === id) {
          const remaining = sessions.filter(s => s.id !== id);
          setActiveSessionId(remaining[0]?.id ?? null);
        }
      },
    });
  }, [deleteSession, queryClient, activeSessionId, sessions]);

  const handleSend = useCallback(async () => {
    if (!input.trim() || isStreaming) return;
    if (!activeSessionId) {
      createSession.mutate(
        { data: { title: input.slice(0, 60) } },
        {
          onSuccess: (session) => {
            queryClient.invalidateQueries({ queryKey: getListChatSessionsQueryKey() });
            setActiveSessionId(session.id);
            setTimeout(() => doSend(session.id), 100);
          },
        }
      );
      return;
    }
    doSend(activeSessionId);
  }, [input, isStreaming, activeSessionId, createSession, queryClient]);

  const doSend = useCallback(async (sessionId: number) => {
    const content = input.trim();
    setInput("");
    setIsStreaming(true);
    setStreamingContent("");

    const apiBase = window.location.protocol === "file:" ? "http://127.0.0.1:8080" : "";
    const sseHeaders: Record<string, string> = { "Content-Type": "application/json" };
    if (window.location.protocol === "file:") {
      const tok = await electron.getLocalToken();
      if (tok) sseHeaders["Authorization"] = `Bearer ${tok}`;
    }
    fetch(`${apiBase}/api/chat/sessions/${sessionId}/messages/stream`, {
      method: "POST",
      headers: sseHeaders,
      body: JSON.stringify({ content }),
    }).then(async (response) => {
      if (!response.ok || !response.body) {
        setIsStreaming(false);
        setStreamingContent("");
        toast({ title: "Failed to send message", variant: "destructive" });
        setInput(content);
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const parts = buffer.split("\n\n");
          buffer = parts.pop() ?? "";
          for (const part of parts) {
            const lines = part.split("\n");
            let eventType = "";
            let eventData = "";
            for (const line of lines) {
              if (line.startsWith("event: ")) eventType = line.slice(7).trim();
              else if (line.startsWith("data: ")) eventData = line.slice(6);
            }
            if (!eventData) continue;
            try {
              const data = JSON.parse(eventData) as Record<string, unknown>;
              if (eventType === "chunk" && typeof data.content === "string") {
                setStreamingContent(prev => prev + data.content);
              }
            } catch {}
          }
        }
      } catch {}

      setIsStreaming(false);
      setStreamingContent("");
      queryClient.invalidateQueries({ queryKey: getGetChatSessionQueryKey(sessionId) });
      queryClient.invalidateQueries({ queryKey: getListChatSessionsQueryKey() });
      queryClient.invalidateQueries({ queryKey: getGetRecentChatsQueryKey() });
    }).catch(() => {
      setIsStreaming(false);
      setStreamingContent("");
      toast({ title: "Failed to send message", variant: "destructive" });
      setInput(content);
    });
  }, [input, queryClient, toast]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleVoiceInput = useCallback(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const w = window as any;
    const SpeechRecognitionCtor = w.SpeechRecognition ?? w.webkitSpeechRecognition;
    if (!SpeechRecognitionCtor) {
      toast({ title: "Voice input not supported", description: "Your browser does not support speech recognition", variant: "destructive" });
      return;
    }
    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
      return;
    }
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const recognition: any = new SpeechRecognitionCtor();
    recognition.lang = "en-US";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognitionRef.current = recognition;
    recognition.onstart = () => setIsListening(true);
    recognition.onend = () => setIsListening(false);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    recognition.onerror = (e: any) => {
      setIsListening(false);
      if (e.error !== "aborted") toast({ title: "Voice input error", description: e.error, variant: "destructive" });
    };
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    recognition.onresult = (e: any) => {
      const transcript = e.results[0][0].transcript as string;
      setInput(prev => prev ? `${prev} ${transcript}` : transcript);
      textareaRef.current?.focus();
    };
    recognition.start();
  }, [isListening, toast]);

  const messages = activeSession?.messages ?? [];
  const filteredSessions = sessions.filter(s =>
    !sessionSearch || s.title.toLowerCase().includes(sessionSearch.toLowerCase())
  );

  const isCloud = settings?.aiMode === "cloud";
  const modelName = settings?.aiModel ?? "…";
  const aiOnline = isCloud ? true : aiStatus?.ollamaAvailable;

  return (
    <div className="flex h-full">
      {/* Session sidebar */}
      <div className="w-52 shrink-0 border-r border-white/[0.07] flex flex-col">
        <div className="p-3 border-b border-white/[0.07] flex items-center justify-between">
          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Sessions</span>
          <div className="flex items-center gap-1">
            <Button
              size="icon"
              variant="ghost"
              className="w-6 h-6 hover:bg-white/10 text-muted-foreground hover:text-foreground"
              onClick={() => setShowSearch(v => !v)}
              title="Search sessions"
            >
              <Search className="w-3 h-3" />
            </Button>
            <Button
              size="icon"
              variant="ghost"
              className="w-6 h-6 hover:bg-white/10 text-muted-foreground hover:text-foreground"
              onClick={handleNewSession}
              disabled={createSession.isPending}
              data-testid="button-new-session"
              title="New chat"
            >
              <Plus className="w-3.5 h-3.5" />
            </Button>
          </div>
        </div>

        {showSearch && (
          <div className="px-2 py-1.5 border-b border-white/[0.07]">
            <Input
              value={sessionSearch}
              onChange={e => setSessionSearch(e.target.value)}
              placeholder="Search sessions..."
              className="glass-input h-7 text-xs"
              autoFocus
            />
          </div>
        )}

        <ScrollArea className="flex-1">
          <div className="p-2 space-y-1">
            {sessionsLoading ? (
              Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-9 w-full rounded-lg bg-white/5" />
              ))
            ) : filteredSessions.length === 0 ? (
              <p className="text-xs text-muted-foreground text-center py-8 px-3">
                {sessionSearch ? "No sessions match." : "No sessions yet. Start a new chat."}
              </p>
            ) : (
              filteredSessions.map((session) => (
                <motion.div
                  key={session.id}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  className={cn(
                    "group flex items-center gap-2 px-2 py-2 rounded-lg cursor-pointer transition-all duration-150 border",
                    activeSessionId === session.id
                      ? "bg-indigo-500/12 border-indigo-500/25 text-indigo-200"
                      : "border-transparent hover:bg-white/5 hover:border-white/10"
                  )}
                  onClick={() => setActiveSessionId(session.id)}
                  data-testid={`session-item-${session.id}`}
                >
                  <MessageSquare className={cn("w-3.5 h-3.5 shrink-0", activeSessionId === session.id ? "text-indigo-400" : "text-muted-foreground")} />
                  <span className="text-xs flex-1 truncate">{session.title}</span>
                  <button
                    className="opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
                    onClick={(e) => handleDeleteSession(session.id, e)}
                    data-testid={`button-delete-session-${session.id}`}
                  >
                    <Trash2 className="w-3 h-3 text-muted-foreground hover:text-destructive transition-colors" />
                  </button>
                </motion.div>
              ))
            )}
          </div>
        </ScrollArea>
      </div>

      {/* Chat area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <div className="px-4 py-3 border-b border-white/[0.07] flex items-center gap-2">
          <Bot className="w-4 h-4 text-sky-400 shrink-0" />
          <span className="text-sm font-medium flex-1 truncate">
            {activeSession?.title || "Select a session"}
          </span>
          <div className="flex items-center gap-2 ml-auto shrink-0">
            {isStreaming && (
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <Loader2 className="w-3 h-3 animate-spin" />
                {streamingContent ? "Responding…" : "Thinking…"}
              </div>
            )}
            {settings && (
              <div className={cn(
                "flex items-center gap-1.5 text-[10px] px-2 py-0.5 rounded-full border",
                isCloud
                  ? "bg-sky-500/10 border-sky-500/25 text-sky-300"
                  : aiOnline
                    ? "bg-emerald-500/10 border-emerald-500/25 text-emerald-300"
                    : "bg-red-500/10 border-red-500/25 text-red-300"
              )}>
                {isCloud ? <Cloud className="w-2.5 h-2.5" /> : <Cpu className="w-2.5 h-2.5" />}
                <span className="font-mono truncate max-w-[80px]">{modelName}</span>
                <span className={cn("w-1.5 h-1.5 rounded-full", aiOnline ? "bg-emerald-400" : "bg-red-400")} />
              </div>
            )}
          </div>
        </div>

        {/* Messages */}
        <ScrollArea className="flex-1 px-4 py-4">
          {!activeSessionId ? (
            <div className="flex flex-col items-center justify-center h-full min-h-[300px] gap-4">
              <div className="w-16 h-16 rounded-2xl bg-sky-500/10 border border-sky-400/20 flex items-center justify-center">
                <Bot className="w-8 h-8 text-sky-400" />
              </div>
              <div className="text-center">
                <p className="text-sm font-medium text-foreground">No active session</p>
                <p className="text-xs text-muted-foreground mt-1">Create a new chat to get started</p>
              </div>
              <Button
                size="sm"
                onClick={handleNewSession}
                className="btn-action"
                data-testid="button-start-chat"
              >
                <Plus className="w-3.5 h-3.5 mr-1.5" />
                Start Chat
              </Button>
            </div>
          ) : messagesLoading ? (
            <div className="space-y-4">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className={cn("flex gap-3", i % 2 === 0 ? "" : "flex-row-reverse")}>
                  <Skeleton className="w-7 h-7 rounded-full bg-white/5 shrink-0" />
                  <Skeleton className={cn("h-16 rounded-2xl bg-white/5", i % 2 === 0 ? "w-2/3" : "w-1/2")} />
                </div>
              ))}
            </div>
          ) : (
            <>
              {messages.map((msg) => (
                <MessageBubble key={msg.id} msg={msg} />
              ))}
              {isStreaming && streamingContent && (
                <motion.div
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex gap-3 mb-4"
                >
                  <div className="w-7 h-7 rounded-full bg-sky-500/10 border border-sky-400/20 flex items-center justify-center shrink-0 mt-0.5">
                    <Bot className="w-3.5 h-3.5 text-sky-400" />
                  </div>
                  <div className="glass-card px-4 py-2.5 rounded-2xl rounded-tl-sm max-w-[75%]">
                    <p className="text-sm leading-relaxed whitespace-pre-wrap">{streamingContent}</p>
                    <span className="inline-block w-1.5 h-4 bg-sky-400 ml-0.5 animate-pulse rounded-sm" />
                  </div>
                </motion.div>
              )}
              {isStreaming && !streamingContent && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex gap-3 mb-4">
                  <div className="w-7 h-7 rounded-full bg-sky-500/10 border border-sky-400/20 flex items-center justify-center shrink-0">
                    <Loader2 className="w-3.5 h-3.5 text-sky-400 animate-spin" />
                  </div>
                  <div className="glass-card px-4 py-3 rounded-2xl rounded-tl-sm">
                    <div className="flex gap-1">
                      {[0, 1, 2].map(i => (
                        <span key={i} className="w-1.5 h-1.5 bg-sky-400/60 rounded-full animate-bounce" style={{ animationDelay: `${i * 0.15}s` }} />
                      ))}
                    </div>
                  </div>
                </motion.div>
              )}
              <div ref={bottomRef} />
            </>
          )}
        </ScrollArea>

        {/* Input */}
        <div className="px-4 py-3 border-t border-white/[0.07]">
          <div className="flex gap-2 items-end">
            <Textarea
              ref={textareaRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask AXIOM to organize files, run a task, or answer a question..."
              className="glass-input flex-1 resize-none min-h-[40px] max-h-32 text-sm py-2.5 leading-relaxed"
              rows={1}
              data-testid="input-chat-message"
            />
            <Button
              size="icon"
              variant="ghost"
              className={cn(
                "h-10 w-10 shrink-0 rounded-xl border transition-all duration-200",
                isListening
                  ? "bg-rose-500/20 border-rose-400/40 text-rose-300"
                  : "border-white/10 text-muted-foreground hover:border-white/20 hover:text-foreground"
              )}
              onClick={handleVoiceInput}
              title={isListening ? "Stop listening" : "Voice input"}
              data-testid="button-voice-input"
            >
              {isListening ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
            </Button>
            <Button
              size="icon"
              className={cn(
                "h-10 w-10 shrink-0 rounded-xl transition-all duration-200",
                input.trim() && !isStreaming
                  ? "bg-indigo-500/25 border border-indigo-400/40 text-indigo-300 hover:bg-indigo-500/35"
                  : "bg-white/5 border border-white/10 text-muted-foreground cursor-not-allowed"
              )}
              onClick={handleSend}
              disabled={!input.trim() || isStreaming}
              data-testid="button-send-message"
            >
              {isStreaming ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            </Button>
          </div>
          <p className="text-[10px] text-muted-foreground/40 mt-1.5 px-0.5">
            Enter to send · Shift+Enter for new line · Mic for voice
          </p>
        </div>
      </div>
    </div>
  );
}
