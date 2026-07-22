import { Link, useLocation } from "wouter";
import { MessageSquare, CalendarClock, BookOpen, Activity, Zap, FolderSearch, Settings, BarChart2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { useGetSettings, getGetSettingsQueryKey } from "@workspace/api-client-react";

const LINKS = [
  { href: "/chat",          icon: MessageSquare, label: "Chat",          color: "text-sky-400",    activeBg: "bg-sky-500/10 border-sky-400/30",    bar: "bg-sky-400" },
  { href: "/scheduler",     icon: CalendarClock, label: "Scheduler",     color: "text-amber-400",  activeBg: "bg-amber-500/10 border-amber-400/30", bar: "bg-amber-400" },
  { href: "/knowledge",     icon: BookOpen,      label: "Knowledge",     color: "text-violet-400", activeBg: "bg-violet-500/10 border-violet-400/30",bar: "bg-violet-400" },
  { href: "/activity",      icon: Activity,      label: "Activity",      color: "text-emerald-400",activeBg: "bg-emerald-500/10 border-emerald-400/30",bar:"bg-emerald-400"},
  { href: "/quick-actions", icon: Zap,           label: "Quick Actions", color: "text-yellow-400", activeBg: "bg-yellow-500/10 border-yellow-400/30",bar: "bg-yellow-400" },
  { href: "/files",         icon: FolderSearch,  label: "Files",         color: "text-orange-400", activeBg: "bg-orange-500/10 border-orange-400/30",bar: "bg-orange-400" },
  { href: "/stats",         icon: BarChart2,      label: "Stats",         color: "text-cyan-400",   activeBg: "bg-cyan-500/10 border-cyan-400/30",   bar: "bg-cyan-400" },
  { href: "/settings",      icon: Settings,      label: "Settings",      color: "text-zinc-400",   activeBg: "bg-zinc-500/10 border-zinc-400/30",   bar: "bg-zinc-400" },
];

export function Sidebar() {
  const [location] = useLocation();
  const { data: settings } = useGetSettings({ query: { queryKey: getGetSettingsQueryKey() } });

  if (settings && !settings.onboardingCompleted && location !== "/onboarding") return null;
  if (location === "/onboarding") return null;

  return (
    <div className="w-16 flex-shrink-0 border-r border-white/[0.07] bg-background flex flex-col items-center py-4 space-y-1 h-full relative z-10">
      {/* Logo */}
      <div className="w-9 h-9 rounded-xl bg-indigo-500/15 flex items-center justify-center border border-indigo-400/30 mb-5 shadow-[0_0_12px_rgba(99,102,241,0.15)]">
        <Zap className="w-4 h-4 text-indigo-400" />
      </div>

      {LINKS.map((link) => {
        const isActive = location === link.href || (location === "/" && link.href === "/chat");
        const Icon = link.icon;

        return (
          <Link
            key={link.href}
            href={link.href}
            className={cn(
              "w-10 h-10 flex items-center justify-center rounded-lg transition-all duration-200 relative group border",
              isActive
                ? `${link.activeBg} ${link.color} shadow-[inset_0_1px_0_rgba(255,255,255,0.06)]`
                : "border-transparent text-muted-foreground hover:bg-white/[0.05] hover:border-white/15 hover:text-foreground/80"
            )}
            title={link.label}
          >
            <Icon className="w-4 h-4" />

            {isActive && (
              <div className={cn("absolute -left-px top-1/2 -translate-y-1/2 w-[3px] h-5 rounded-r-full", link.bar)} />
            )}

            <div className="absolute left-[52px] bg-popover text-popover-foreground text-xs px-2.5 py-1.5 rounded-md opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity duration-150 whitespace-nowrap border border-white/[0.08] shadow-xl z-50">
              {link.label}
            </div>
          </Link>
        );
      })}
    </div>
  );
}
