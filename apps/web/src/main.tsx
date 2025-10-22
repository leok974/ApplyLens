import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import '@/styles/theme.css'
import '@/styles/dark-hotfix.css'
import App from './App'
import { ThemeProvider } from '@/components/theme/ThemeProvider'
import { initTheme } from './lib/theme'
import { installGlobalReloadGuard } from './lib/reload-guard'
// import { registerServiceWorker } from './lib/sw-register'

// Install reload guard to prevent infinite reload loops
installGlobalReloadGuard()

// Initialize theme based on saved preference or system setting
initTheme()

// Optionally register service worker (currently disabled)
// Uncomment when you have a sw.js file and want to enable offline support
// registerServiceWorker().catch(console.error)

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ThemeProvider>
      <BrowserRouter
        future={{
          v7_startTransition: true,
          v7_relativeSplatPath: true,
        }}
      >
        <App />
      </BrowserRouter>
    </ThemeProvider>
  </React.StrictMode>
)
