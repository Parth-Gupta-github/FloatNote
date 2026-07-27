const path = require("path");
const { app, BrowserWindow, ipcMain } = require("electron");
const configStore = require("./config-store");
const backendProcess = require("./backend-process");

app.setName("FloatNote");

const DEV_SERVER_URL = "http://localhost:5173";
const isDev = !app.isPackaged;

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

function createMainWindow() {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    // alwaysOnTop: true,
    // frame: false,
    transparent: false,
    // skipTaskbar: true,
  });

  win.setContentProtection(true);

  if (isDev) {
    // Retry on load failures too (e.g. dev server restart).
    win.webContents.on("did-fail-load", () => loadDevServer(win));
    loadDevServer(win);
  } else {
    backendProcess.start();
    const reactIndexPath = app.isPackaged
      ? path.join(process.resourcesPath, "react-app", "dist", "index.html")
      : path.join(__dirname, "..", "react-app", "dist", "index.html");
    win.loadFile(reactIndexPath);
  }
}

function createFirstRunWindow() {
  return new Promise((resolve) => {
    const win = new BrowserWindow({
      width: 480,
      height: 560,
      resizable: false,
      autoHideMenuBar: true,
      webPreferences: {
        preload: path.join(__dirname, "first-run", "preload.js"),
      },
    });

    ipcMain.handleOnce("first-run:save-api-keys", (_event, keys) => {
      configStore.writeConfig(keys);
      win.close();
    });

    win.on("closed", resolve);
    win.loadFile(path.join(__dirname, "first-run", "index.html"));
  });
}

app.whenReady().then(async () => {
  if (!isDev && !configStore.isConfigured()) {
    await createFirstRunWindow();
  }
  createMainWindow();
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
