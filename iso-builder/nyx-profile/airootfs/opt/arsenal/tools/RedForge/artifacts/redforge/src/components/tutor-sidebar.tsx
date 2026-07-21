import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Bot, User, Loader2, X, SendHorizontal } from "lucide-react";
import { MarkdownRenderer } from "./markdown-renderer";

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface TutorSidebarProps {
  context?: string;
  onClose: () => void;
}

export function TutorSidebar({ context, onClose }: TutorSidebarProps) {
  const [messages, setMessages] = useState<Message[]>([
    { role: "assistant", content: "AI Assistant ready. How can I assist your operation?" }
  ]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isTyping]);

  const handleSend = async () => {
    if (!input.trim() || isTyping) return;
    
    const userMessage = input;
    setInput("");
    setMessages(prev => [...prev, { role: "user", content: userMessage }]);
    setIsTyping(true);

    try {
      const response = await fetch(`${import.meta.env.BASE_URL}api/tutor/explain`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: userMessage, context })
      });

      if (!response.ok) throw new Error("Stream failed");
      
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      
      setMessages(prev => [...prev, { role: "assistant", content: "" }]);

      if (reader) {
        let text = "";
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value);
          // Simple SSE parsing: look for data: ...
          const lines = chunk.split('\n');
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6);
              if (data === '[DONE]') continue;
              try {
                const parsed = JSON.parse(data);
                if (parsed.content) {
                  text += parsed.content;
                  setMessages(prev => {
                    const newArr = [...prev];
                    newArr[newArr.length - 1].content = text;
                    return newArr;
                  });
                }
              } catch (e) {
                // ignore parse errors for partial chunks
              }
            }
          }
        }
      }
    } catch (err) {
      setMessages(prev => {
        const newArr = [...prev];
        newArr[newArr.length - 1].content = "Error connecting to AI Tutor.";
        return newArr;
      });
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="w-80 h-full border-l border-border bg-sidebar flex flex-col absolute right-0 top-0 bottom-0 z-20 shadow-2xl">
      <div className="flex items-center justify-between p-3 border-b border-border bg-muted/20">
        <div className="flex items-center gap-2 text-primary text-sm font-bold tracking-widest uppercase">
          <Bot className="w-4 h-4" />
          Tactical AI
        </div>
        <Button variant="ghost" size="icon" className="h-6 w-6" onClick={onClose}>
          <X className="w-4 h-4" />
        </Button>
      </div>

      <div ref={scrollRef} className="flex-1 p-4 overflow-y-auto">
        <div className="space-y-4">
          {messages.map((msg, i) => (
            <div key={i} className={`flex flex-col ${msg.role === "user" ? "items-end" : "items-start"}`}>
              <div className={`flex items-center gap-2 mb-1 text-[10px] uppercase tracking-widest ${msg.role === "user" ? "text-muted-foreground flex-row-reverse" : "text-primary"}`}>
                {msg.role === "user" ? <User className="w-3 h-3" /> : <Bot className="w-3 h-3" />}
                {msg.role === "user" ? "Operator" : "System"}
              </div>
              <div className={`p-3 rounded max-w-[90%] text-xs ${
                msg.role === "user" 
                  ? "bg-muted text-foreground border border-border" 
                  : "bg-primary/10 border border-primary/20 text-foreground"
              }`}>
                {msg.role === "user" ? (
                  <div className="whitespace-pre-wrap font-mono">{msg.content}</div>
                ) : (
                  <MarkdownRenderer content={msg.content} className="prose-xs" />
                )}
              </div>
            </div>
          ))}
          {isTyping && (
            <div className="flex items-start">
              <div className="p-3 rounded bg-primary/10 border border-primary/20 flex items-center gap-2">
                <Loader2 className="w-3 h-3 animate-spin text-primary" />
                <span className="text-xs text-primary font-mono animate-pulse">PROCESSING...</span>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="p-3 border-t border-border bg-muted/10">
        <form onSubmit={(e) => { e.preventDefault(); handleSend(); }} className="flex gap-2">
          <Input 
            value={input} 
            onChange={e => setInput(e.target.value)} 
            placeholder="Query intelligence..." 
            className="font-mono text-xs bg-background h-8"
            disabled={isTyping}
          />
          <Button type="submit" size="icon" disabled={!input.trim() || isTyping} className="h-8 w-8 shrink-0">
            <SendHorizontal className="w-4 h-4" />
          </Button>
        </form>
      </div>
    </div>
  );
}
