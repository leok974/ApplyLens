import { Routes, Route } from 'react-router-dom'
import Inbox from './pages/Inbox'
import Tracker from './pages/Tracker'
import Applications from './pages/Applications'
import Settings from './pages/Settings'
import SettingsSecurity from './pages/SettingsSecurity'
import { AppHeader } from './components/AppHeader'
import Search from './pages/Search'
import InboxWithActions from './components/InboxWithActions'
import InboxPolished from './pages/InboxPolished'
import InboxPolishedDemo from './pages/InboxPolishedDemo'
import ChatPage from './pages/ChatPage'
import { ToastProvider } from './components/ui/use-toast'
import { Toaster } from './components/ui/sonner'
import { ProfileSummary } from './components/profile/ProfileSummary'

export default function App() {
  return (
    <ToastProvider>
      <div id="app-root" data-testid="app-root" className="min-h-screen bg-background text-foreground">
        <AppHeader />
        <main className="mx-auto max-w-6xl px-4 py-6">
          <Routes>
            <Route path="/" element={<Inbox />} />
            <Route path="/inbox-polished" element={<InboxPolished />} />
            <Route path="/inbox-polished-demo" element={<InboxPolishedDemo />} />
            <Route path="/inbox-actions" element={<InboxWithActions />} />
            <Route path="/search" element={<Search />} />
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/tracker" element={<Tracker />} />
            <Route path="/profile" element={<ProfileSummary />} />
            <Route path="/applications" element={<Applications />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/settings/security" element={<SettingsSecurity />} />
          </Routes>
        </main>
        <Toaster />
      </div>
    </ToastProvider>
  )
}
