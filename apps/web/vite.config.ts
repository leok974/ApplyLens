import { defineConfig, Plugin } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// Check if we need a proxy (when API_BASE is not explicitly set or is relative)
const API_BASE = process.env.VITE_API_BASE
const needsProxy = !API_BASE || API_BASE.startsWith('/')
// Support ASSET_BASE for CDN, fallback to VITE_BASE_PATH or '/'
const ASSET_BASE = process.env.ASSET_BASE || process.env.VITE_BASE_PATH || '/'

// Generate build ID from timestamp
const BUILD_ID = process.env.BUILD_ID || ``

// Plugin to inject build ID into HTML
function buildIdPlugin(): Plugin {
  return {
    name: 'build-id-injector',
    transformIndexHtml(html) {
      return html.replace('__BUILD_ID__', BUILD_ID)
    }
  }
}

export default defineConfig({
  // Use ASSET_BASE for CDN support (e.g., https://cdn.applylens.app/)
  base: ASSET_BASE,
  plugins: [react(), buildIdPlugin()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  define: {
    '__BUILD_ID__': JSON.stringify(BUILD_ID),
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
        rewrite: (path) => path.replace(/^\/api/, ''),  // Strip /api prefix
      }
    } : undefined
  },
  build: {
    // Replace __BUILD_ID__ in HTML during build
    rollupOptions: {
      output: {
        // Add build ID to chunk names for cache busting
        chunkFileNames: `assets/[name]-.[hash].js`,
        entryFileNames: `assets/[name]-.[hash].js`,
        assetFileNames: `assets/[name]-.[hash].[ext]`,
      }
    }
  }
})
