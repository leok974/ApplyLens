/**
 * Chat page - Conversational mailbox assistant
 */

import MailChat from '@/components/MailChat'
import { MailboxThemeProvider } from '@/themes/mailbox/context'
import { useMailboxTheme } from '@/hooks/useMailboxTheme'
import { cn } from '@/lib/utils'

function ChatPageInner() {
  const { themeId } = useMailboxTheme()

  // Banana Pro specific styling
  const isBananaPro = themeId === 'bananaPro'
  const canvasStyle = isBananaPro
    ? 'bg-slate-950 bg-gradient-to-b from-slate-950 via-slate-950 to-slate-950'
    : 'bg-slate-950'

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
