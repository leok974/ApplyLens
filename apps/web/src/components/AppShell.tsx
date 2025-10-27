import { ReactNode } from 'react'
import { AppHeader } from './AppHeader'

interface AppShellProps {
  children: ReactNode
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="min-h-screen bg-zinc-100 dark:bg-[#0f172a]">
      <AppHeader />
      <main>{children}</main>
    </div>
  )
}
