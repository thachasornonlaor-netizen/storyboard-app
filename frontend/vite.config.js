import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': {
        target: 'http://backend:3001',
        timeout: 300000
      },
      '/frames': {
        target: 'http://ai-service:8000',
        timeout: 300000
      }
    }
  }
})
