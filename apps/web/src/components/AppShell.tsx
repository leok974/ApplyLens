import { ReactNode } from 'react'
import { AppHeader } from './AppHeader'

interface AppShellProps {
  children: ReactNode
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="min-h-screen bg-zinc-100 text-zinc-900 dark:bg-[#0f172a] dark:text-zinc-100">
      <AppHeader />
      <main className="px-4 py-4 md:px-6 md:py-6">
        <div className="mx-auto max-w-7xl space-y-4">
          {children}
        </div>
      </main>
    </div>
  )
}
