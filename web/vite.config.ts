import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: { '/ask': 'http://127.0.0.1:8000' },
    // For ../data/. `allow` replaces the default list, so '..' has to cover web/ too.
    fs: { allow: ['..'] },
  },
})
