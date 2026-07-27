const { contextBridge, ipcRenderer } = require("electron");

// Safe, minimal bridge exposed to the React app as window.floatnote.
// The renderer never touches the filesystem directly (contextIsolation stays
// on); it asks the main process to read/write the token in userData/config.json.
contextBridge.exposeInMainWorld("floatnote", {
  isDesktop: true,
  getConfig: () => ipcRenderer.invoke("floatnote:get-config"),
  saveToken: (token) => ipcRenderer.invoke("floatnote:save-token", token),
});
