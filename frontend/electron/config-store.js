const fs = require("fs");
const path = require("path");
const { app } = require("electron");

const REQUIRED_KEYS = ["GROQ_API_KEY", "HUGGINGFACEHUB_API_TOKEN", "GEMINI_API_KEY"];

function configDir() {
  return app.getPath("userData");
}

function configPath() {
  return path.join(configDir(), ".env");
}

function readConfig() {
  const file = configPath();
  if (!fs.existsSync(file)) return {};
  const values = {};
  for (const line of fs.readFileSync(file, "utf-8").split(/\r?\n/)) {
    const match = /^([A-Z0-9_]+)=(.*)$/.exec(line.trim());
    if (match) values[match[1]] = match[2];
  }
  return values;
}

function isConfigured() {
  const values = readConfig();
  return REQUIRED_KEYS.every((key) => (values[key] || "").trim().length > 0);
}

function writeConfig(values) {
  fs.mkdirSync(configDir(), { recursive: true });
  const merged = { ...readConfig(), ...values };
  const body = Object.entries(merged)
    .filter(([, value]) => (value || "").length > 0)
    .map(([key, value]) => `${key}=${value}`)
    .join("\n");
  fs.writeFileSync(configPath(), body + "\n", "utf-8");
}

module.exports = { REQUIRED_KEYS, configDir, configPath, readConfig, isConfigured, writeConfig };
