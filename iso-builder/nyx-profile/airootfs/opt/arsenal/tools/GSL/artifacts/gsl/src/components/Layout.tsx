import { Link, useLocation } from "wouter";
import {
  AlertTriangle, Home, Wrench, History as HistoryIcon,
  FileText, ShieldAlert, Search, Menu, BookOpen,
  Wifi, Activity, Terminal, Zap, LogOut,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { ReactNode, useState, useEffect } from "react";
import { CommandPalette } from "./CommandPalette";
import { useQuery } from "@tanstack/react-query";
import { apiFetch, logout } from "@/lib/api";

interface SystemStats {
  cpu: { percent: number };
  memory: { percent: number };
}

const navSections = [
  {
    label: "Workspace",
    items: [
      { href: "/", icon: Home, label: "Dashboard", color: "#7B6FD4" },
      { href: "/tools", icon: Wrench, label: "Tools", color: "#7B6FD4" },
    ],
  },
  {
    label: "Analysis",
    items: [
      { href: "/history", icon: HistoryIcon, label: "History", color: "#60a5fa" },
      { href: "/findings", icon: ShieldAlert, label: "Findings", color: "#f87171" },
    ],
  },
  {
    label: "Study",
    items: [
      { href: "/learn", icon: BookOpen, label: "Learn", color: "#4ade80" },
      { href: "/library", icon: Terminal, label: "Command Library", color: "#4ade80" },
      { href: "/notes", icon: FileText, label: "Notes", color: "#fbbf24" },
    ],
  },
];

export function Layout({ children }: { children: ReactNode }) {
  const [location] = useLocation();
  const [open, setOpen] = useState(false);
  const [cmdOpen, setCmdOpen] = useState(false);
  const [time, setTime] = useState(() => new Date());

  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setCmdOpen((v) => !v);
      }
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, []);

  const { data: sysStats } = useQuery<SystemStats>({
    queryKey: ["system-stats-sidebar"],
    queryFn: () => apiFetch<SystemStats>("/api/dashboard/system-stats"),
    refetchInterval: 10000,
    staleTime: 8000,
  });

  const timeStr = time.toLocaleTimeString("en-US", {
    hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false,
  });
  const dateStr = time.toLocaleDateString("en-US", { month: "short", day: "numeric" });

  const NavLinks = ({ onNav }: { onNav?: () => void }) => (
    <div className="space-y-5">
      {navSections.map((section) => (
        <div key={section.label}>
          <div className="sidebar-section-label">{section.label}</div>
          <div className="space-y-0.5 mt-1">
            {section.items.map((item) => {
              const isActive =
                location === item.href ||
                (item.href !== "/" && location.startsWith(item.href));
              return (
                <Link key={item.href} href={item.href}>
                  <span
                    className={`relative flex items-center gap-2.5 px-3 py-2 text-[13px] rounded-sm transition-all duration-150 cursor-pointer select-none ${
                      isActive
                        ? "nav-active font-medium"
                        : "text-muted-foreground hover:text-foreground hover:bg-white/[0.03]"
                    }`}
                    onClick={onNav}
                  >
                    <item.icon
                      className="h-4 w-4 flex-shrink-0 transition-colors"
                      style={{ color: isActive ? item.color : undefined }}
                    />
                    <span className="flex-1">{item.label}</span>
                    {isActive && (
                      <span
                        className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                        style={{ background: item.color, boxShadow: `0 0 6px ${item.color}` }}
                      />
                    )}
                  </span>
                </Link>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );

  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground dark">
      {/* Security Banner */}
      <div
        className="flex items-center justify-center gap-2 px-4 py-1.5 text-[11px] font-medium flex-shrink-0 z-50"
        style={{
          background: "linear-gradient(90deg, rgba(251,191,36,0.06) 0%, rgba(251,191,36,0.04) 50%, rgba(251,191,36,0.06) 100%)",
          borderBottom: "1px solid rgba(251,191,36,0.12)",
          color: "rgba(251,191,36,0.75)",
        }}
      >
        <AlertTriangle className="h-3 w-3" />
        <span>Authorized use on GowskiNet (192.168.0.x) only</span>
        <span className="mx-2 opacity-30">·</span>
        <span className="opacity-50 font-mono">nyx-cosmic · 192.168.0.172</span>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Desktop Sidebar */}
        <aside
          className="hidden md:flex w-[230px] flex-col flex-shrink-0"
          style={{
            background: "hsl(237 38% 3.5%)",
            borderRight: "1px solid hsl(232 18% 10%)",
          }}
        >
          {/* Brand */}
          <div className="px-4 pt-4 pb-3.5" style={{ borderBottom: "1px solid hsl(232 18% 10%)" }}>
            <div className="flex items-center gap-3">
              <div
                className="w-8 h-8 rounded flex items-center justify-center flex-shrink-0 relative"
                style={{
                  background: "linear-gradient(135deg, hsl(263 55% 62% / 0.2), hsl(192 100% 50% / 0.1))",
                  border: "1px solid hsl(263 55% 62% / 0.3)",
                  boxShadow: "0 0 12px hsl(263 55% 62% / 0.15)",
                }}
              >
                <Terminal className="h-4 w-4" style={{ color: "hsl(263 55% 72%)" }} />
              </div>
              <div className="min-w-0">
                <div className="text-[13px] font-bold font-mono tracking-widest" style={{ color: "hsl(220 20% 95%)", letterSpacing: "0.15em" }}>
                  GSL
                </div>
                <div className="text-[9px] font-mono opacity-40 tracking-wider">
                  GOWSKINET SECURITY LAB
                </div>
              </div>
              <div className="ml-auto">
                <div
                  className="text-[9px] font-mono px-1.5 py-0.5 rounded-sm font-semibold tracking-widest"
                  style={{
                    background: "hsl(263 55% 62% / 0.12)",
                    border: "1px solid hsl(263 55% 62% / 0.25)",
                    color: "hsl(263 55% 75%)",
                  }}
                >
                  v2
                </div>
              </div>
            </div>
          </div>

          {/* Nav */}
          <nav className="flex-1 p-3 pt-4 overflow-y-auto">
            <NavLinks />
          </nav>

          {/* System micro stats */}
          {sysStats && (
            <div className="px-3 py-2.5 mx-3 mb-2 rounded-sm" style={{ background: "hsl(235 28% 6%)", border: "1px solid hsl(232 18% 11%)" }}>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-[9px] uppercase tracking-wider font-mono" style={{ color: "hsl(232 10% 35%)" }}>System</span>
                <Activity className="h-2.5 w-2.5" style={{ color: "hsl(263 55% 55%)" }} />
              </div>
              <div className="space-y-1.5">
                <div>
                  <div className="flex justify-between mb-0.5">
                    <span className="text-[9px] font-mono text-muted-foreground/60">CPU</span>
                    <span className="text-[9px] font-mono tabular-nums" style={{ color: "hsl(220 20% 80%)" }}>{sysStats.cpu.percent}%</span>
                  </div>
                  <div className="gauge-bar">
                    <div
                      className="gauge-fill"
                      style={{
                        width: `${sysStats.cpu.percent}%`,
                        background: sysStats.cpu.percent > 85 ? "#f87171" : sysStats.cpu.percent > 60 ? "#fbbf24" : "hsl(263 55% 62%)",
                      }}
                    />
                  </div>
                </div>
                <div>
                  <div className="flex justify-between mb-0.5">
                    <span className="text-[9px] font-mono text-muted-foreground/60">MEM</span>
                    <span className="text-[9px] font-mono tabular-nums" style={{ color: "hsl(220 20% 80%)" }}>{sysStats.memory.percent}%</span>
                  </div>
                  <div className="gauge-bar">
                    <div
                      className="gauge-fill"
                      style={{
                        width: `${sysStats.memory.percent}%`,
                        background: sysStats.memory.percent > 85 ? "#f87171" : sysStats.memory.percent > 70 ? "#fbbf24" : "#60a5fa",
                      }}
                    />
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Footer */}
          <div className="p-3" style={{ borderTop: "1px solid hsl(232 18% 10%)" }}>
            <button
              onClick={() => setCmdOpen(true)}
              className="w-full flex items-center gap-2 px-3 py-2 rounded-sm transition-colors mb-2.5 group"
              style={{
                background: "hsl(235 28% 6.5%)",
                border: "1px solid hsl(232 18% 12%)",
                color: "hsl(232 10% 48%)",
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLButtonElement).style.borderColor = "hsl(263 55% 62% / 0.3)";
                (e.currentTarget as HTMLButtonElement).style.color = "hsl(220 20% 85%)";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLButtonElement).style.borderColor = "hsl(232 18% 12%)";
                (e.currentTarget as HTMLButtonElement).style.color = "hsl(232 10% 48%)";
              }}
            >
              <Search className="h-3 w-3" />
              <span className="flex-1 text-left text-[11px]">Quick launch...</span>
              <kbd>⌘K</kbd>
            </button>

            <div className="flex items-center justify-between px-1">
              <div className="flex items-center gap-2">
                <div className="relative">
                  <div className="w-2 h-2 rounded-full bg-green-500 pulse-dot" />
                </div>
                <span className="text-[10px] font-mono font-semibold" style={{ color: "#4ade80" }}>ONLINE</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="text-[9px] font-mono tabular-nums" style={{ color: "hsl(232 10% 38%)" }}>
                  {dateStr} · {timeStr}
                </div>
                <button
                  onClick={async () => {
                    await logout();
                    window.dispatchEvent(new Event("gsl:unauthorized"));
                  }}
                  title="Sign out"
                  className="text-muted-foreground hover:text-foreground transition-colors"
                >
                  <LogOut className="h-3 w-3" />
                </button>
              </div>
            </div>
          </div>
        </aside>

        {/* Mobile Header */}
        <div
          className="md:hidden px-4 py-3 flex items-center justify-between w-full flex-shrink-0"
          style={{ background: "hsl(237 38% 3.5%)", borderBottom: "1px solid hsl(232 18% 10%)" }}
        >
          <div className="flex items-center gap-2.5">
            <div
              className="w-7 h-7 rounded flex items-center justify-center"
              style={{
                background: "hsl(263 55% 62% / 0.15)",
                border: "1px solid hsl(263 55% 62% / 0.3)",
              }}
            >
              <Zap className="h-3.5 w-3.5" style={{ color: "hsl(263 55% 72%)" }} />
            </div>
            <span className="text-sm font-bold font-mono tracking-widest" style={{ letterSpacing: "0.15em" }}>GSL</span>
          </div>
          <div className="flex items-center gap-1">
            <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setCmdOpen(true)}>
              <Search className="h-4 w-4" />
            </Button>
            <Sheet open={open} onOpenChange={setOpen}>
              <SheetTrigger asChild>
                <Button variant="ghost" size="icon" className="h-8 w-8">
                  <Menu className="h-4 w-4" />
                </Button>
              </SheetTrigger>
              <SheetContent side="left" className="w-[230px] p-0" style={{ background: "hsl(237 38% 3.5%)", borderColor: "hsl(232 18% 10%)" }}>
                <div className="px-4 py-4" style={{ borderBottom: "1px solid hsl(232 18% 10%)" }}>
                  <div className="text-sm font-bold font-mono tracking-widest" style={{ letterSpacing: "0.15em" }}>GSL</div>
                  <div className="text-[10px] font-mono opacity-40 mt-0.5">nyx-cosmic · 192.168.0.172</div>
                </div>
                <nav className="p-3 pt-4">
                  <NavLinks onNav={() => setOpen(false)} />
                </nav>
              </SheetContent>
            </Sheet>
          </div>
        </div>

        {/* Main Content */}
        <main className="flex-1 overflow-y-auto bg-grid">
          {children}
        </main>
      </div>

      <CommandPalette open={cmdOpen} onOpenChange={setCmdOpen} />
    </div>
  );
}
