import { useLocation } from "wouter";
import { useGetDashboardSummary, useGetActiveMission } from "@workspace/api-client-react";
import { Terminal } from "lucide-react";
import { cn } from "@/lib/utils";

export function Topbar() {
  const [location] = useLocation();
  const { data: summary } = useGetDashboardSummary();
  const { data: activeMissionData } = useGetActiveMission();
  
  const activeMission = activeMissionData?.mission;

  // Simple path-to-title logic
  const getPageTitle = () => {
    if (location === "/") return "MISSION CONTROL";
    const segment = location.split("/")[1];
    return segment ? segment.toUpperCase() : "";
  };

  return (
    <header className="h-14 border-b border-border bg-background/95 backdrop-blur z-10 flex items-center justify-between px-6 shrink-0">
      <div className="flex items-center gap-4">
        <h1 className="font-bold text-sm tracking-widest text-foreground/90">
          // {getPageTitle()}
        </h1>
      </div>

      <div className="flex items-center gap-4">
        {activeMission && (
          <div className="flex items-center gap-2 bg-destructive/10 border border-destructive/30 px-3 py-1 rounded text-destructive text-xs font-medium animate-pulse">
            <span className="w-2 h-2 rounded-full bg-destructive" />
            MISSION ACTIVE: {activeMission.scenarioName}
          </div>
        )}
        
        {summary?.threatLevel && (
          <div className={cn(
            "text-xs px-2 py-1 border rounded uppercase tracking-wider font-semibold",
            summary.threatLevel === "ELEVATED" ? "border-primary text-primary bg-primary/10" : "border-secondary text-secondary bg-secondary/10"
          )}>
            THREAT LEVEL: {summary.threatLevel}
          </div>
        )}

        <button 
          className="flex items-center gap-2 text-xs text-muted-foreground bg-muted/50 border border-border px-2 py-1 rounded hover:bg-muted transition-colors"
          onClick={() => {
            document.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', metaKey: true }));
          }}
        >
          <Terminal className="w-3 h-3" />
          <span>CMD</span>
          <kbd className="font-sans text-[10px] bg-background px-1 rounded border border-border">⌘K</kbd>
        </button>
      </div>
    </header>
  );
}
