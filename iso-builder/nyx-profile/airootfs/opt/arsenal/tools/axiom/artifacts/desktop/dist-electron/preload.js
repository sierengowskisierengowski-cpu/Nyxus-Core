"use strict";
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);

// electron/preload.ts
var preload_exports = {};
module.exports = __toCommonJS(preload_exports);
var import_electron = require("electron");
var electronAPI = {
  // ── Platform ──────────────────────────────────────────────────────────────
  platform: process.platform,
  // ── Window ────────────────────────────────────────────────────────────────
  toggleWindow: () => import_electron.ipcRenderer.invoke("window:toggle"),
  showWindow: () => import_electron.ipcRenderer.invoke("window:show"),
  hideWindow: () => import_electron.ipcRenderer.invoke("window:hide"),
  minimizeWindow: () => import_electron.ipcRenderer.invoke("window:minimize"),
  setPinned: (pinned) => import_electron.ipcRenderer.invoke("window:set-pin", pinned),
  setDismissOnBlur: (enabled) => import_electron.ipcRenderer.invoke("window:set-dismiss-on-blur", enabled),
  // ── Hotkey ────────────────────────────────────────────────────────────────
  updateHotkey: (accelerator) => import_electron.ipcRenderer.invoke("hotkey:update", accelerator),
  // ── Auto-launch ───────────────────────────────────────────────────────────
  setAutoLaunch: (enabled) => import_electron.ipcRenderer.invoke("autolaunch:set", enabled),
  isAutoLaunchEnabled: () => import_electron.ipcRenderer.invoke("autolaunch:is-enabled"),
  // ── App info ──────────────────────────────────────────────────────────────
  getConfig: () => import_electron.ipcRenderer.invoke("app:get-config"),
  getVersion: () => import_electron.ipcRenderer.invoke("app:get-version"),
  openExternal: (url) => import_electron.ipcRenderer.invoke("app:open-external", url),
  showItemInFolder: (filePath) => import_electron.ipcRenderer.invoke("app:show-item-in-folder", filePath),
  // ── Native dialogs ────────────────────────────────────────────────────────
  openDirectoryDialog: () => import_electron.ipcRenderer.invoke("dialog:open-directory"),
  // ── Event listeners ───────────────────────────────────────────────────────
  onHotkeyTriggered: (callback) => {
    const handler = () => callback();
    import_electron.ipcRenderer.on("hotkey-triggered", handler);
    return () => import_electron.ipcRenderer.removeListener("hotkey-triggered", handler);
  },
  onPinChanged: (callback) => {
    const handler = (_e, pinned) => callback(pinned);
    import_electron.ipcRenderer.on("pin-changed", handler);
    return () => import_electron.ipcRenderer.removeListener("pin-changed", handler);
  },
  onNavigate: (callback) => {
    const handler = (_e, p) => callback(p);
    import_electron.ipcRenderer.on("navigate", handler);
    return () => import_electron.ipcRenderer.removeListener("navigate", handler);
  },
  onTrayActivated: (callback) => {
    const handler = () => callback();
    import_electron.ipcRenderer.on("tray-activated", handler);
    return () => import_electron.ipcRenderer.removeListener("tray-activated", handler);
  }
};
import_electron.contextBridge.exposeInMainWorld("electronAPI", electronAPI);
//# sourceMappingURL=preload.js.map
