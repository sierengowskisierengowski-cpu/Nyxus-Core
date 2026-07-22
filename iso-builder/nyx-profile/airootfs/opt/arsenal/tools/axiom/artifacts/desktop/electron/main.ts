import {
  app,
  BrowserWindow,
  Tray,
  Menu,
  globalShortcut,
  ipcMain,
  screen,
  nativeImage,
  shell,
  dialog,
} from "electron";
import path from "path";
import fs from "fs";
import { spawn, ChildProcess } from "child_process";
import AutoLaunch from "auto-launch";
import log from "electron-log";

// ─── Constants ───────────────────────────────────────────────────────────────

const isDev = process.env.NODE_ENV === "development" || !app.isPackaged;
const DEV_RENDERER_URL = "http://localhost:21098";
const CONFIG_PATH = path.join(app.getPath("userData"), "axiom-config.json");

// Random token generated once per Electron session. Passed to the spawned API
// server and sent with every renderer request so the API refuses calls from
// any other process on the machine.
import { randomUUID } from "node:crypto";
const LOCAL_SESSION_TOKEN = randomUUID();
const ICON_PATH = path.join(__dirname, "..", "icons", "tray-icon.png");

// ─── Types ────────────────────────────────────────────────────────────────────

interface WindowConfig {
  x?: number;
  y?: number;
  width: number;
  height: number;
  pinned: boolean;
  hotkey: string;
  launchAtLogin: boolean;
  startMinimized: boolean;
  dismissOnBlur: boolean;
}

const DEFAULT_CONFIG: WindowConfig = {
  width: 1200,
  height: 750,
  pinned: false,
  hotkey: "CommandOrControl+Shift+Space",
  launchAtLogin: false,
  startMinimized: false,
  dismissOnBlur: false,
};

// ─── Config persistence ───────────────────────────────────────────────────────

function loadConfig(): WindowConfig {
  try {
    if (fs.existsSync(CONFIG_PATH)) {
      const raw = fs.readFileSync(CONFIG_PATH, "utf-8");
      return { ...DEFAULT_CONFIG, ...JSON.parse(raw) };
    }
  } catch (e) {
    log.warn("Failed to load config, using defaults:", e);
  }
  return { ...DEFAULT_CONFIG };
}

function saveConfig(config: Partial<WindowConfig>): void {
  const current = loadConfig();
  try {
    fs.writeFileSync(CONFIG_PATH, JSON.stringify({ ...current, ...config }, null, 2));
  } catch (e) {
    log.error("Failed to save config:", e);
  }
}

// ─── State ────────────────────────────────────────────────────────────────────

let mainWindow: BrowserWindow | null = null;
let tray: Tray | null = null;
let config: WindowConfig = loadConfig();
let isQuitting = false;
let apiServerProcess: ChildProcess | null = null;

const autoLauncher = new AutoLaunch({
  name: "AXIOM",
  isHidden: true,
});

// ─── API Server (production only) ─────────────────────────────────────────────

function startApiServer(): void {
  if (isDev) return;
  const serverPath = path.join(process.resourcesPath, "api-server", "dist", "index.mjs");
  if (!fs.existsSync(serverPath)) {
    log.warn("API server binary not found at:", serverPath);
    return;
  }
  const axiomDbPath = path.join(app.getPath("userData"), "axiom.db");
  // NODE_PATH lets the externalized better-sqlite3 (and any other non-bundled
  // native modules) be resolved from the packaged resources directory.
  const nodeModulesPath = path.join(process.resourcesPath, "api-server", "node_modules");
  apiServerProcess = spawn(process.execPath, [serverPath], {
    env: {
      ...process.env,
      NODE_ENV: "production",
      PORT: "8080",
      AXIOM_DB_PATH: axiomDbPath,
      NODE_PATH: nodeModulesPath,
      AXIOM_LOCAL_TOKEN: LOCAL_SESSION_TOKEN,
      AXIOM_API_HOST: "127.0.0.1",
    },
    detached: false,
    stdio: ["ignore", "pipe", "pipe"],
  });
  apiServerProcess.stdout?.on("data", (d) => log.info("[api]", d.toString().trim()));
  apiServerProcess.stderr?.on("data", (d) => log.warn("[api]", d.toString().trim()));
  apiServerProcess.on("exit", (code) => {
    log.info(`API server exited with code ${code}`);
    apiServerProcess = null;
  });
}

// ─── Window ───────────────────────────────────────────────────────────────────

function createWindow(): BrowserWindow {
  const display = screen.getPrimaryDisplay();
  const { width: dw, height: dh } = display.workAreaSize;

  const x = config.x ?? Math.round((dw - config.width) / 2);
  const y = config.y ?? Math.round((dh - config.height) / 2);

  const win = new BrowserWindow({
    x,
    y,
    width: config.width,
    height: config.height,
    minWidth: 800,
    minHeight: 600,
    frame: false,
    transparent: true,
    vibrancy: "under-window",
    visualEffectState: "followWindow",
    titleBarStyle: "hidden",
    trafficLightPosition: { x: 14, y: 14 },
    show: false,
    alwaysOnTop: config.pinned,
    hasShadow: true,
    roundedCorners: true,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
      webSecurity: true,
    },
  });

  if (isDev) {
    win.loadURL(DEV_RENDERER_URL);
    win.webContents.openDevTools({ mode: "detach" });
  } else {
    win.loadFile(path.join(__dirname, "..", "dist", "public", "index.html"));
  }

  win.once("ready-to-show", () => {
    if (!config.startMinimized) {
      win.show();
      win.focus();
    }
  });

  win.on("resize", () => {
    const [w, h] = win.getSize();
    saveConfig({ width: w, height: h });
  });

  win.on("moved", () => {
    const [px, py] = win.getPosition();
    saveConfig({ x: px, y: py });
  });

  win.on("blur", () => {
    if (config.dismissOnBlur && !config.pinned && !isQuitting) {
      win.hide();
    }
  });

  win.on("close", (e) => {
    if (!isQuitting) {
      e.preventDefault();
      win.hide();
    }
  });

  return win;
}

// ─── Tray ─────────────────────────────────────────────────────────────────────

function createTray(win: BrowserWindow): Tray {
  const iconExists = fs.existsSync(ICON_PATH);
  const icon = iconExists
    ? nativeImage.createFromPath(ICON_PATH).resize({ width: 16, height: 16 })
    : nativeImage.createEmpty();

  const t = new Tray(icon);
  t.setToolTip("AXIOM — AI Assistant");

  const buildMenu = () =>
    Menu.buildFromTemplate([
      {
        label: win.isVisible() ? "Hide AXIOM" : "Show AXIOM",
        click: () => toggleWindow(win),
      },
      { type: "separator" },
      {
        label: "Open Settings",
        click: () => {
          showWindow(win);
          win.webContents.send("navigate", "/settings");
        },
      },
      { type: "separator" },
      {
        label: "Quit AXIOM",
        accelerator: "CommandOrControl+Q",
        click: () => {
          isQuitting = true;
          app.quit();
        },
      },
    ]);

  t.on("double-click", () => toggleWindow(win));
  t.on("click", () => toggleWindow(win));
  t.on("right-click", () => t.popUpContextMenu(buildMenu()));

  // Update menu on visibility change so label stays current
  win.on("show", () => t.setContextMenu(buildMenu()));
  win.on("hide", () => t.setContextMenu(buildMenu()));
  t.setContextMenu(buildMenu());

  return t;
}

// ─── Window helpers ───────────────────────────────────────────────────────────

function showWindow(win: BrowserWindow): void {
  if (win.isMinimized()) win.restore();
  win.show();
  win.focus();
}

function toggleWindow(win: BrowserWindow): void {
  if (win.isVisible() && win.isFocused()) {
    win.hide();
  } else {
    showWindow(win);
  }
}

// ─── Global hotkey ───────────────────────────────────────────────────────────

function registerHotkey(accelerator: string, win: BrowserWindow): boolean {
  globalShortcut.unregisterAll();
  try {
    const ok = globalShortcut.register(accelerator, () => {
      toggleWindow(win);
      win.webContents.send("hotkey-triggered");
    });
    if (!ok) log.warn("Hotkey registration failed:", accelerator);
    return ok;
  } catch (e) {
    log.error("Hotkey error:", e);
    return false;
  }
}

// ─── IPC handlers ────────────────────────────────────────────────────────────

function setupIpc(win: BrowserWindow): void {
  ipcMain.handle("window:toggle", () => toggleWindow(win));
  ipcMain.handle("window:show", () => showWindow(win));
  ipcMain.handle("window:hide", () => win.hide());
  ipcMain.handle("window:minimize", () => win.minimize());

  ipcMain.handle("window:set-pin", (_e, pinned: boolean) => {
    config.pinned = pinned;
    win.setAlwaysOnTop(pinned, "floating");
    saveConfig({ pinned });
    win.webContents.send("pin-changed", pinned);
  });

  ipcMain.handle("window:set-dismiss-on-blur", (_e, enabled: boolean) => {
    config.dismissOnBlur = enabled;
    saveConfig({ dismissOnBlur: enabled });
  });

  ipcMain.handle("window:set-start-minimized", (_e, enabled: boolean) => {
    config.startMinimized = enabled;
    saveConfig({ startMinimized: enabled });
    return { success: true };
  });

  ipcMain.handle("hotkey:update", (_e, accelerator: string) => {
    const ok = registerHotkey(accelerator, win);
    if (ok) {
      config.hotkey = accelerator;
      saveConfig({ hotkey: accelerator });
    }
    return { success: ok };
  });

  ipcMain.handle("autolaunch:set", async (_e, enabled: boolean) => {
    try {
      if (enabled) {
        await autoLauncher.enable();
      } else {
        await autoLauncher.disable();
      }
      config.launchAtLogin = enabled;
      saveConfig({ launchAtLogin: enabled });
      return { success: true };
    } catch (e) {
      log.error("AutoLaunch error:", e);
      return { success: false, error: String(e) };
    }
  });

  ipcMain.handle("autolaunch:is-enabled", async () => {
    try {
      return await autoLauncher.isEnabled();
    } catch {
      return false;
    }
  });

  ipcMain.handle("app:get-config", () => loadConfig());

  ipcMain.handle("app:get-version", () => app.getVersion());

  ipcMain.handle("app:get-local-token", () => LOCAL_SESSION_TOKEN);

  ipcMain.handle("app:open-external", (_e, url: string) => {
    shell.openExternal(url);
  });

  ipcMain.handle("app:show-item-in-folder", (_e, filePath: string) => {
    shell.showItemInFolder(filePath);
  });

  ipcMain.handle("dialog:open-directory", async () => {
    const result = await dialog.showOpenDialog(win, {
      properties: ["openDirectory", "createDirectory"],
      title: "Select an allowed directory for AXIOM",
    });
    return result.canceled ? null : result.filePaths[0];
  });

  ipcMain.handle("platform:get", () => process.platform);
}

// ─── App lifecycle ────────────────────────────────────────────────────────────

app.whenReady().then(() => {
  log.info("AXIOM starting…");

  startApiServer();

  mainWindow = createWindow();
  tray = createTray(mainWindow);
  setupIpc(mainWindow);
  registerHotkey(config.hotkey, mainWindow);

  app.on("activate", () => {
    if (mainWindow) showWindow(mainWindow);
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("before-quit", () => {
  isQuitting = true;
  globalShortcut.unregisterAll();
  if (apiServerProcess) {
    apiServerProcess.kill("SIGTERM");
    apiServerProcess = null;
  }
});

app.on("will-quit", () => {
  globalShortcut.unregisterAll();
});

// Prevent multiple instances
const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
} else {
  app.on("second-instance", () => {
    if (mainWindow) showWindow(mainWindow);
  });
}
