import React from "react";
import { Link, useLocation } from "wouter";
import {
  Terminal,
  Hash,
  Crosshair,
  Activity,
  FileSearch,
  Library,
  Braces,
  Database,
  ShieldAlert,
  BookOpen,
  Settings,
  Cpu,
  LogOut,
} from "lucide-react";
import { useGetActiveJobs, useGetSystemStats, useLogout } from "@workspace/api-client-react";
import { clearToken } from "@/lib/auth";

export function Layout({ children }: { children: React.ReactNode }) {
  const [location] = useLocation();
  const { data: activeJobs } = useGetActiveJobs({ query: { refetchInterval: 3000, queryKey: ["getActiveJobs"] } });
  const { data: stats } = useGetSystemStats({ query: { refetchInterval: 5000, queryKey: ["getSystemStatsSidebar"] } });
  const logoutMutation = useLogout();

  const gpu = stats?.gpus?.[0];
  const cpuUsage = stats?.cpu?.usagePercent ?? 0;

  const handleLogout = () => {
    logoutMutation.mutate(undefined, {
      onSettled: () => {
        clearToken();
        window.location.reload();
      },
    });
  };

  const navItems = [
    { href: "/", label: "Dashboard", icon: Terminal },
    { href: "/hashes", label: "Hash Submission", icon: Hash },
    { href: "/attack", label: "Attack Engine", icon: Crosshair },
    { href: "/monitor", label: "Live Monitor", icon: Activity },
    { href: "/results", label: "Results & Analysis", icon: FileSearch },
    { href: "/wordlists", label: "Wordlists", icon: Library },
    { href: "/rules", label: "Rules Library", icon: Braces },
    { href: "/database", label: "Hash Database", icon: Database },
    { href: "/analyzer", label: "Strength Analyzer", icon: ShieldAlert },
    { href: "/notes", label: "Research Notes", icon: BookOpen },
    { href: "/settings", label: "Settings", icon: Settings },
  ];

  return (
    <div className="flex h-screen w-full bg-background text-foreground overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 border-r border-border bg-sidebar flex flex-col justify-between flex-shrink-0">
        <div className="min-h-0 flex flex-col">
          <div className="h-16 flex items-center px-6 border-b border-border">
            <span className="font-mono font-bold text-lg text-primary flex items-center gap-2">
              <Terminal size={20} />
              CIPHER
            </span>
          </div>
          <nav className="p-4 flex flex-col gap-1 overflow-y-auto">
            {navItems.map((item) => {
              const active = location === item.href;
              const Icon = item.icon;
              return (
                <Link key={item.href} href={item.href}>
                  <div className={`flex items-center gap-3 px-3 py-2 rounded-sm cursor-pointer transition-colors ${active ? "bg-primary/10 text-primary border-l-2 border-primary" : "text-muted-foreground hover:bg-card hover:text-foreground border-l-2 border-transparent"}`}>
                    <Icon size={18} />
                    <span className="text-sm font-medium">{item.label}</span>
                    {item.href === "/monitor" && activeJobs && activeJobs.length > 0 && (
                      <span className="ml-auto w-2 h-2 rounded-full bg-success animate-pulse" />
                    )}
                  </div>
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Real system status footer */}
        <div className="p-4 border-t border-border bg-card/50 space-y-3">
          {gpu ? (
            <div className="flex flex-col gap-1">
              <div className="flex justify-between items-center text-xs">
                <span className="text-muted-foreground truncate pr-2">GPU</span>
                <span className="font-mono text-primary">
                  {gpu.temperatureCelsius ?? 0}°C · {gpu.utilizationPercent ?? 0}%
                </span>
              </div>
              <div className="w-full bg-background rounded-full h-1.5 overflow-hidden">
                <div className="bg-primary h-full transition-all duration-500" style={{ width: `${gpu.utilizationPercent ?? 0}%` }} />
              </div>
            </div>
          ) : (
            <div className="text-[10px] text-muted-foreground font-mono">No NVIDIA GPU detected</div>
          )}
          <div className="flex flex-col gap-1">
            <div className="flex justify-between items-center text-xs">
              <span className="text-muted-foreground flex items-center gap-1">
                <Cpu className="w-3 h-3" /> CPU
              </span>
              <span className="font-mono text-primary">{cpuUsage}%</span>
            </div>
            <div className="w-full bg-background rounded-full h-1.5 overflow-hidden">
              <div className="bg-secondary h-full transition-all duration-500" style={{ width: `${cpuUsage}%` }} />
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="w-full flex items-center justify-center gap-2 text-[10px] uppercase tracking-widest text-muted-foreground hover:text-destructive transition-colors pt-1"
          >
            <LogOut className="w-3 h-3" /> Log out
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col min-w-0">
        <header className="h-14 border-b border-border bg-card/30 flex items-center justify-between px-6 flex-shrink-0 backdrop-blur-sm">
          <div className="text-sm text-muted-foreground font-mono">{location}</div>
          <div className="text-xs text-muted-foreground tracking-widest uppercase">GowskiNet Security · Local Lab</div>
        </header>

        <div className="flex-1 overflow-y-auto p-6">{children}</div>
      </main>
    </div>
  );
}
