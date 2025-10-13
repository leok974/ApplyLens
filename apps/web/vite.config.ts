import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// Check if we need a proxy (when API_BASE is not explicitly set or is relative)
const API_BASE = process.env.VITE_API_BASE
const needsProxy = !API_BASE || API_BASE.startsWith('/')

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5175,
    // Only use proxy if API_BASE is not set (for backward compatibility)
    // When VITE_API_BASE is set, the client calls it directly
    proxy: needsProxy ? {
      '/api': {
        target: 'http://localhost:8003',  // Default for local dev
        changeOrigin: true,
        secure: false,
      }
    } : undefined
  }
})
