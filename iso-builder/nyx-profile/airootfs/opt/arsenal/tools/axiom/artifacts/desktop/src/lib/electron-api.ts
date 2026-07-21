/**
 * Typed bridge to the Electron preload API.
 * When running in a plain browser (Replit preview / web), all calls are no-ops
 * and `isElectron` is false, so the renderer degrades gracefully.
 */

export type ElectronPlatform = NodeJS.Platform;

interface IElectronAPI {
  platform: ElectronPlatform;
  toggleWindow: () => Promise<void>;
  showWindow: () => Promise<void>;
  hideWindow: () => Promise<void>;
  minimizeWindow: () => Promise<void>;
  setPinned: (pinned: boolean) => Promise<void>;
  setDismissOnBlur: (enabled: boolean) => Promise<void>;
  setStartMinimized: (enabled: boolean) => Promise<{ success: boolean }>;
  updateHotkey: (accelerator: string) => Promise<{ success: boolean }>;
  setAutoLaunch: (enabled: boolean) => Promise<{ success: boolean; error?: string }>;
  isAutoLaunchEnabled: () => Promise<boolean>;
  getConfig: () => Promise<Record<string, unknown>>;
  getVersion: () => Promise<string>;
  getLocalToken: () => Promise<string>;
  openExternal: (url: string) => Promise<void>;
  showItemInFolder: (filePath: string) => Promise<void>;
  openDirectoryDialog: () => Promise<string | null>;
  onHotkeyTriggered: (callback: () => void) => () => void;
  onPinChanged: (callback: (pinned: boolean) => void) => () => void;
  onNavigate: (callback: (path: string) => void) => () => void;
  onTrayActivated: (callback: () => void) => () => void;
}

declare global {
  interface Window {
    electronAPI?: IElectronAPI;
  }
}

/** True when the renderer is running inside the Electron shell. */
export const isElectron = typeof window !== "undefined" && !!window.electronAPI;

/** Access the native Electron API (undefined in browser context). */
export const electronAPI: IElectronAPI | undefined =
  typeof window !== "undefined" ? window.electronAPI : undefined;

/** No-op fallback for calls that are safe to skip in browser context. */
const noop = async () => {};
const noopBool = async () => false;
const noopStr = async () => "";
const noopNull = async () => null as string | null;
const noopObj = async () => ({}) as Record<string, unknown>;
const noopResult = async () => ({ success: false as const });
const unsubscribe = () => {};

/** Safe wrapper: calls Electron API if available, else falls back gracefully. */
export const electron = {
  platform: (electronAPI?.platform ?? "browser") as ElectronPlatform | "browser",
  toggleWindow: electronAPI?.toggleWindow ?? noop,
  showWindow: electronAPI?.showWindow ?? noop,
  hideWindow: electronAPI?.hideWindow ?? noop,
  minimizeWindow: electronAPI?.minimizeWindow ?? noop,
  setPinned: electronAPI?.setPinned ?? noop,
  setDismissOnBlur: electronAPI?.setDismissOnBlur ?? noop,
  setStartMinimized: electronAPI?.setStartMinimized ?? noopResult,
  updateHotkey: electronAPI?.updateHotkey ?? noopResult,
  setAutoLaunch: electronAPI?.setAutoLaunch ?? noopResult,
  isAutoLaunchEnabled: electronAPI?.isAutoLaunchEnabled ?? noopBool,
  getConfig: electronAPI?.getConfig ?? noopObj,
  getVersion: electronAPI?.getVersion ?? noopStr,
  getLocalToken: electronAPI?.getLocalToken ?? noopStr,
  openExternal: electronAPI?.openExternal ?? noop,
  showItemInFolder: electronAPI?.showItemInFolder ?? noop,
  openDirectoryDialog: electronAPI?.openDirectoryDialog ?? noopNull,
  onHotkeyTriggered: electronAPI?.onHotkeyTriggered ?? ((_cb: () => void) => unsubscribe),
  onPinChanged: electronAPI?.onPinChanged ?? ((_cb: (_: boolean) => void) => unsubscribe),
  onNavigate: electronAPI?.onNavigate ?? ((_cb: (_: string) => void) => unsubscribe),
  onTrayActivated: electronAPI?.onTrayActivated ?? ((_cb: () => void) => unsubscribe),
} satisfies Record<string, unknown>;
