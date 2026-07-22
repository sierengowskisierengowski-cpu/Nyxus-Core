import { Link, useLocation } from "wouter";
import { 
  ShieldAlert, 
  TerminalSquare, 
  Target, 
  Network, 
  BookOpen, 
  BookMarked, 
  Library, 
  Activity, 
  Settings, 
  LogOut 
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useLogout, useGetAuthStatus } from "@workspace/api-client-react";

export function Sidebar() {
  const [location] = useLocation();
  const { data: authStatus } = useGetAuthStatus();
  const logoutMutation = useLogout();

  if (!authStatus?.authenticated) return null;

  const handleLogout = () => {
    logoutMutation.mutate(undefined, {
      onSuccess: () => {
        window.location.href = "/login";
      }
    });
  };

  const navGroups = [
    {
      title: "MISSION CONTROL",
      items: [
        { label: "Dashboard", href: "/", icon: ShieldAlert },
      ]
    },
    {
      title: "OPERATIONS",
      items: [
        { label: "Scenarios", href: "/scenarios", icon: Target },
        { label: "Missions", href: "/missions", icon: TerminalSquare },
        { label: "Network", href: "/network", icon: Network },
      ]
    },
    {
      title: "KNOWLEDGE",
      items: [
        { label: "Notes", href: "/notes", icon: BookOpen },
        { label: "Notebooks", href: "/notebooks", icon: BookMarked },
        { label: "Knowledge Base", href: "/kb", icon: Library },
      ]
    },
    {
      title: "PROGRESS",
      items: [
        { label: "Scoreboard", href: "/scoreboard", icon: Activity },
      ]
    },
    {
      title: "SYSTEM",
      items: [
        { label: "Settings", href: "/settings", icon: Settings },
      ]
    }
  ];

  return (
    <aside className="w-64 border-r border-sidebar-border bg-sidebar text-sidebar-foreground flex flex-col">
      <div className="h-14 flex items-center px-4 border-b border-sidebar-border font-bold text-lg tracking-wider text-primary">
        REDFORGE_
      </div>
      
      <div className="flex-1 overflow-y-auto py-4 space-y-6 scrollbar-thin">
        {navGroups.map((group) => (
          <div key={group.title} className="px-3">
            <h3 className="mb-2 px-2 text-xs font-semibold text-sidebar-foreground/50 tracking-widest uppercase">
              {group.title}
            </h3>
            <div className="space-y-1">
              {group.items.map((item) => {
                const isActive = location === item.href || (item.href !== "/" && location.startsWith(item.href));
                const Icon = item.icon;
                return (
                  <Link 
                    key={item.href} 
                    href={item.href}
                    className={cn(
                      "flex items-center gap-3 px-2 py-1.5 text-sm rounded-md transition-colors",
                      isActive 
                        ? "bg-sidebar-accent text-sidebar-accent-foreground font-medium" 
                        : "text-sidebar-foreground/70 hover:text-sidebar-foreground hover:bg-sidebar-accent/50"
                    )}
                  >
                    <Icon className="w-4 h-4" />
                    {item.label}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      <div className="p-3 border-t border-sidebar-border">
        <button 
          onClick={handleLogout}
          className="flex items-center gap-3 px-2 py-1.5 w-full text-sm text-sidebar-foreground/70 hover:text-destructive hover:bg-destructive/10 rounded-md transition-colors"
        >
          <LogOut className="w-4 h-4" />
          Disconnect
        </button>
      </div>
    </aside>
  );
}
