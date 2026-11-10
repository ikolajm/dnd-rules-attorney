import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // The browser asks Vite's own origin, and Vite forwards the question to the
  // Python server, so the endpoint needs no CORS.
  server: {
    proxy: { '/ask': 'http://127.0.0.1:8000' },
    // The encyclopedia imports the data in ../data/, which the dev server
    // refuses outside its root. `allow` replaces the default list, so it covers
    // web/ too. The build does not read it.
    fs: { allow: ['..'] },
  },
})
