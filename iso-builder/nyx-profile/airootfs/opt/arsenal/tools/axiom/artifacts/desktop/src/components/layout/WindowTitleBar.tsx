import { useEffect, useState } from "react";
import { Minus, Square, X, Pin, PinOff } from "lucide-react";
import { electron, isElectron } from "@/lib/electron-api";
import { cn } from "@/lib/utils";

export function WindowTitleBar() {
  const [pinned, setPinned] = useState(false);
  const [platform, setPlatform] = useState<string>("browser");

  useEffect(() => {
    setPlatform(electron.platform);
    // Listen for pin state changes from main process
    const unsub = electron.onPinChanged((p) => setPinned(p));
    return unsub;
  }, []);

  if (!isElectron) return null;

  const handlePin = () => {
    const next = !pinned;
    setPinned(next);
    electron.setPinned(next);
  };

  const handleMinimize = () => electron.minimizeWindow();
  const handleClose = () => electron.hideWindow();

  // macOS uses traffic-light controls built into the native titlebar, so just show pin
  const isMac = platform === "darwin";

  return (
    <div
      className="h-8 shrink-0 flex items-center justify-between px-3 select-none"
      style={{ WebkitAppRegion: "drag" } as React.CSSProperties}
    >
      {/* Left: app name */}
      <span className="text-[10px] font-semibold tracking-widest text-muted-foreground/50 uppercase">
        AXIOM
      </span>

      {/* Right: window controls */}
      <div
        className="flex items-center gap-1"
        style={{ WebkitAppRegion: "no-drag" } as React.CSSProperties}
      >
        <button
          onClick={handlePin}
          title={pinned ? "Unpin window" : "Pin window (always on top)"}
          className={cn(
            "w-5 h-5 rounded flex items-center justify-center transition-colors",
            pinned
              ? "text-primary bg-primary/20 hover:bg-primary/30"
              : "text-muted-foreground/40 hover:text-muted-foreground hover:bg-white/10"
          )}
        >
          {pinned ? <Pin className="w-2.5 h-2.5" /> : <PinOff className="w-2.5 h-2.5" />}
        </button>

        {!isMac && (
          <>
            <button
              onClick={handleMinimize}
              title="Minimize"
              className="w-5 h-5 rounded flex items-center justify-center text-muted-foreground/40 hover:text-muted-foreground hover:bg-white/10 transition-colors"
            >
              <Minus className="w-2.5 h-2.5" />
            </button>
            <button
              onClick={handleClose}
              title="Close to tray"
              className="w-5 h-5 rounded flex items-center justify-center text-muted-foreground/40 hover:text-red-400 hover:bg-red-500/10 transition-colors"
            >
              <X className="w-2.5 h-2.5" />
            </button>
          </>
        )}
      </div>
    </div>
  );
}
