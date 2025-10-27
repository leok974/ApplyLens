import { Routes, Route, Navigate } from 'react-router-dom'
import Inbox from './pages/Inbox'
import TrackerPage from './pages/TrackerPage'
import Applications from './pages/Applications'
import Settings from './pages/Settings'
import SettingsSecurity from './pages/SettingsSecurity'
import SettingsSendersPage from './pages/SettingsSendersPage'
import Landing from './pages/Landing'
import LoginGuard from './pages/LoginGuard'
import { AppShell } from './components/AppShell'
import Search from './pages/Search'
import InboxWithActions from './components/InboxWithActions'
import InboxPolished from './pages/InboxPolished'
import InboxPolishedDemo from './pages/InboxPolishedDemo'
import ChatPage from './pages/ChatPage'
import PolicyStudio from './pages/PolicyStudio'
import { ToastProvider } from './components/ui/use-toast'
import { Toaster } from './components/ui/sonner'
import { ProfileSummary } from './components/profile/ProfileSummary'
import { TooltipProvider } from '@/components/ui/tooltip'

export default function App() {
  return (
    <ToastProvider>
      <TooltipProvider delayDuration={100}>
        <Routes>
          {/* Public landing page */}
          <Route path="/welcome" element={<Landing />} />

          {/* Protected routes */}
          <Route path="/*" element={
            <LoginGuard>
              <AppShell>
                <Routes>
                  <Route path="/" element={<Inbox />} />
                  <Route path="/inbox" element={<Inbox />} />
                  <Route path="/inbox-polished" element={<InboxPolished />} />
                  <Route path="/inbox-polished-demo" element={<InboxPolishedDemo />} />
                  <Route path="/inbox-actions" element={<InboxWithActions />} />
                  <Route path="/search" element={<Search />} />
                  <Route path="/chat" element={<ChatPage />} />
                  <Route path="/tracker" element={<TrackerPage />} />
                  <Route path="/profile" element={<ProfileSummary />} />
                  <Route path="/applications" element={<Applications />} />
                  <Route path="/settings" element={<Settings />} />
                  <Route path="/settings/security" element={<SettingsSecurity />} />
                  <Route path="/settings/senders" element={<SettingsSendersPage />} />
                  <Route path="/policy-studio" element={<PolicyStudio />} />
                  <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
              </AppShell>
            </LoginGuard>
          } />
        </Routes>
        <Toaster />
      </TooltipProvider>
    </ToastProvider>
  )
}
