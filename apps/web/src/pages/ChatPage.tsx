/**
 * Chat page - Conversational mailbox assistant
 */

import MailChat from '@/components/MailChat'
import { MailboxThemeProvider } from '@/themes/mailbox/context'

export default function ChatPage() {
  return (
    <MailboxThemeProvider>
      <MailChat />
    </MailboxThemeProvider>
  )
}
