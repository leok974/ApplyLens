/**
 * API Base URL Configuration
 * 
 * This module provides the base URL for API calls, configured via environment variables.
 * 
 * Environment Configurations:
 * - Local dev (.env.local): VITE_API_BASE=http://localhost:8003
 * - Docker (.env.docker): VITE_API_BASE=http://api:8003
 * - Fallback: '/api' (uses Vite proxy)
 * 
 * Usage:
 * import { API_BASE } from '@/lib/apiBase'
 * const response = await fetch(`${API_BASE}/actions/tray`)
 */

export const API_BASE = import.meta.env.VITE_API_BASE ?? '/api'

// Log configuration in development
if (import.meta.env.DEV) {
  console.log('[API Config] Base URL:', API_BASE)
}
