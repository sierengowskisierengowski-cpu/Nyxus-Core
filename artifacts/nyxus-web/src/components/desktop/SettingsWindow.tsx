import { useState, useEffect, useCallback, type ReactNode, type CSSProperties } from "react";
import { C } from "./shared";

const STORAGE_KEY = "nyxus-settings-v2";

type Settings = {
  wallpaperRotation: boolean;
  wallpaperRotationSec: number;
  blurSize: number;
  blurPasses: number;
  blurBrightness: number;
  windowOpacityFocused: number;
  windowOpacityUnfocused: number;
  scale: number;
  refreshRate: number;
  volume: number;
  muted: boolean;
  micVolume: number;
  micMuted: boolean;
  defaultSink: string;
  powerProfile: "performance" | "balanced" | "power-saver";
  idleTimeoutMin: number;
  screensaverDelayMin: number;
  lidAction: "suspend" | "ignore" | "lock" | "shutdown";
  lowBatteryAt: number;
  wifiEnabled: boolean;
  bluetoothEnabled: boolean;
  vpnEnabled: boolean;
  ethernetPriority: boolean;
  keyboardLayout: string;
  repeatRate: number;
  repeatDelayMs: number;
  numlockOnBoot: boolean;
  mouseSensitivity: number;
  naturalScroll: boolean;
  tapToClick: boolean;
  middleClickPaste: boolean;
  dnd: boolean;
  notifPosition: "top-right" | "top-left" | "top-center" | "bottom-right" | "bottom-left";
  notifTimeoutSec: number;
  notifSounds: boolean;
  notifShowOnLock: boolean;
  hyprGapsIn: number;
  hyprGapsOut: number;
  hyprBorderSize: number;
  hyprAnimations: boolean;
  hyprSmartGaps: boolean;
  defaultBrowser: string;
  defaultTerminal: string;
  defaultEditor: string;
  newsSources: string[];
  newsRefreshMin: number;
  newsTickerEnabled: boolean;
  filterRules: string[];
  telemetry: boolean;
  locationServices: boolean;
  crashReports: boolean;
  autoUpdate: boolean;
  updateChannel: "stable" | "edge";
  username: string;
  hostname: string;
};

const DEFAULTS: Settings = {
  wallpaperRotation: true,
  wallpaperRotationSec: 15,
  blurSize: 14,
  blurPasses: 4,
  blurBrightness: 0.92,
  windowOpacityFocused: 0.92,
  windowOpacityUnfocused: 0.78,
  scale: 1.0,
  refreshRate: 144,
  volume: 0.62,
  muted: false,
  micVolume: 0.85,
  micMuted: true,
  defaultSink: "Built-in Audio",
  powerProfile: "balanced",
  idleTimeoutMin: 10,
  screensaverDelayMin: 5,
  lidAction: "suspend",
  lowBatteryAt: 15,
  wifiEnabled: true,
  bluetoothEnabled: false,
  vpnEnabled: false,
  ethernetPriority: true,
  keyboardLayout: "us",
  repeatRate: 25,
  repeatDelayMs: 600,
  numlockOnBoot: true,
  mouseSensitivity: 0.0,
  naturalScroll: false,
  tapToClick: true,
  middleClickPaste: true,
  dnd: false,
  notifPosition: "top-right",
  notifTimeoutSec: 6,
  notifSounds: true,
  notifShowOnLock: false,
  hyprGapsIn: 4,
  hyprGapsOut: 8,
  hyprBorderSize: 1,
  hyprAnimations: true,
  hyprSmartGaps: true,
  defaultBrowser: "firefox-developer-edition",
  defaultTerminal: "alacritty",
  defaultEditor: "nvim",
  newsSources: ["Hacker News", "Lobsters", "Phoronix"],
  newsRefreshMin: 5,
  newsTickerEnabled: true,
  filterRules: ["block-trackers", "block-ads", "strip-utm", "force-https"],
  telemetry: false,
  locationServices: false,
  crashReports: true,
  autoUpdate: true,
  updateChannel: "stable",
  username: "jsierengowski",
  hostname: "nyxus",
};

function useSettings() {
  const [s, setS] = useState<Settings>(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) return { ...DEFAULTS, ...JSON.parse(raw) };
    } catch {}
    return DEFAULTS;
  });
  useEffect(() => {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(s)); } catch {}
  }, [s]);
  const set = useCallback(<K extends keyof Settings>(k: K, v: Settings[K]) => {
    setS(prev => ({ ...prev, [k]: v }));
  }, []);
  const reset = useCallback(() => setS(DEFAULTS), []);
  return { s, set, reset };
}

export function SettingsWindow({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { s, set, reset } = useSettings();
  const [active, setActive] = useState("appearance");
  const [savedFlash, setSavedFlash] = useState(false);

  useEffect(() => {
    if (!open) return;
    setSavedFlash(true);
    const t = setTimeout(() => setSavedFlash(false), 600);
    return () => clearTimeout(t);
  }, [s, open]);

  if (!open) return null;

  const sections = [
    { id: "appearance",    label: "Appearance",    glyph: "◐" },
    { id: "display",       label: "Display",       glyph: "▭" },
    { id: "sound",         label: "Sound",         glyph: "♪" },
    { id: "power",         label: "Power",         glyph: "⏻" },
    { id: "network",       label: "Network",       glyph: "◍" },
    { id: "keyboard",      label: "Keyboard",      glyph: "⌨" },
    { id: "mouse",         label: "Mouse",         glyph: "◎" },
    { id: "notifications", label: "Notifications", glyph: "✉" },
    { id: "hyprland",      label: "Hyprland",      glyph: "▦" },
    { id: "apps",          label: "Apps",          glyph: "◧" },
    { id: "news",          label: "News",          glyph: "✑" },
    { id: "filters",       label: "Filters",       glyph: "⊘" },
    { id: "privacy",       label: "Privacy",       glyph: "◆" },
    { id: "updates",       label: "Updates",       glyph: "↻" },
    { id: "profile",       label: "Profile",       glyph: "✦" },
    { id: "cache",         label: "Cache",         glyph: "▣" },
    { id: "about",         label: "About",         glyph: "ⓘ" },
  ];
  const sec = sections.find(x => x.id === active)!;

  const renderBody = () => {
    switch (active) {
      case "appearance":
        return (
          <Stack>
            <ReadOnlyRow label="Theme" value="DARK MIRROR · rev r16 (locked)" />
            <Toggle label="Wallpaper rotation" value={s.wallpaperRotation} onChange={v => set("wallpaperRotation", v)} />
            <Slider label="Rotation interval" min={5} max={120} step={5} unit="s" value={s.wallpaperRotationSec} onChange={v => set("wallpaperRotationSec", v)} />
            <Slider label="Blur size" min={0} max={32} value={s.blurSize} onChange={v => set("blurSize", v)} />
            <Slider label="Blur passes" min={1} max={8} value={s.blurPasses} onChange={v => set("blurPasses", v)} />
            <Slider label="Blur brightness" min={0.5} max={1.5} step={0.01} value={s.blurBrightness} onChange={v => set("blurBrightness", v)} format={v => v.toFixed(2)} />
            <Slider label="Window opacity (focused)" min={0.3} max={1} step={0.01} value={s.windowOpacityFocused} onChange={v => set("windowOpacityFocused", v)} format={v => v.toFixed(2)} />
            <Slider label="Window opacity (unfocused)" min={0.3} max={1} step={0.01} value={s.windowOpacityUnfocused} onChange={v => set("windowOpacityUnfocused", v)} format={v => v.toFixed(2)} />
          </Stack>
        );
      case "display":
        return (
          <Stack>
            <ReadOnlyRow label="Primary monitor" value="DP-1 · 2560×1396 @ 144Hz" />
            <Slider label="Display scale" min={1} max={2} step={0.1} value={s.scale} onChange={v => set("scale", v)} format={v => `${v.toFixed(1)}x`} />
            <Select label="Refresh rate" value={String(s.refreshRate)} options={["60", "75", "120", "144", "165", "240"]} onChange={v => set("refreshRate", Number(v))} suffix="Hz" />
            <ReadOnlyRow label="Color profile" value="sRGB · gamma 2.2" />
          </Stack>
        );
      case "sound":
        return (
          <Stack>
            <Toggle label="Output muted" value={s.muted} onChange={v => set("muted", v)} />
            <Slider label="Output volume" min={0} max={1} step={0.01} value={s.volume} onChange={v => set("volume", v)} format={v => `${Math.round(v * 100)}%`} />
            <Toggle label="Microphone muted" value={s.micMuted} onChange={v => set("micMuted", v)} />
            <Slider label="Microphone level" min={0} max={1} step={0.01} value={s.micVolume} onChange={v => set("micVolume", v)} format={v => `${Math.round(v * 100)}%`} />
            <Select label="Default sink" value={s.defaultSink} options={["Built-in Audio", "USB Headset", "HDMI Output", "Bluetooth"]} onChange={v => set("defaultSink", v)} />
          </Stack>
        );
      case "power":
        return (
          <Stack>
            <Select label="Power profile" value={s.powerProfile} options={["performance", "balanced", "power-saver"]} onChange={v => set("powerProfile", v as Settings["powerProfile"])} />
            <Slider label="Idle timeout" min={1} max={60} unit="min" value={s.idleTimeoutMin} onChange={v => set("idleTimeoutMin", v)} />
            <Slider label="Screensaver delay" min={1} max={30} unit="min" value={s.screensaverDelayMin} onChange={v => set("screensaverDelayMin", v)} />
            <Select label="Lid close action" value={s.lidAction} options={["suspend", "lock", "ignore", "shutdown"]} onChange={v => set("lidAction", v as Settings["lidAction"])} />
            <Slider label="Low-battery alert" min={5} max={50} unit="%" value={s.lowBatteryAt} onChange={v => set("lowBatteryAt", v)} />
          </Stack>
        );
      case "network":
        return (
          <Stack>
            <Toggle label="Wi-Fi" value={s.wifiEnabled} onChange={v => set("wifiEnabled", v)} />
            <Toggle label="Bluetooth" value={s.bluetoothEnabled} onChange={v => set("bluetoothEnabled", v)} />
            <Toggle label="VPN" value={s.vpnEnabled} onChange={v => set("vpnEnabled", v)} />
            <Toggle label="Prefer ethernet over wi-fi" value={s.ethernetPriority} onChange={v => set("ethernetPriority", v)} />
            <ReadOnlyRow label="Hostname" value={`${s.hostname}.local`} />
          </Stack>
        );
      case "keyboard":
        return (
          <Stack>
            <Select label="Layout" value={s.keyboardLayout} options={["us", "us-intl", "uk", "de", "fr", "dvorak", "colemak"]} onChange={v => set("keyboardLayout", v)} />
            <Slider label="Repeat rate" min={5} max={50} unit="cps" value={s.repeatRate} onChange={v => set("repeatRate", v)} />
            <Slider label="Repeat delay" min={150} max={1500} step={50} unit="ms" value={s.repeatDelayMs} onChange={v => set("repeatDelayMs", v)} />
            <Toggle label="Numlock on boot" value={s.numlockOnBoot} onChange={v => set("numlockOnBoot", v)} />
          </Stack>
        );
      case "mouse":
        return (
          <Stack>
            <Slider label="Pointer sensitivity" min={-1} max={1} step={0.05} value={s.mouseSensitivity} onChange={v => set("mouseSensitivity", v)} format={v => v.toFixed(2)} />
            <Toggle label="Natural scroll" value={s.naturalScroll} onChange={v => set("naturalScroll", v)} />
            <Toggle label="Tap to click" value={s.tapToClick} onChange={v => set("tapToClick", v)} />
            <Toggle label="Middle-click paste" value={s.middleClickPaste} onChange={v => set("middleClickPaste", v)} />
          </Stack>
        );
      case "notifications":
        return (
          <Stack>
            <ReadOnlyRow label="Daemon" value="Dunst (system-wide)" />
            <Toggle label="Do not disturb" value={s.dnd} onChange={v => set("dnd", v)} />
            <Select label="Position" value={s.notifPosition} options={["top-right", "top-left", "top-center", "bottom-right", "bottom-left"]} onChange={v => set("notifPosition", v as Settings["notifPosition"])} />
            <Slider label="Default timeout" min={1} max={30} unit="s" value={s.notifTimeoutSec} onChange={v => set("notifTimeoutSec", v)} />
            <Toggle label="Sounds" value={s.notifSounds} onChange={v => set("notifSounds", v)} />
            <Toggle label="Show on lock screen" value={s.notifShowOnLock} onChange={v => set("notifShowOnLock", v)} />
          </Stack>
        );
      case "hyprland":
        return (
          <Stack>
            <Slider label="Gaps (inner)" min={0} max={20} value={s.hyprGapsIn} onChange={v => set("hyprGapsIn", v)} />
            <Slider label="Gaps (outer)" min={0} max={40} value={s.hyprGapsOut} onChange={v => set("hyprGapsOut", v)} />
            <Slider label="Border size" min={0} max={8} value={s.hyprBorderSize} onChange={v => set("hyprBorderSize", v)} />
            <Toggle label="Animations" value={s.hyprAnimations} onChange={v => set("hyprAnimations", v)} />
            <Toggle label="Smart gaps (no gaps with one window)" value={s.hyprSmartGaps} onChange={v => set("hyprSmartGaps", v)} />
            <ReadOnlyRow label="Active border" value="rim-light gradient (white → off-white → black)" />
          </Stack>
        );
      case "apps":
        return (
          <Stack>
            <TextInput label="Default browser" value={s.defaultBrowser} onChange={v => set("defaultBrowser", v)} />
            <TextInput label="Default terminal" value={s.defaultTerminal} onChange={v => set("defaultTerminal", v)} />
            <TextInput label="Default editor" value={s.defaultEditor} onChange={v => set("defaultEditor", v)} />
            <ReadOnlyRow label="Installed NYXUS apps" value="26 (3 live + 11 tarball + 12 system)" />
          </Stack>
        );
      case "news":
        return (
          <Stack>
            <Toggle label="News ticker" value={s.newsTickerEnabled} onChange={v => set("newsTickerEnabled", v)} />
            <Slider label="Refresh interval" min={1} max={60} unit="min" value={s.newsRefreshMin} onChange={v => set("newsRefreshMin", v)} />
            <ListEditor label="Sources" items={s.newsSources} onChange={v => set("newsSources", v)} placeholder="Add a feed name…" />
          </Stack>
        );
      case "filters":
        return (
          <Stack>
            <ListEditor label="Active rules" items={s.filterRules} onChange={v => set("filterRules", v)} placeholder="Add filter rule slug…" />
          </Stack>
        );
      case "privacy":
        return (
          <Stack>
            <Toggle label="Anonymous telemetry" value={s.telemetry} onChange={v => set("telemetry", v)} />
            <Toggle label="Location services" value={s.locationServices} onChange={v => set("locationServices", v)} />
            <Toggle label="Crash reports" value={s.crashReports} onChange={v => set("crashReports", v)} />
          </Stack>
        );
      case "updates":
        return (
          <Stack>
            <Toggle label="Automatic updates" value={s.autoUpdate} onChange={v => set("autoUpdate", v)} />
            <Select label="Update channel" value={s.updateChannel} options={["stable", "edge"]} onChange={v => set("updateChannel", v as Settings["updateChannel"])} />
            <ActionRow label="Check for updates" action="Check now" onClick={() => alert("nyxus-resync-all.sh\n→ would pull latest from nyxus-core.replit.app")} />
            <ReadOnlyRow label="Source" value="github.com/sierengowskisierengowski-cpu/Nyxus-Core" />
          </Stack>
        );
      case "profile":
        return (
          <Stack>
            <TextInput label="Username" value={s.username} onChange={v => set("username", v)} />
            <TextInput label="Hostname" value={s.hostname} onChange={v => set("hostname", v)} />
            <ReadOnlyRow label="OS" value="NYXUS · Arch + Hyprland" />
            <ReadOnlyRow label="ISO" value="nyx-2026.05.02-x86_64.iso" />
            <ReadOnlyRow label="License" value="NYX-J5W-2026-SIERENGOWSKI-LOCKED" />
          </Stack>
        );
      case "cache":
        return (
          <Stack>
            <ReadOnlyRow label="Settings store" value={`${STORAGE_KEY} · localStorage`} />
            <ReadOnlyRow label="Mirror cache" value="~/.cache/nyxus/" />
            <ActionRow label="Clear settings cache" action="Reset to defaults" onClick={() => { if (confirm("Reset every setting to its default value?")) reset(); }} />
            <ActionRow label="Clear localStorage" action="Purge" onClick={() => { if (confirm("Wipe ALL NYXUS web preview data?")) { localStorage.clear(); location.reload(); } }} />
          </Stack>
        );
      case "about":
        return (
          <Stack>
            <ReadOnlyRow label="NYXUS" value="rev r16 · DARK MIRROR (LOCKED)" />
            <ReadOnlyRow label="Apps" value="26 installed (3 live + 11 tarball + 12 system)" />
            <ReadOnlyRow label="Settings keys" value={`${Object.keys(s).length} wired in`} />
            <ReadOnlyRow label="Creator" value="Joseph Sierengowski" />
            <ReadOnlyRow label="Source" value="github.com/sierengowskisierengowski-cpu/Nyxus-Core" />
            <ReadOnlyRow label="Distribution" value="nyxus-core.replit.app" />
          </Stack>
        );
      default:
        return null;
    }
  };

  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed", inset: 0,
        background: "rgba(0,0,0,0.55)",
        backdropFilter: "blur(8px)",
        zIndex: 90,
        display: "flex", alignItems: "center", justifyContent: "center",
        padding: 50,
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          width: "100%", maxWidth: 860,
          height: "100%", maxHeight: 600,
          background: C.glassDark,
          backdropFilter: "blur(14px) saturate(1.1)",
          WebkitBackdropFilter: "blur(14px) saturate(1.1)",
          border: `1px solid ${C.hairline}`,
          borderRadius: 14,
          boxShadow: `0 20px 60px ${C.rimDark}`,
          display: "grid",
          gridTemplateColumns: "210px 1fr",
          fontFamily: '"Inter", sans-serif',
          overflow: "hidden",
        }}
      >
        <div style={{
          background: C.glassDeeper,
          borderRight: `1px solid ${C.hairline}`,
          padding: "0.9rem 0.55rem",
          display: "flex", flexDirection: "column", gap: 2,
          overflowY: "auto",
        }}>
          <div style={{
            fontSize: "0.55rem",
            color: C.textTertiary,
            letterSpacing: "0.22em",
            padding: "0.35rem 0.55rem",
            marginBottom: 6,
            fontFamily: '"JetBrains Mono", monospace',
          }}>SETTINGS</div>
          {sections.map(x => {
            const isActive = x.id === active;
            return (
              <button
                key={x.id}
                onClick={() => setActive(x.id)}
                style={{
                  width: "100%", textAlign: "left",
                  background: isActive ? C.glassDeepest : "transparent",
                  border: `1px solid ${isActive ? C.hairlineHi : "transparent"}`,
                  color: isActive ? C.white : C.textSecondary,
                  padding: "5px 10px",
                  borderRadius: 8,
                  fontSize: "0.72rem",
                  cursor: "pointer",
                  display: "flex", alignItems: "center", gap: 8,
                  fontFamily: '"Inter", sans-serif',
                  transition: "all 0.12s",
                }}
                onMouseEnter={e => { e.currentTarget.style.color = C.white; }}
                onMouseLeave={e => { e.currentTarget.style.color = isActive ? C.white : C.textSecondary; }}
              >
                <span style={{ width: 14, textAlign: "center" }}>{x.glyph}</span>
                {x.label}
              </button>
            );
          })}
          <div style={{ flex: 1, minHeight: 8 }} />
          <button onClick={onClose} style={{
            background: "transparent",
            border: `1px solid ${C.hairline}`,
            color: C.textSecondary,
            padding: "5px 10px",
            fontSize: "0.65rem",
            cursor: "pointer",
            borderRadius: 6,
            letterSpacing: "0.15em",
            fontFamily: '"JetBrains Mono", monospace',
          }}>✕ CLOSE</button>
        </div>

        <div style={{ padding: "1.4rem 1.6rem", overflowY: "auto" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
            <div>
              <div style={{
                fontSize: "0.55rem",
                color: C.textTertiary,
                letterSpacing: "0.22em",
                fontFamily: '"JetBrains Mono", monospace',
              }}>NYXUS · {sec.label.toUpperCase()}</div>
              <div style={{
                fontSize: "1.4rem",
                color: C.textPrimary,
                fontFamily: '"Architects Daughter", "Caveat", cursive',
                marginBottom: "1.2rem",
                marginTop: 2,
              }}>{sec.label}</div>
            </div>
            <div style={{
              fontSize: "0.55rem",
              color: savedFlash ? C.white : C.textTertiary,
              letterSpacing: "0.2em",
              fontFamily: '"JetBrains Mono", monospace',
              transition: "color 0.4s",
            }}>{savedFlash ? "● SAVED" : "○ AUTO-SAVE"}</div>
          </div>

          {renderBody()}
        </div>
      </div>
    </div>
  );
}

// ── primitives ───────────────────────────────────────────────────────────
function Stack({ children }: { children: ReactNode }) {
  return <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>{children}</div>;
}

const rowBase: CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  gap: 16,
  padding: "9px 12px",
  background: C.glassDeeper,
  border: `1px solid ${C.hairline}`,
  borderRadius: 10,
  fontSize: "0.75rem",
};
const labelStyle: CSSProperties = { color: C.textTertiary, letterSpacing: "0.04em", flex: 1 };

function ReadOnlyRow({ label, value }: { label: string; value: string }) {
  return (
    <div style={rowBase}>
      <span style={labelStyle}>{label}</span>
      <span style={{ color: C.textPrimary, textAlign: "right" }}>{value}</span>
    </div>
  );
}

function Toggle({ label, value, onChange }: { label: string; value: boolean; onChange: (v: boolean) => void }) {
  return (
    <div style={rowBase}>
      <span style={labelStyle}>{label}</span>
      <button
        onClick={() => onChange(!value)}
        aria-pressed={value}
        style={{
          width: 38, height: 20,
          borderRadius: 10,
          background: value ? "rgba(255,255,255,0.85)" : "rgba(255,255,255,0.10)",
          border: `1px solid ${value ? "rgba(255,255,255,0.95)" : C.hairline}`,
          position: "relative",
          cursor: "pointer",
          padding: 0,
          transition: "background 0.15s, border 0.15s",
        }}
      >
        <span style={{
          position: "absolute",
          top: 1, left: value ? 19 : 1,
          width: 16, height: 16,
          borderRadius: "50%",
          background: value ? "#0a0a0a" : C.textSecondary,
          transition: "left 0.15s, background 0.15s",
        }} />
      </button>
    </div>
  );
}

function Slider({ label, value, min, max, step = 1, unit, format, onChange }: {
  label: string; value: number; min: number; max: number; step?: number;
  unit?: string; format?: (v: number) => string; onChange: (v: number) => void;
}) {
  const display = format ? format(value) : `${value}${unit ? unit : ""}`;
  return (
    <div style={{ ...rowBase, flexDirection: "column", alignItems: "stretch", gap: 6, padding: "9px 12px 11px" }}>
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <span style={labelStyle}>{label}</span>
        <span style={{ color: C.textPrimary, fontFamily: '"JetBrains Mono", monospace', fontSize: "0.72rem" }}>{display}</span>
      </div>
      <input
        type="range"
        min={min} max={max} step={step} value={value}
        onChange={e => onChange(Number(e.target.value))}
        style={{ width: "100%", accentColor: C.white }}
      />
    </div>
  );
}

function Select({ label, value, options, onChange, suffix }: {
  label: string; value: string; options: string[]; onChange: (v: string) => void; suffix?: string;
}) {
  return (
    <div style={rowBase}>
      <span style={labelStyle}>{label}</span>
      <select
        value={value}
        onChange={e => onChange(e.target.value)}
        style={{
          background: C.glassDeepest,
          color: C.textPrimary,
          border: `1px solid ${C.hairline}`,
          borderRadius: 6,
          padding: "4px 8px",
          fontSize: "0.72rem",
          fontFamily: '"Inter", sans-serif',
          cursor: "pointer",
        }}
      >
        {options.map(o => <option key={o} value={o} style={{ background: "#0a0a0a" }}>{o}{suffix ? ` ${suffix}` : ""}</option>)}
      </select>
    </div>
  );
}

function TextInput({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <div style={rowBase}>
      <span style={labelStyle}>{label}</span>
      <input
        type="text"
        value={value}
        onChange={e => onChange(e.target.value)}
        style={{
          background: C.glassDeepest,
          color: C.textPrimary,
          border: `1px solid ${C.hairline}`,
          borderRadius: 6,
          padding: "4px 8px",
          fontSize: "0.72rem",
          fontFamily: '"JetBrains Mono", monospace',
          width: 220,
          outline: "none",
        }}
      />
    </div>
  );
}

function ActionRow({ label, action, onClick }: { label: string; action: string; onClick: () => void }) {
  return (
    <div style={rowBase}>
      <span style={labelStyle}>{label}</span>
      <button
        onClick={onClick}
        style={{
          background: "rgba(255,255,255,0.08)",
          color: C.textPrimary,
          border: `1px solid ${C.hairlineHi}`,
          borderRadius: 6,
          padding: "5px 12px",
          fontSize: "0.7rem",
          cursor: "pointer",
          fontFamily: '"Inter", sans-serif',
          letterSpacing: "0.04em",
        }}
        onMouseEnter={e => { e.currentTarget.style.background = "rgba(255,255,255,0.16)"; }}
        onMouseLeave={e => { e.currentTarget.style.background = "rgba(255,255,255,0.08)"; }}
      >{action}</button>
    </div>
  );
}

function ListEditor({ label, items, onChange, placeholder }: {
  label: string; items: string[]; onChange: (v: string[]) => void; placeholder?: string;
}) {
  const [draft, setDraft] = useState("");
  const add = () => {
    const t = draft.trim();
    if (!t || items.includes(t)) return;
    onChange([...items, t]);
    setDraft("");
  };
  const remove = (i: number) => onChange(items.filter((_, idx) => idx !== i));
  return (
    <div style={{ ...rowBase, flexDirection: "column", alignItems: "stretch", gap: 8 }}>
      <span style={labelStyle}>{label}</span>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
        {items.length === 0 && <span style={{ color: C.textTertiary, fontSize: "0.7rem" }}>(empty)</span>}
        {items.map((x, i) => (
          <span key={i} style={{
            display: "inline-flex", alignItems: "center", gap: 6,
            background: C.glassDeepest,
            border: `1px solid ${C.hairline}`,
            color: C.textPrimary,
            borderRadius: 6,
            padding: "3px 6px 3px 10px",
            fontSize: "0.7rem",
            fontFamily: '"JetBrains Mono", monospace',
          }}>
            {x}
            <button onClick={() => remove(i)} style={{
              background: "transparent",
              border: "none",
              color: C.textTertiary,
              cursor: "pointer",
              fontSize: "0.85rem",
              lineHeight: 1,
              padding: "0 2px",
            }}>×</button>
          </span>
        ))}
      </div>
      <div style={{ display: "flex", gap: 6 }}>
        <input
          type="text"
          value={draft}
          onChange={e => setDraft(e.target.value)}
          onKeyDown={e => { if (e.key === "Enter") add(); }}
          placeholder={placeholder}
          style={{
            flex: 1,
            background: C.glassDeepest,
            color: C.textPrimary,
            border: `1px solid ${C.hairline}`,
            borderRadius: 6,
            padding: "5px 8px",
            fontSize: "0.7rem",
            fontFamily: '"Inter", sans-serif',
            outline: "none",
          }}
        />
        <button onClick={add} style={{
          background: "rgba(255,255,255,0.08)",
          color: C.textPrimary,
          border: `1px solid ${C.hairlineHi}`,
          borderRadius: 6,
          padding: "5px 12px",
          fontSize: "0.7rem",
          cursor: "pointer",
          fontFamily: '"Inter", sans-serif',
        }}>+ Add</button>
      </div>
    </div>
  );
}
