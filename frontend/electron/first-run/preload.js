const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("firstRun", {
  saveApiKeys: (keys) => ipcRenderer.invoke("first-run:save-api-keys", keys),
});
