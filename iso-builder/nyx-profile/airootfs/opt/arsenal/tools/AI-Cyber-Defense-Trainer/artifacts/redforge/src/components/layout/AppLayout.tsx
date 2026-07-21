import { Link, useLocation } from "wouter";
import { Terminal, Crosshair, Target, Network, BookOpen, BarChart2, ShieldAlert, LogOut } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { ReactNode } from "react";

export function AppLayout({ children }: { children: ReactNode }) {
  const [location] = useLocation();
  const { logout } = useAuth();

  const links = [
    { href: "/", label: "MISSION CONTROL", icon: Terminal },
    { href: "/generate", label: "ATTACK GENERATOR", icon: Crosshair },
    { href: "/missions", label: "MISSION ARCHIVE", icon: Target },
    { href: "/notes", label: "STUDY NOTES", icon: BookOpen },
    { href: "/network", label: "NETWORK MAP", icon: Network },
    { href: "/knowledge-base", label: "KNOWLEDGE BASE", icon: ShieldAlert },
    { href: "/stats", label: "TRAINING STATS", icon: BarChart2 },
  ];

  return (
    <div className="min-h-screen flex bg-background text-foreground">
      {/* Sidebar */}
      <div className="w-64 border-r border-border bg-card flex flex-col">
        <div className="p-6 border-b border-border">
          <div className="flex items-center gap-3 text-primary">
            <Terminal size={24} />
            <h1 className="font-bold tracking-widest text-lg">REDFORGE</h1>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto py-4">
          <nav className="space-y-1 px-2">
            {links.map((link) => {
              const active = location === link.href;
              const Icon = link.icon;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    active ? "bg-primary/10 text-primary" : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                  }`}
                >
                  <Icon size={18} />
                  {link.label}
                </Link>
              );
            })}
          </nav>
        </div>
        <div className="p-4 border-t border-border">
          <button
            onClick={logout}
            className="flex items-center gap-3 px-3 py-2 w-full rounded-md text-sm font-medium text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition-colors"
          >
            <LogOut size={18} />
            DISCONNECT
          </button>
        </div>
      </div>
      
      {/* Main Content */}
      <div className="flex-1 flex flex-col h-screen overflow-hidden">
        <main className="flex-1 overflow-y-auto p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
