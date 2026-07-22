import { Sidebar } from "./Sidebar";
import { WindowTitleBar } from "./WindowTitleBar";
import { useLocation } from "wouter";
import { useEffect } from "react";
import { useGetSettings, getGetSettingsQueryKey } from "@workspace/api-client-react";

function applyTheme(theme: string) {
  const root = document.documentElement;
  if (theme === "light") {
    root.classList.remove("dark");
    root.classList.add("light");
  } else if (theme === "dark") {
    root.classList.remove("light");
    root.classList.add("dark");
  } else {
    // system
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    root.classList.remove("light", "dark");
    root.classList.add(prefersDark ? "dark" : "light");
  }
}

export function AppLayout({ children }: { children: React.ReactNode }) {
  const [location] = useLocation();
  const { data: settings } = useGetSettings({ query: { queryKey: getGetSettingsQueryKey() } });

  useEffect(() => {
    const theme = settings?.theme ?? "dark";
    applyTheme(theme);

    if (theme === "system") {
      const mq = window.matchMedia("(prefers-color-scheme: dark)");
      const handler = () => applyTheme("system");
      mq.addEventListener("change", handler);
      return () => mq.removeEventListener("change", handler);
    }
    return undefined;
  }, [settings?.theme]);

  return (
    <div className="flex h-screen w-full overflow-hidden bg-background">
      {/* Subtle noise/grain texture overlay */}
      <div className="absolute inset-0 opacity-[0.025] pointer-events-none z-0"
        style={{ backgroundImage: "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E\")", backgroundRepeat: "repeat", backgroundSize: "128px 128px" }} />
      <Sidebar />
      <main className="flex-1 overflow-auto relative z-10 h-full p-3 flex flex-col">
        <WindowTitleBar />
        <div className="flex-1 glass-panel rounded-2xl overflow-hidden shadow-2xl relative flex flex-col min-h-0">
          {children}
        </div>
      </main>
    </div>
  );
}
