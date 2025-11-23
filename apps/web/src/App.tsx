import { Routes, Route, Navigate } from 'react-router-dom'
import Inbox from './pages/Inbox'
import TrackerPage from './pages/TrackerPage'
import Applications from './pages/Applications'
import Settings from './pages/Settings'
import SettingsSecurity from './pages/SettingsSecurity'
import SettingsSendersPage from './pages/SettingsSendersPage'
import CompanionSettings from './pages/settings/CompanionSettings'
import ExtensionLanding from './pages/extension/ExtensionLanding'
import ExtensionSupport from './pages/extension/ExtensionSupport'
import ExtensionPrivacy from './pages/extension/ExtensionPrivacy'
import Landing from './pages/Landing'
import LoginGuard from './pages/LoginGuard'
import { AppShell } from './components/AppShell'
import Search from './pages/Search'
import InboxWithActions from './components/InboxWithActions'
import InboxPolished from './pages/InboxPolished'
import InboxPolishedDemo from './pages/InboxPolishedDemo'
import ChatPage from './pages/ChatPage'
import PolicyStudio from './pages/PolicyStudio'
import Today from './pages/Today'
import { ToastProvider } from './components/ui/use-toast'
import { Toaster } from './components/ui/sonner'
import { ProfileSummary } from './components/profile/ProfileSummary'
import { TooltipProvider } from '@/components/ui/tooltip'

export default function App() {
  return (
    <ToastProvider>
      <TooltipProvider delayDuration={100}>
        <div data-testid="app-root">
          <Routes>
            {/* Public landing page */}
            <Route path="/welcome" element={<Landing />} />

            {/* Public extension pages */}
            <Route path="/extension" element={<ExtensionLanding />} />
            <Route path="/extension/support" element={<ExtensionSupport />} />
            <Route path="/extension/privacy" element={<ExtensionPrivacy />} />

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
                  <Route path="/today" element={<Today />} />
                  <Route path="/tracker" element={<TrackerPage />} />
                  <Route path="/profile" element={<ProfileSummary />} />
                  <Route path="/applications" element={<Applications />} />
                  <Route path="/settings" element={<Settings />} />
                  <Route path="/settings/security" element={<SettingsSecurity />} />
                  <Route path="/settings/senders" element={<SettingsSendersPage />} />
                  <Route path="/settings/companion" element={<CompanionSettings />} />
                  <Route path="/policy-studio" element={<PolicyStudio />} />
                  <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
              </AppShell>
            </LoginGuard>
          } />
          </Routes>
          <Toaster />
        </div>
      </TooltipProvider>
    </ToastProvider>
  )
}
