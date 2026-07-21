import { ReactNode } from "react";
import { Sidebar } from "./sidebar";
import { Topbar } from "./topbar";
import { Footer } from "./footer";
import { CommandPalette } from "./command-palette";
import { AuthGate } from "./auth-gate";

interface LayoutProps {
  children: ReactNode;
}

export function Layout({ children }: LayoutProps) {
  return (
    <AuthGate>
      <div className="flex h-screen overflow-hidden bg-background text-foreground selection:bg-primary/30">
        <Sidebar />
        <div className="flex flex-col flex-1 min-w-0 overflow-hidden relative">
          <Topbar />
          <main className="flex-1 overflow-y-auto overflow-x-hidden p-6 relative">
            <div className="mx-auto max-w-[1600px] w-full h-full flex flex-col">
              {children}
            </div>
          </main>
          <Footer />
        </div>
        <CommandPalette />
      </div>
    </AuthGate>
  );
}
