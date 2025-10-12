import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5175,
    proxy: {
      '/api': {
        target: 'http://api:8003',  // Use Docker service name, not localhost
        changeOrigin: true,
        // Don't rewrite - keep /api prefix for the backend
      }
    }
  }
})
