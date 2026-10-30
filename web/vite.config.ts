import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // The browser asks Vite's own origin, and Vite forwards the question to the
  // Python server, so the endpoint needs no CORS.
  server: { proxy: { '/ask': 'http://127.0.0.1:8000' } },
})
