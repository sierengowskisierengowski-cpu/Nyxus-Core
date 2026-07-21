import { useState, useRef, useEffect } from "react";
import { useAcceptDisclaimer, useGetAuthStatus } from "@workspace/api-client-react";
import { useLocation } from "wouter";
import { useToast } from "@/hooks/use-toast";
import { useDocumentTitle } from "@/hooks/use-document-title";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { DISCLAIMER_TEXT } from "@/lib/constants";
import { AlertTriangle } from "lucide-react";
import ReactMarkdown from "react-markdown";

export default function Disclaimer() {
  useDocumentTitle("Legal Disclaimer");
  const [, setLocation] = useLocation();
  const { toast } = useToast();
  const acceptMutation = useAcceptDisclaimer();
  const { data: authStatus } = useGetAuthStatus();
  
  const [scrolledToBottom, setScrolledToBottom] = useState(false);
  const [accepted, setAccepted] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const handleScroll = () => {
    if (!scrollRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
    if (scrollHeight - scrollTop - clientHeight < 10) {
      setScrolledToBottom(true);
    }
  };

  useEffect(() => {
    handleScroll(); // Check if initially fits in view
  }, []);

  const handleSubmit = () => {
    if (!accepted) return;
    
    acceptMutation.mutate(undefined, {
      onSuccess: () => {
        toast({ title: "Disclaimer Accepted", description: "Entering REDFORGE." });
        setLocation("/");
      },
      onError: (err) => {
        toast({ title: "Error", description: "Failed to record acceptance.", variant: "destructive" });
      }
    });
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-background p-4 sm:p-8">
      <div className="w-full max-w-3xl flex flex-col h-[80vh] border border-destructive/50 bg-card shadow-2xl relative overflow-hidden">
        
        <div className="bg-destructive text-destructive-foreground p-4 flex items-center gap-3 shrink-0">
          <AlertTriangle className="w-6 h-6 animate-pulse" />
          <div>
            <h1 className="font-bold tracking-widest uppercase">Mandatory Legal Disclaimer</h1>
            <p className="text-xs opacity-90">Read carefully before proceeding. Operator: {authStatus?.username || "Unknown"}</p>
          </div>
        </div>

        <div 
          ref={scrollRef}
          onScroll={handleScroll}
          className="flex-1 overflow-y-auto p-6 md:p-8 bg-background prose prose-invert prose-red max-w-none font-mono text-sm leading-relaxed"
        >
          <ReactMarkdown>{DISCLAIMER_TEXT}</ReactMarkdown>
        </div>

        <div className="p-6 border-t border-border bg-card shrink-0 space-y-6">
          <div className="flex items-center space-x-3">
            <Checkbox 
              id="accept" 
              checked={accepted} 
              onCheckedChange={(c) => setAccepted(c as boolean)} 
              disabled={!scrolledToBottom}
              className="border-destructive data-[state=checked]:bg-destructive data-[state=checked]:text-destructive-foreground"
            />
            <label 
              htmlFor="accept" 
              className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-50 text-foreground"
            >
              I understand and accept all terms, and confirm I am authorized to test my network.
            </label>
          </div>

          <Button 
            onClick={handleSubmit} 
            disabled={!accepted || acceptMutation.isPending} 
            variant="destructive"
            className="w-full font-mono uppercase tracking-widest h-12"
          >
            {acceptMutation.isPending ? "Recording..." : "Acknowledge & Enter REDFORGE"}
          </Button>
        </div>
        
      </div>
    </div>
  );
}
