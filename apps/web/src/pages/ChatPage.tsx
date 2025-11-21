/**
 * Chat page - Conversational mailbox assistant
 */

import MailChat from '@/components/MailChat'
import { MailboxThemeProvider } from '@/themes/mailbox/context'
import { useMailboxTheme } from '@/hooks/useMailboxTheme'

function ChatPageInner() {
  const { themeId } = useMailboxTheme()
  return (
    <div data-mailbox-theme={themeId}>
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
