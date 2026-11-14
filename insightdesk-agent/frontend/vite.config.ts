import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The frontend calls /api/* and Vite forwards it to FastAPI, so there are no CORS issues in dev.
// In Docker, nginx does the same thing (see nginx.conf).
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: process.env.API_URL ?? 'http://localhost:8000',
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
