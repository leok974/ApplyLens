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
  const canvasStyle = theme.frame?.canvas || 'bg-slate-950'

  return (
    <div
      data-testid="chat-root"
      data-mailbox-theme={themeId}
      className={cn("flex h-full flex-col", canvasStyle)}
    >
      <MailChat />
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
