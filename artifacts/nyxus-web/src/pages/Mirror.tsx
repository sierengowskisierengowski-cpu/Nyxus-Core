// ============================================
// NYXUS — nyx-2026.05.02-x86_64.iso
// Copyright © 2026 Joseph Sierengowski
// All Rights Reserved
// NYX-J5W-2026-SIERENGOWSKI-LOCKED
// ============================================
//
// /mirror — exact visual mirror of the NYXUS Hyprland desktop.
// Thin neon-outlined frames (pink top/bottom/left, gold right), colored
// workspace circles, app launcher squares on the right edge, and a
// wallpaper-only desktop. Click any launcher icon to open that app
// in a window. Web mockups (Notepad, Stickies, SysMon) load
// as live iframes; the 8 tarball apps open NYXUS-themed previews.
//
// All sub-components live in ./components/desktop/* — this file is the
// orchestrator (state + wiring only).

import { useState, useEffect } from "react";
import HomeDashboard from "./HomeDashboard";
import { C, AppDef, useTime, useWallpaperRotation } from "../components/desktop/shared";
import { TopBar } from "../components/desktop/TopBar";
import { LeftBar } from "../components/desktop/LeftBar";
import { RightBar } from "../components/desktop/RightBar";
import { BottomBar } from "../components/desktop/BottomBar";
import { Window } from "../components/desktop/Window";
import { MockupBody } from "../components/desktop/MockupBody";
import { PanelFlyout } from "../components/desktop/PanelFlyout";
import { StartMenu } from "../components/desktop/StartMenu";
import { Notifications } from "../components/desktop/Notifications";
import { SettingsWindow } from "../components/desktop/SettingsWindow";

export default function Mirror() {
  const time = useTime();
  const wp = useWallpaperRotation(15000);

  const [activeWs, setActiveWs] = useState(0);
  const [openApp, setOpenApp] = useState<AppDef | null>(null);
  const [showStart, setShowStart] = useState(false);
  const [showPanel, setShowPanel] = useState(false);
  const [showNotif, setShowNotif] = useState(false);
  const [showSettings, setShowSettings] = useState(false);

  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setOpenApp(null);
        setShowStart(false);
        setShowPanel(false);
        setShowNotif(false);
        setShowSettings(false);
      }
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, []);

  return (
    <div style={{
      position: "fixed",
      inset: 0,
      overflow: "hidden",
      background: C.void,
      fontFamily: '"JetBrains Mono", monospace',
    }}>
      {/* DARK MIRROR fonts — Architects Daughter (wordmarks), Inter (body), JetBrains Mono (stats/code) */}
      <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Architects+Daughter&family=Caveat:wght@400;700&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap" />

      {/* full-bleed wallpaper */}
      <div style={{
        position: "absolute",
        inset: 0,
        backgroundImage: `url(${wp.url})`,
        backgroundSize: "cover",
        backgroundPosition: "center",
        transition: "background-image 1.5s ease-in-out",
      }} />

      {/* dark vignette */}
      <div style={{
        position: "absolute", inset: 0,
        background: "radial-gradient(ellipse at center, rgba(0,0,0,0.18) 0%, rgba(0,0,0,0.42) 100%)",
        pointerEvents: "none",
      }} />

      {/* Bars (neon-outlined floating frames) */}
      <TopBar time={time} />
      <LeftBar  activeWs={activeWs} onSelect={setActiveWs} />
      <RightBar onLaunch={(a) => setOpenApp(a)} openId={openApp?.id ?? null} />
      <BottomBar
        activeWs={activeWs}
        onSelectWs={setActiveWs}
        time={time}
        onHome     ={() => { setActiveWs(0); setShowStart(false); setShowPanel(false); setShowNotif(false); setShowSettings(false); }}
        onStart    ={() => { setShowStart(s => !s);    setShowPanel(false); setShowNotif(false); setShowSettings(false); }}
        onPanel    ={() => { setShowPanel(s => !s);    setShowStart(false); setShowNotif(false); setShowSettings(false); }}
        onNotif    ={() => { setShowNotif(s => !s);    setShowStart(false); setShowPanel(false); setShowSettings(false); }}
        onSettings ={() => { setShowSettings(s => !s); setShowStart(false); setShowPanel(false); setShowNotif(false); }}
      />

      {/* HOME DASHBOARD (workspace 0) — sits inside the desktop area between bars */}
      {activeWs === 0 && (
        <div style={{
          position: "absolute",
          top: 32,
          left: 46,
          right: 50,
          bottom: 32,
          zIndex: 40,
          overflow: "hidden",
        }}>
          <HomeDashboard />
        </div>
      )}

      {/* Wallpaper + back-to-portal labels (tiny, corner) — DARK MIRROR */}
      <div style={{
        position: "absolute",
        top: 36, left: 50,
        background: C.glassDark,
        backdropFilter: "blur(14px) saturate(1.1)",
        WebkitBackdropFilter: "blur(14px) saturate(1.1)",
        border: `1px solid ${C.hairline}`,
        color: C.textTertiary,
        fontSize: "0.5rem",
        padding: "3px 8px",
        letterSpacing: "0.18em",
        borderRadius: 6,
        fontFamily: '"JetBrains Mono", monospace',
        zIndex: 60,
      }}>
        WALLPAPER {String(wp.idx + 1).padStart(2, "0")}/15
      </div>
      <a
        href="#/"
        style={{
          position: "absolute",
          top: 36, right: 54,
          background: C.glassDark,
          backdropFilter: "blur(14px) saturate(1.1)",
          WebkitBackdropFilter: "blur(14px) saturate(1.1)",
          border: `1px solid ${C.hairline}`,
          color: C.textSecondary,
          fontSize: "0.55rem",
          padding: "3px 9px",
          textDecoration: "none",
          letterSpacing: "0.18em",
          borderRadius: 6,
          fontFamily: '"JetBrains Mono", monospace',
          zIndex: 60,
        }}
      >
        ◀ BACK TO PORTAL
      </a>

      {/* Flyouts */}
      <PanelFlyout open={showPanel} onClose={() => setShowPanel(false)} />
      <Notifications open={showNotif} onClose={() => setShowNotif(false)} />
      <StartMenu open={showStart} onClose={() => setShowStart(false)} onLaunch={(a) => setOpenApp(a)} />
      <SettingsWindow open={showSettings} onClose={() => setShowSettings(false)} />

      {/* App window */}
      {openApp && (
        <Window a={openApp} onClose={() => setOpenApp(null)}>
          {openApp.kind === "iframe" ? (
            <iframe
              title={openApp.name}
              src={openApp.src}
              style={{ width: "100%", height: "100%", border: "none", background: C.void }}
            />
          ) : (
            <MockupBody a={openApp} />
          )}
        </Window>
      )}
    </div>
  );
}
