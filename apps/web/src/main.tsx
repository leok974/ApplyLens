import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import '@/styles/theme.css'
import '@/styles/dark-hotfix.css'
import App from './App'
import { installGlobalReloadGuard } from './lib/reload-guard'
import { ensureCsrf } from './lib/csrf'
import { BUILD_META } from './buildMeta'
// import { registerServiceWorker } from './lib/sw-register'

// Version banner for debugging
console.info(
  "🔍 ApplyLens Web",
  `env=${BUILD_META.env}`,
  `flavor=${BUILD_META.flavor}`,
  `version=${BUILD_META.version}`,
  `sha=${BUILD_META.gitSha}`,
  `builtAt=${BUILD_META.builtAt || "unknown"}`,
  "\nFeatures:",
  "Theme-aware select fields for light/dark modes"
)

// Install reload guard to prevent infinite reload loops
installGlobalReloadGuard()

// Bootstrap CSRF token (fire-and-forget, don't block render)
ensureCsrf().catch(console.warn)

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
