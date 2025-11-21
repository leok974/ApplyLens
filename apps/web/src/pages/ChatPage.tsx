/**
 * Chat page - Conversational mailbox assistant
 */

import MailChat from '@/components/MailChat'
import { MailboxThemeProvider } from '@/themes/mailbox/context'
import { useMailboxTheme } from '@/hooks/useMailboxTheme'

function ChatPageInner() {
  const { themeId } = useMailboxTheme()
  return (
    <div data-testid="chat-root" data-mailbox-theme={themeId} className="flex h-full flex-col">
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
