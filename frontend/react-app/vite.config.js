import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  // Relative asset paths so the built index.html works when Electron loads it
  // as a file:// URL in production (absolute "/assets/..." would 404 there).
  base: './',
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
  },
})
