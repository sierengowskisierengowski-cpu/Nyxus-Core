import { contextBridge, ipcRenderer } from "electron";

// ─── Typed IPC bridge ─────────────────────────────────────────────────────────

const electronAPI = {
  // ── Platform ──────────────────────────────────────────────────────────────
  platform: process.platform as NodeJS.Platform,

  // ── Window ────────────────────────────────────────────────────────────────
  toggleWindow: () => ipcRenderer.invoke("window:toggle"),
  showWindow: () => ipcRenderer.invoke("window:show"),
  hideWindow: () => ipcRenderer.invoke("window:hide"),
  minimizeWindow: () => ipcRenderer.invoke("window:minimize"),
  setPinned: (pinned: boolean) => ipcRenderer.invoke("window:set-pin", pinned),
  setDismissOnBlur: (enabled: boolean) =>
    ipcRenderer.invoke("window:set-dismiss-on-blur", enabled),
  setStartMinimized: (enabled: boolean): Promise<{ success: boolean }> =>
    ipcRenderer.invoke("window:set-start-minimized", enabled),

  // ── Hotkey ────────────────────────────────────────────────────────────────
  updateHotkey: (accelerator: string): Promise<{ success: boolean }> =>
    ipcRenderer.invoke("hotkey:update", accelerator),

  // ── Auto-launch ───────────────────────────────────────────────────────────
  setAutoLaunch: (enabled: boolean): Promise<{ success: boolean; error?: string }> =>
    ipcRenderer.invoke("autolaunch:set", enabled),
  isAutoLaunchEnabled: (): Promise<boolean> =>
    ipcRenderer.invoke("autolaunch:is-enabled"),

  // ── App info ──────────────────────────────────────────────────────────────
  getConfig: () => ipcRenderer.invoke("app:get-config"),
  getVersion: (): Promise<string> => ipcRenderer.invoke("app:get-version"),
  getLocalToken: (): Promise<string> => ipcRenderer.invoke("app:get-local-token"),
  openExternal: (url: string) => ipcRenderer.invoke("app:open-external", url),
  showItemInFolder: (filePath: string) =>
    ipcRenderer.invoke("app:show-item-in-folder", filePath),

  // ── Native dialogs ────────────────────────────────────────────────────────
  openDirectoryDialog: (): Promise<string | null> =>
    ipcRenderer.invoke("dialog:open-directory"),

  // ── Event listeners ───────────────────────────────────────────────────────
  onHotkeyTriggered: (callback: () => void) => {
    const handler = () => callback();
    ipcRenderer.on("hotkey-triggered", handler);
    return () => ipcRenderer.removeListener("hotkey-triggered", handler);
  },

  onPinChanged: (callback: (pinned: boolean) => void) => {
    const handler = (_e: Electron.IpcRendererEvent, pinned: boolean) => callback(pinned);
    ipcRenderer.on("pin-changed", handler);
    return () => ipcRenderer.removeListener("pin-changed", handler);
  },

  onNavigate: (callback: (path: string) => void) => {
    const handler = (_e: Electron.IpcRendererEvent, p: string) => callback(p);
    ipcRenderer.on("navigate", handler);
    return () => ipcRenderer.removeListener("navigate", handler);
  },

  onTrayActivated: (callback: () => void) => {
    const handler = () => callback();
    ipcRenderer.on("tray-activated", handler);
    return () => ipcRenderer.removeListener("tray-activated", handler);
  },
};

contextBridge.exposeInMainWorld("electronAPI", electronAPI);

export type ElectronAPI = typeof electronAPI;
