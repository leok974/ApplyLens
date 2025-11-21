/**
 * Chat page - Conversational mailbox assistant
 */

import MailChat from '@/components/MailChat'
import { MailboxThemeProvider } from '@/themes/mailbox/context'
import { useMailboxTheme } from '@/hooks/useMailboxTheme'
import { cn } from '@/lib/utils'

function ChatPageInner() {
  const { themeId, theme } = useMailboxTheme()

  // Use theme frame tokens for clean canvas (no muddy overlays)
  const backdropStyle = theme.frame?.backdrop || 'bg-slate-950'
  const frameContainer = theme.frame?.container || ''
  const frameGlow = theme.frame?.glow || ''

  return (
    <div
      data-testid="chat-root"
      data-mailbox-theme={themeId}
      className={cn("relative min-h-[calc(100vh-64px)] overflow-hidden flex flex-col", backdropStyle)}
    >
      <div
        data-testid="mailbox-frame"
        className={cn("flex h-full flex-col", frameContainer, frameGlow)}
      >
        <MailChat />
      </div>
    </div>
  )
}

export default function ChatPage() {
  return (
    <MailboxThemeProvider>
      <ChatPageInner />
    </MailboxThemeProvider>
  )
}
