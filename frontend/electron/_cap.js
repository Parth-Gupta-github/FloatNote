const { app, BrowserWindow } = require("electron");
const fs = require("fs");
const path = require("path");

// argv: SVG_FULL_PATH OUT_PNG_PATH [W] [H] [BG]
const [svgPath, outPath, W, H, BG] = process.argv.slice(2);
const w = parseInt(W || "512", 10), h = parseInt(H || "512", 10);
const bg = BG || "#e9ecf4";

app.disableHardwareAcceleration();

app.whenReady().then(() => {
  const svg = fs.readFileSync(svgPath, "utf8");
  const html =
    `<!doctype html><meta charset="utf8">` +
    `<style>html,body{margin:0;padding:0}` +
    `#w{width:${w}px;height:${h}px;background:${bg};` +
    `display:flex;align-items:center;justify-content:center;overflow:hidden}` +
    `#w svg{width:${w}px;height:${h}px;display:block}</style>` +
    `<div id="w">${svg}</div>`;
  const win = new BrowserWindow({
    width: w, height: h, x: 60, y: 60,
    show: true, frame: false, useContentSize: true, backgroundColor: bg,
  });
  win.webContents.once("did-finish-load", async () => {
    await new Promise((r) => setTimeout(r, 700));
    const img = await win.capturePage();
    fs.writeFileSync(outPath, img.toPNG());
    app.quit();
  });
  win.loadURL("data:text/html;charset=utf-8," + encodeURIComponent(html));
});
