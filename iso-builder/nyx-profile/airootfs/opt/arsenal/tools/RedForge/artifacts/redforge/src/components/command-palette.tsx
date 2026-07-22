import { useEffect, useState } from "react";
import { useLocation } from "wouter";
import { CommandDialog, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { Target, TerminalSquare, BookOpen, Activity, Network, Settings } from "lucide-react";

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [, setLocation] = useLocation();

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((open) => !open);
      }
    };

    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, []);

  const runCommand = (command: () => void) => {
    setOpen(false);
    command();
  };

  return (
    <CommandDialog open={open} onOpenChange={setOpen}>
      <CommandInput placeholder="Type a command or search..." />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>
        <CommandGroup heading="Operations">
          <CommandItem onSelect={() => runCommand(() => setLocation("/scenarios"))}>
            <Target className="mr-2 h-4 w-4" />
            <span>Deploy Scenario</span>
          </CommandItem>
          <CommandItem onSelect={() => runCommand(() => setLocation("/missions"))}>
            <TerminalSquare className="mr-2 h-4 w-4" />
            <span>Active Missions</span>
          </CommandItem>
          <CommandItem onSelect={() => runCommand(() => setLocation("/network"))}>
            <Network className="mr-2 h-4 w-4" />
            <span>Network Scanner</span>
          </CommandItem>
        </CommandGroup>
        <CommandGroup heading="Knowledge">
          <CommandItem onSelect={() => runCommand(() => setLocation("/notes"))}>
            <BookOpen className="mr-2 h-4 w-4" />
            <span>Search Notes</span>
          </CommandItem>
          <CommandItem onSelect={() => runCommand(() => setLocation("/kb"))}>
            <BookOpen className="mr-2 h-4 w-4" />
            <span>Knowledge Base</span>
          </CommandItem>
        </CommandGroup>
        <CommandGroup heading="System">
          <CommandItem onSelect={() => runCommand(() => setLocation("/scoreboard"))}>
            <Activity className="mr-2 h-4 w-4" />
            <span>Scoreboard</span>
          </CommandItem>
          <CommandItem onSelect={() => runCommand(() => setLocation("/settings"))}>
            <Settings className="mr-2 h-4 w-4" />
            <span>Settings</span>
          </CommandItem>
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
}
