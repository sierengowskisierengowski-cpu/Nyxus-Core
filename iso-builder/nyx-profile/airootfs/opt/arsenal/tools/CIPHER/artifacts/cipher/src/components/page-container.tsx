import { ReactNode } from "react";

export function PageContainer({ children, title }: { children: ReactNode, title?: string }) {
  return (
    <div className="flex flex-col min-h-full">
      <div className="flex-1">
        {title && <h1 className="text-2xl font-bold mb-6 font-mono tracking-tight text-primary uppercase">{title}</h1>}
        {children}
      </div>
      <footer className="mt-8 py-4 border-t border-border/50 text-center text-[10px] text-muted-foreground uppercase tracking-widest font-mono">
        GowskiNet CIPHER — Authorized Research Only | GowskiNet Security
      </footer>
    </div>
  );
}
