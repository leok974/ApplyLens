import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import '@/styles/theme.css'
import '@/styles/dark-hotfix.css'
import App from './App'
import { installGlobalReloadGuard } from './lib/reload-guard'
// import { registerServiceWorker } from './lib/sw-register'

// Version banner for debugging
console.info(
  '%c🔍 ApplyLens Web v0.4.59%c\n' +
  'Build: 2025-10-26\n' +
  'Features: Theme-aware pages and components',
  'color: #10b981; font-weight: bold; font-size: 14px;',
  'color: #6b7280; font-size: 11px;'
)

// Install reload guard to prevent infinite reload loops
installGlobalReloadGuard()

// Theme is now initialized by useTheme hook on first render
// (Keeping this for backwards compatibility during initial load)
const savedTheme = window.localStorage.getItem("applylens-theme")
if (savedTheme === "dark" || !savedTheme) {
  document.documentElement.classList.add("dark")
} else {
  document.documentElement.classList.remove("dark")
}

// Optionally register service worker (currently disabled)
// Uncomment when you have a sw.js file and want to enable offline support
// registerServiceWorker().catch(console.error)

// Determine basename from Vite's BASE_URL
const basename = import.meta.env.BASE_URL && import.meta.env.BASE_URL !== '/' ? import.meta.env.BASE_URL : ''

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter
      basename={basename}
      future={{
        v7_startTransition: true,
        v7_relativeSplatPath: true,
      }}
    >
      <App />
    </BrowserRouter>
  </React.StrictMode>
)
