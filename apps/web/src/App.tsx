import { Routes, Route } from 'react-router-dom'
import Inbox from './pages/Inbox'
import Tracker from './pages/Tracker'
import Applications from './pages/Applications'
import Settings from './pages/Settings'
import Nav from './components/Nav'
import Search from './pages/Search'
import InboxWithActions from './components/InboxWithActions'
import InboxPolished from './pages/InboxPolished'
import InboxPolishedDemo from './pages/InboxPolishedDemo'
import { ToastProvider } from './components/ui/use-toast'

export default function App() {
  return (
    <ToastProvider>
      <div className="min-h-screen font-sans">
        <Nav />
        <div className="p-4 max-w-5xl mx-auto">
          <Routes>
            <Route path="/" element={<Inbox />} />
            <Route path="/inbox-polished" element={<InboxPolished />} />
            <Route path="/inbox-polished-demo" element={<InboxPolishedDemo />} />
            <Route path="/inbox-actions" element={<InboxWithActions />} />
            <Route path="/search" element={<Search />} />
            <Route path="/tracker" element={<Tracker />} />
            <Route path="/applications" element={<Applications />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </div>
      </div>
    </ToastProvider>
  )
}
