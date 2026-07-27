const fs = require("fs");
const path = require("path");
const { spawn } = require("child_process");
const { app } = require("electron");
const { configDir } = require("./config-store");

let child = null;

function backendExePath() {
  return path.join(process.resourcesPath, "backend", "FloatNoteBackend.exe");
}

function isAvailable() {
  return fs.existsSync(backendExePath());
}

function start() {
  if (child || !isAvailable()) return;

  child = spawn(backendExePath(), [], {
    cwd: path.dirname(backendExePath()),
    env: { ...process.env, FLOATNOTE_CONFIG_DIR: configDir() },
    windowsHide: true,
  });

  child.stdout?.on("data", (data) => console.log(`[backend] ${data}`.trimEnd()));
  child.stderr?.on("data", (data) => console.error(`[backend] ${data}`.trimEnd()));
  child.on("exit", (code, signal) => {
    console.log(`[backend] exited (code=${code}, signal=${signal})`);
    child = null;
  });
}

function stop() {
  if (!child) return;
  child.kill();
  child = null;
}

app.on("will-quit", stop);

module.exports = { start, stop, isAvailable };
