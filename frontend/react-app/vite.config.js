import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  // Emit relative asset paths ("./assets/...") so the built index.html works
  // when Electron loads it from disk via file:// in the packaged app.
  // Without this, Vite uses absolute "/assets/..." paths that resolve to the
  // filesystem root under file:// and leave the window blank white.
  base: './',
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
  },
})
