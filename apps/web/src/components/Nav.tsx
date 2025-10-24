import { Link, useLocation } from 'react-router-dom'
import ThemeToggle from './ThemeToggle'

export default function Nav() {
  const { pathname } = useLocation()
  const link = (to: string, label: string) => (
    <Link to={to} style={{
      padding: '8px 12px',
      borderRadius: 8,
      textDecoration: 'none',
      background: pathname === to ? '#111' : '#eee',
      color: pathname === to ? '#fff' : '#111',
      marginRight: 8
    }}>{label}</Link>
  )
  return (
    <nav style={{ padding: 12, borderBottom: '1px solid #ddd', display: 'flex', alignItems: 'center' }}>
      <div style={{ flex: 1 }}>
        {link('/', 'Inbox')}
        {link('/inbox-actions', 'Actions')}
        {link('/search', 'Search')}
        {link('/tracker', 'Tracker')}
        {link('/settings', 'Settings')}
      </div>
      <ThemeToggle />
    </nav>
  )
}
