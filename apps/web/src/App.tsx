import { Routes, Route } from 'react-router-dom'
import Inbox from './pages/Inbox'
import Tracker from './pages/Tracker'
import Settings from './pages/Settings'
import Nav from './components/Nav'
import Search from './pages/Search'

export default function App() {
  return (
    <div className="min-h-screen font-sans">
      <Nav />
      <div className="p-4 max-w-5xl mx-auto">
        <Routes>
          <Route path="/" element={<Inbox />} />
          <Route path="/search" element={<Search />} />
          <Route path="/tracker" element={<Tracker />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </div>
    </div>
  )
}
