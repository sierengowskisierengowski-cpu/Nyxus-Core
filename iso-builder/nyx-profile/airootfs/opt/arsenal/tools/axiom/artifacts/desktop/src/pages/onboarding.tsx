import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Zap, Keyboard, Shield, Brain, Cloud, Cpu, ArrowRight, CheckCircle2, Loader2, Plus, Trash2, FolderOpen } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";
import { electron, isElectron } from "@/lib/electron-api";
import {
  useUpdateSettings,
  useCreateKnowledgeNote,
  useAddAllowedPath,
  getGetSettingsQueryKey,
  getListKnowledgeNotesQueryKey,
  getGetAllowedPathsQueryKey,
} from "@workspace/api-client-react";
import { useQueryClient } from "@tanstack/react-query";
import { useLocation } from "wouter";

const STEPS = [
  { id: "welcome", title: "Welcome to AXIOM", icon: Zap },
  { id: "hotkey", title: "Global Hotkey", icon: Keyboard },
  { id: "paths", title: "Allowed Paths", icon: Shield },
  { id: "ai", title: "AI Provider", icon: Brain },
  { id: "knowledge", title: "Knowledge Base", icon: Brain },
  { id: "done", title: "Ready", icon: CheckCircle2 },
] as const;

type StepId = typeof STEPS[number]["id"];

const pageVariants = {
  enter: { opacity: 0, x: 40, scale: 0.97 },
  center: { opacity: 1, x: 0, scale: 1 },
  exit: { opacity: 0, x: -40, scale: 0.97 },
};

export default function Onboarding() {
  const [step, setStep] = useState<StepId>("welcome");
  const [hotkey, setHotkey] = useState("CommandOrControl+Shift+Space");
  const [paths, setPaths] = useState<string[]>([""]);
  const [aiMode, setAiMode] = useState<"local" | "cloud">("cloud");
  const [apiKey, setApiKey] = useState("");
  const [ollamaUrl, setOllamaUrl] = useState("http://localhost:11434");
  const [noteTitle, setNoteTitle] = useState("My System Setup");
  const [noteContent, setNoteContent] = useState("My home directory is at /Users/me. My Downloads folder is at /Users/me/Downloads. My Desktop is at /Users/me/Desktop.");
  const [completing, setCompleting] = useState(false);

  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [, setLocation] = useLocation();

  const updateSettings = useUpdateSettings();
  const createNote = useCreateKnowledgeNote();
  const addPath = useAddAllowedPath();

  const stepIndex = STEPS.findIndex(s => s.id === step);

  const next = () => {
    const nextStep = STEPS[stepIndex + 1];
    if (nextStep) setStep(nextStep.id);
  };

  const handleComplete = async () => {
    setCompleting(true);
    try {
      const validPaths = paths.filter(p => p.trim());
      for (const p of validPaths) {
        try { await addPath.mutateAsync({ data: { path: p.trim() } }); } catch {}
      }
      if (noteTitle.trim() && noteContent.trim()) {
        try { await createNote.mutateAsync({ data: { title: noteTitle, content: noteContent, pinned: true } }); } catch {}
      }
      await updateSettings.mutateAsync({
        data: {
          hotkey,
          aiMode,
          cloudApiKey: apiKey || undefined,
          ollamaBaseUrl: ollamaUrl,
          onboardingCompleted: true,
        }
      });
      queryClient.invalidateQueries({ queryKey: getGetSettingsQueryKey() });
      queryClient.invalidateQueries({ queryKey: getListKnowledgeNotesQueryKey() });
      queryClient.invalidateQueries({ queryKey: getGetAllowedPathsQueryKey() });
      // Apply hotkey at OS level in Electron
      if (isElectron) {
        await electron.updateHotkey(hotkey);
      }
      setLocation("/chat");
    } catch {
      toast({ title: "Setup error", description: "Some settings could not be saved. You can configure them in Settings.", variant: "destructive" });
      setLocation("/chat");
    } finally {
      setCompleting(false);
    }
  };

  return (
    <div className="flex items-center justify-center h-full bg-transparent">
      <div className="w-full max-w-lg px-8 py-10">
        {/* Progress */}
        <div className="flex items-center justify-center gap-2 mb-10">
          {STEPS.map((s, i) => (
            <div
              key={s.id}
              className={cn(
                "h-1 rounded-full transition-all duration-300",
                i < stepIndex ? "bg-primary w-8" : i === stepIndex ? "bg-primary/70 w-10" : "bg-white/10 w-5"
              )}
            />
          ))}
        </div>

        <AnimatePresence mode="wait">
          <motion.div
            key={step}
            variants={pageVariants}
            initial="enter"
            animate="center"
            exit="exit"
            transition={{ duration: 0.3, ease: "easeInOut" }}
            className="space-y-6"
          >
            {/* Welcome */}
            {step === "welcome" && (
              <div className="text-center space-y-5">
                <motion.div
                  initial={{ scale: 0.8, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={{ delay: 0.1 }}
                  className="w-20 h-20 rounded-2xl bg-primary/15 border border-primary/25 flex items-center justify-center mx-auto shadow-[0_0_40px_rgba(0,210,220,0.15)]"
                >
                  <Zap className="w-10 h-10 text-primary" />
                </motion.div>
                <div>
                  <h1 className="text-2xl font-bold tracking-tight">Welcome to AXIOM</h1>
                  <p className="text-sm text-muted-foreground mt-2 leading-relaxed max-w-sm mx-auto">
                    Your personal AI command center. Let's get you set up in about two minutes.
                  </p>
                </div>
                <div className="grid grid-cols-2 gap-3 text-left">
                  {[
                    { icon: Brain, label: "AI-powered file management" },
                    { icon: Shield, label: "Sandboxed to approved paths" },
                    { icon: Cpu, label: "Runs locally on your GPU" },
                    { icon: CheckCircle2, label: "Full undo on all operations" },
                  ].map((f, i) => (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.2 + i * 0.07 }}
                      className="flex items-center gap-2.5 px-3 py-2.5 rounded-lg bg-white/5 border border-white/10"
                    >
                      <f.icon className="w-3.5 h-3.5 text-primary" />
                      <span className="text-xs text-muted-foreground">{f.label}</span>
                    </motion.div>
                  ))}
                </div>
              </div>
            )}

            {/* Hotkey */}
            {step === "hotkey" && (
              <div className="space-y-5">
                <div className="text-center">
                  <div className="w-12 h-12 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center mx-auto mb-3">
                    <Keyboard className="w-6 h-6 text-primary" />
                  </div>
                  <h2 className="text-lg font-semibold">Global Hotkey</h2>
                  <p className="text-sm text-muted-foreground mt-1.5">The keyboard shortcut to summon AXIOM from anywhere on your system.</p>
                </div>
                <div className="space-y-2">
                  <Label className="text-xs text-muted-foreground">Hotkey Combination</Label>
                  <Input
                    value={hotkey}
                    onChange={e => setHotkey(e.target.value)}
                    className="glass-input text-sm font-mono text-center"
                    data-testid="input-onboarding-hotkey"
                  />
                  <p className="text-xs text-muted-foreground">
                    Use <code className="text-primary">CommandOrControl</code> for Cmd on Mac / Ctrl on Windows/Linux
                  </p>
                </div>
              </div>
            )}

            {/* Paths */}
            {step === "paths" && (
              <div className="space-y-5">
                <div className="text-center">
                  <div className="w-12 h-12 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center mx-auto mb-3">
                    <Shield className="w-6 h-6 text-primary" />
                  </div>
                  <h2 className="text-lg font-semibold">Allowed Paths</h2>
                  <p className="text-sm text-muted-foreground mt-1.5">AXIOM will only operate on directories you explicitly approve here.</p>
                </div>
                <div className="space-y-2">
                  {paths.map((p, i) => (
                    <div key={i} className="flex gap-2">
                      <Input
                        value={p}
                        onChange={e => {
                          const next = [...paths];
                          next[i] = e.target.value;
                          setPaths(next);
                        }}
                        placeholder="/Users/me/Downloads"
                        className="glass-input text-sm font-mono flex-1"
                        data-testid={`input-path-${i}`}
                      />
                      {isElectron && (
                        <Button
                          size="icon"
                          variant="ghost"
                          className="w-8 h-8 border border-white/10 shrink-0"
                          title="Browse for folder"
                          onClick={async () => {
                            const result = await electron.openDirectoryDialog();
                            if (result) {
                              const next = [...paths];
                              next[i] = result;
                              setPaths(next);
                            }
                          }}
                        >
                          <FolderOpen className="w-3.5 h-3.5" />
                        </Button>
                      )}
                      {paths.length > 1 && (
                        <Button
                          size="icon"
                          variant="ghost"
                          className="w-8 h-8 hover:bg-destructive/10 shrink-0"
                          onClick={() => setPaths(paths.filter((_, j) => j !== i))}
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </Button>
                      )}
                    </div>
                  ))}
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-7 text-xs border border-white/10"
                    onClick={async () => {
                      if (isElectron) {
                        const result = await electron.openDirectoryDialog();
                        if (result) setPaths([...paths, result]);
                      } else {
                        setPaths([...paths, ""]);
                      }
                    }}
                    data-testid="button-add-onboarding-path"
                  >
                    <Plus className="w-3 h-3 mr-1" />
                    {isElectron ? "Browse for folder" : "Add another path"}
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground">You can add or remove paths later in Settings.</p>
              </div>
            )}

            {/* AI */}
            {step === "ai" && (
              <div className="space-y-5">
                <div className="text-center">
                  <div className="w-12 h-12 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center mx-auto mb-3">
                    <Brain className="w-6 h-6 text-primary" />
                  </div>
                  <h2 className="text-lg font-semibold">AI Provider</h2>
                  <p className="text-sm text-muted-foreground mt-1.5">Choose how AXIOM should think.</p>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    className={cn(
                      "p-4 rounded-xl border transition-all text-left space-y-2",
                      aiMode === "cloud"
                        ? "border-primary/40 bg-primary/10"
                        : "border-white/10 bg-white/5 hover:bg-white/10"
                    )}
                    onClick={() => setAiMode("cloud")}
                    data-testid="button-onboarding-cloud"
                  >
                    <Cloud className="w-5 h-5 text-primary" />
                    <p className="text-sm font-medium">Cloud</p>
                    <p className="text-xs text-muted-foreground">OpenAI GPT-4o, fast, powerful, requires API key</p>
                  </button>
                  <button
                    className={cn(
                      "p-4 rounded-xl border transition-all text-left space-y-2",
                      aiMode === "local"
                        ? "border-primary/40 bg-primary/10"
                        : "border-white/10 bg-white/5 hover:bg-white/10"
                    )}
                    onClick={() => setAiMode("local")}
                    data-testid="button-onboarding-local"
                  >
                    <Cpu className="w-5 h-5 text-primary" />
                    <p className="text-sm font-medium">Local GPU</p>
                    <p className="text-xs text-muted-foreground">Ollama models, private, no API cost, runs on your machine</p>
                  </button>
                </div>
                {aiMode === "cloud" && (
                  <div className="space-y-1.5">
                    <Label className="text-xs text-muted-foreground">OpenAI API Key</Label>
                    <Input
                      type="password"
                      value={apiKey}
                      onChange={e => setApiKey(e.target.value)}
                      placeholder="sk-..."
                      className="glass-input text-sm font-mono"
                      data-testid="input-onboarding-apikey"
                    />
                    <p className="text-xs text-muted-foreground">You can add this later in Settings if you skip for now.</p>
                  </div>
                )}
                {aiMode === "local" && (
                  <div className="space-y-1.5">
                    <Label className="text-xs text-muted-foreground">Ollama Base URL</Label>
                    <Input
                      value={ollamaUrl}
                      onChange={e => setOllamaUrl(e.target.value)}
                      className="glass-input text-sm font-mono"
                      data-testid="input-onboarding-ollama-url"
                    />
                    <p className="text-xs text-muted-foreground">
                      Install Ollama at <span className="text-primary">ollama.ai</span>, then run: <code className="text-primary">ollama pull llama3</code>
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* Knowledge */}
            {step === "knowledge" && (
              <div className="space-y-5">
                <div className="text-center">
                  <div className="w-12 h-12 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center mx-auto mb-3">
                    <Brain className="w-6 h-6 text-primary" />
                  </div>
                  <h2 className="text-lg font-semibold">Knowledge Base</h2>
                  <p className="text-sm text-muted-foreground mt-1.5">Add a note about your system. AXIOM will read it on every request.</p>
                </div>
                <div className="space-y-3">
                  <div className="space-y-1.5">
                    <Label className="text-xs text-muted-foreground">Note Title</Label>
                    <Input
                      value={noteTitle}
                      onChange={e => setNoteTitle(e.target.value)}
                      className="glass-input text-sm"
                      data-testid="input-onboarding-note-title"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label className="text-xs text-muted-foreground">Note Content</Label>
                    <Textarea
                      value={noteContent}
                      onChange={e => setNoteContent(e.target.value)}
                      className="glass-input text-sm min-h-[100px] resize-none"
                      data-testid="textarea-onboarding-note-content"
                    />
                  </div>
                </div>
                <p className="text-xs text-muted-foreground">You can add, edit, and remove notes anytime in the Knowledge Base.</p>
              </div>
            )}

            {/* Done */}
            {step === "done" && (
              <div className="text-center space-y-5">
                <motion.div
                  initial={{ scale: 0.7, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={{ type: "spring", stiffness: 200, damping: 15 }}
                  className="w-20 h-20 rounded-2xl bg-green-500/15 border border-green-500/25 flex items-center justify-center mx-auto shadow-[0_0_40px_rgba(34,197,94,0.1)]"
                >
                  <CheckCircle2 className="w-10 h-10 text-green-400" />
                </motion.div>
                <div>
                  <h2 className="text-2xl font-bold">You're all set</h2>
                  <p className="text-sm text-muted-foreground mt-2 leading-relaxed max-w-sm mx-auto">
                    AXIOM is configured and ready. You can change any of these settings later from the Settings panel.
                  </p>
                </div>
                <div className="space-y-2">
                  {[
                    `Hotkey: ${hotkey}`,
                    `AI Mode: ${aiMode === "cloud" ? "Cloud (OpenAI)" : "Local GPU (Ollama)"}`,
                    paths.filter(p => p.trim()).length > 0 ? `${paths.filter(p => p.trim()).length} allowed path(s) added` : "No paths added yet (add in Settings)",
                  ].map((line, i) => (
                    <div key={i} className="flex items-center gap-2 text-xs text-muted-foreground px-3 py-2 rounded-lg bg-white/5">
                      <CheckCircle2 className="w-3 h-3 text-primary shrink-0" />
                      {line}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </motion.div>
        </AnimatePresence>

        {/* Navigation */}
        <div className="flex items-center justify-between mt-8">
          <p className="text-xs text-muted-foreground">
            Step {stepIndex + 1} of {STEPS.length}
          </p>
          <div className="flex gap-2">
            {step !== "welcome" && step !== "done" && (
              <Button
                variant="ghost"
                size="sm"
                className="text-xs text-muted-foreground"
                onClick={() => {
                  const prev = STEPS[stepIndex - 1];
                  if (prev) setStep(prev.id);
                }}
              >
                Back
              </Button>
            )}
            {step !== "done" ? (
              <Button
                size="sm"
                className="bg-primary/20 hover:bg-primary/30 text-primary border border-primary/30 text-xs gap-1.5"
                onClick={next}
                data-testid="button-onboarding-next"
              >
                {step === "knowledge" ? "Almost done" : "Continue"}
                <ArrowRight className="w-3.5 h-3.5" />
              </Button>
            ) : (
              <Button
                size="sm"
                className="bg-primary/20 hover:bg-primary/30 text-primary border border-primary/30 text-xs gap-1.5"
                onClick={handleComplete}
                disabled={completing}
                data-testid="button-onboarding-finish"
              >
                {completing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Zap className="w-3.5 h-3.5" />}
                Launch AXIOM
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
