const path = require("path");
const fs = require("fs");
const os = require("os");
const http = require("http");
const { spawn } = require("child_process");
const { app, BrowserWindow, ipcMain } = require("electron");

// Crash/step log to a stable file — Windows GUI apps have no console to read.
const LOG_FILE = path.join(os.tmpdir(), "floatnote-main.log");
function logMain(msg) {
  try {
    fs.appendFileSync(LOG_FILE, `[${new Date().toISOString()}] ${msg}\n`);
  } catch {
    /* ignore */
  }
}
process.on("uncaughtException", (e) => logMain("UNCAUGHT: " + (e && e.stack ? e.stack : e)));
process.on("unhandledRejection", (e) => logMain("UNHANDLED_REJECTION: " + (e && e.stack ? e.stack : e)));
logMain("main.js loaded; isPackaged=" + app.isPackaged);

const isDev = !app.isPackaged;
const DEV_SERVER_URL = "http://localhost:5173";
const BACKEND_URL = "http://127.0.0.1:8000";

let backendProcess = null;
let mainWindow = null;

// In the packaged app the onedir PyInstaller backend ships under
// resources/backend/floatnote-backend/. In dev the backend is started
// separately (run.ps1), so Electron does not spawn it.
function backendExePath() {
  return path.join(
    process.resourcesPath,
    "backend",
    "floatnote-backend",
    "floatnote-backend.exe"
  );
}

function startBackend() {
  if (isDev) {
    return; // dev backend runs from run.ps1 / `python main.py`
  }
  const exe = backendExePath();
  logMain("startBackend spawning: " + exe + " exists=" + fs.existsSync(exe));
  backendProcess = spawn(exe, [], {
    env: {
      ...process.env,
      // Where the backend reads config.json (the HF token) and caches models.
      FLOATNOTE_DATA_DIR: app.getPath("userData"),
      // Avoid the Windows console UnicodeEncodeError on the backend's emoji logs.
      PYTHONIOENCODING: "utf-8",
      PYTHONUTF8: "1",
      // Screen Reader (OCR) on by default in the shipped app, using the bundled
      // Tesseract engine so the user needs no separate install.
      ENABLE_OCR: "true",
      TESSERACT_CMD: path.join(process.resourcesPath, "tesseract", "tesseract.exe"),
      TESSDATA_PREFIX: path.join(process.resourcesPath, "tesseract", "tessdata"),
    },
    windowsHide: true,
  });
  backendProcess.stdout.on("data", (d) => console.log(`[backend] ${d}`));
  backendProcess.stderr.on("data", (d) => console.error(`[backend] ${d}`));
  // Without this handler a spawn failure ('error' event) would crash the main
  // process as an unhandled error.
  backendProcess.on("error", (err) => logMain("backend spawn error: " + err));
  backendProcess.on("exit", (code) => logMain("backend exited code=" + code));
}

function stopBackend() {
  if (backendProcess && !backendProcess.killed) {
    backendProcess.kill();
    backendProcess = null;
  }
}

// Poll the backend until it answers, so we don't show the UI before the
// server it depends on is ready.
function waitForBackend(callback, attempt = 0) {
  const maxAttempts = 90; // ~90s: first launch may download models
  const req = http.get(`${BACKEND_URL}/openapi.json`, (res) => {
    res.destroy();
    callback(true);
  });
  req.on("error", () => {
    if (attempt >= maxAttempts) {
      callback(false);
      return;
    }
    setTimeout(() => waitForBackend(callback, attempt + 1), 1000);
  });
}

function loadDevServer(win, attempt = 0) {
  const maxAttempts = 30;
  win.loadURL(DEV_SERVER_URL).catch(() => {
    if (attempt >= maxAttempts) {
      console.error(
        `Could not reach Vite dev server at ${DEV_SERVER_URL} after ${maxAttempts} attempts.`
      );
      return;
    }
    setTimeout(() => loadDevServer(win, attempt + 1), 1000);
  });
}

function loadApp(win) {
  // Packaged: electron-builder copies react-app/dist to resources/ui.
  // Unpackaged prod-mode run: fall back to the sibling react-app/dist.
  const packaged = path.join(process.resourcesPath, "ui", "index.html");
  const unpackaged = path.join(__dirname, "..", "react-app", "dist", "index.html");
  win.loadFile(app.isPackaged ? packaged : unpackaged);
}

// --- Config (HuggingFace token) stored in userData/config.json, the same
// directory passed to the backend as FLOATNOTE_DATA_DIR so it reads the token. ---
function configFilePath() {
  return path.join(app.getPath("userData"), "config.json");
}

function readConfig() {
  try {
    return JSON.parse(fs.readFileSync(configFilePath(), "utf-8"));
  } catch {
    return {};
  }
}

ipcMain.handle("floatnote:get-config", () => {
  const cfg = readConfig();
  // Never send the raw token to the renderer — just whether one is set.
  return { hasToken: Boolean(cfg.huggingface_token) };
});

ipcMain.handle("floatnote:save-token", (_event, token) => {
  const cfg = readConfig();
  cfg.huggingface_token = String(token || "").trim();
  fs.mkdirSync(app.getPath("userData"), { recursive: true });
  fs.writeFileSync(configFilePath(), JSON.stringify(cfg, null, 2), "utf-8");
  return { hasToken: Boolean(cfg.huggingface_token) };
});

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    transparent: false,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  // Content protection excludes this window from ALL screen capture — including
  // the OCR's own screen grab, so Screen Reader never reads FloatNote's own UI
  // back into the meeting (it still reads the rest of the screen: slides, etc.).
  // Side effect: the window can't be screenshotted while this is on. To capture
  // marketing screenshots, temporarily set this to false and relaunch.
  mainWindow.setContentProtection(true);

  if (isDev) {
    mainWindow.webContents.on("did-fail-load", () => loadDevServer(mainWindow));
    loadDevServer(mainWindow);
    return;
  }

  // Production: show a splash, wait for the spawned backend, then load the app.
  mainWindow.loadFile(path.join(__dirname, "splash.html"));
  waitForBackend((ready) => {
    if (!mainWindow) {
      return;
    }
    if (ready) {
      loadApp(mainWindow);
    } else {
      mainWindow.loadFile(path.join(__dirname, "backend-error.html"));
    }
  });
}

app.whenReady().then(() => {
  logMain("app ready");
  try {
    startBackend();
  } catch (e) {
    logMain("startBackend threw: " + (e && e.stack ? e.stack : e));
  }
  try {
    createWindow();
    logMain("createWindow returned");
  } catch (e) {
    logMain("createWindow threw: " + (e && e.stack ? e.stack : e));
  }
}).catch((e) => logMain("whenReady rejected: " + (e && e.stack ? e.stack : e)));

// Quit when all windows are closed (except macOS), and make sure the backend
// child process is shut down so nothing is left running.
app.on("window-all-closed", () => {
  stopBackend();
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("before-quit", stopBackend);

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});
