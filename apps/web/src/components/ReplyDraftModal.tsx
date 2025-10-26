import { useState } from 'react'
import { X, Copy, ExternalLink, Mail, CheckCircle, RefreshCw } from 'lucide-react'
import { DraftReplyResponse, draftReply } from '../lib/api'

interface ReplyDraftModalProps {
  draft: DraftReplyResponse
  onClose: () => void
  emailId: string
  account: string
  senderEmail?: string
  onOpenedInGmail?: () => void  // NEW: callback to log "sent" confirmation
}

export function ReplyDraftModal({ draft, onClose, emailId, account, senderEmail, onOpenedInGmail }: ReplyDraftModalProps) {
  const [editedDraft, setEditedDraft] = useState(draft.draft)
  const [copied, setCopied] = useState(false)
  const [regenerating, setRegenerating] = useState(false)
  const [currentTone, setCurrentTone] = useState<string | undefined>(undefined)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(editedDraft)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  const handleRegenerate = async (tone?: string) => {
    setRegenerating(true)
    setCurrentTone(tone)
    try {
      const newDraft = await draftReply({
        email_id: emailId,
        sender: draft.sender,
        subject: draft.subject,
        account: account,
        tone: tone as any,
      })
      setEditedDraft(newDraft.draft)
    } catch (err) {
      console.error('Failed to regenerate:', err)
    } finally {
      setRegenerating(false)
    }
  }

  const handleOpenGmail = () => {
    // Use sender_email from draft response or senderEmail prop, fallback to sender display name
    const recipientEmail = draft.sender_email || senderEmail || draft.sender

    // Auto-prefix "Re:" if not already present (prevents looking like cold outreach)
    const finalSubject = draft.subject?.toLowerCase().startsWith("re:")
      ? draft.subject
      : `Re: ${draft.subject || ""}`

    // Gmail compose URL with pre-filled fields
    const gmailUrl = `https://mail.google.com/mail/?view=cm&fs=1&to=${encodeURIComponent(recipientEmail)}&su=${encodeURIComponent(finalSubject)}&body=${encodeURIComponent(editedDraft)}`
    window.open(gmailUrl, '_blank', 'noopener,noreferrer')

    // NEW: let MailChat know we "sent" it
    if (onOpenedInGmail) {
      onOpenedInGmail()
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-2">
            <Mail className="w-5 h-5 text-blue-600" />
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Draft Reply
            </h2>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Email Details */}
        <div className="p-4 bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-500 dark:text-gray-400">To:</span>
              <span className="text-sm font-medium text-gray-900 dark:text-white">
                {draft.sender}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-500 dark:text-gray-400">Subject:</span>
              <span className="text-sm text-gray-900 dark:text-white">
                {draft.subject}
              </span>
            </div>
          </div>
        </div>

        {/* Draft Editor */}
        <div className="flex-1 overflow-auto p-4">
          {/* Tone adjustment buttons */}
          <div className="mb-3 flex items-center gap-2 flex-wrap">
            <span className="text-sm text-gray-600 dark:text-gray-400">Adjust tone:</span>
            <button
              onClick={() => handleRegenerate('warmer')}
              disabled={regenerating}
              className="inline-flex items-center gap-1 px-3 py-1 text-sm bg-blue-50 text-blue-700 rounded-full hover:bg-blue-100 disabled:opacity-50 disabled:cursor-not-allowed dark:bg-blue-900/30 dark:text-blue-300 dark:hover:bg-blue-900/50 transition-colors"
            >
              {regenerating && currentTone === 'warmer' && <RefreshCw className="h-3 w-3 animate-spin" />}
              Warmer
            </button>
            <button
              onClick={() => handleRegenerate('more_direct')}
              disabled={regenerating}
              className="inline-flex items-center gap-1 px-3 py-1 text-sm bg-purple-50 text-purple-700 rounded-full hover:bg-purple-100 disabled:opacity-50 disabled:cursor-not-allowed dark:bg-purple-900/30 dark:text-purple-300 dark:hover:bg-purple-900/50 transition-colors"
            >
              {regenerating && currentTone === 'more_direct' && <RefreshCw className="h-3 w-3 animate-spin" />}
              More Direct
            </button>
            <button
              onClick={() => handleRegenerate('formal')}
              disabled={regenerating}
              className="inline-flex items-center gap-1 px-3 py-1 text-sm bg-gray-50 text-gray-700 rounded-full hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600 transition-colors"
            >
              {regenerating && currentTone === 'formal' && <RefreshCw className="h-3 w-3 animate-spin" />}
              Formal
            </button>
            <button
              onClick={() => handleRegenerate('casual')}
              disabled={regenerating}
              className="inline-flex items-center gap-1 px-3 py-1 text-sm bg-green-50 text-green-700 rounded-full hover:bg-green-100 disabled:opacity-50 disabled:cursor-not-allowed dark:bg-green-900/30 dark:text-green-300 dark:hover:bg-green-900/50 transition-colors"
            >
              {regenerating && currentTone === 'casual' && <RefreshCw className="h-3 w-3 animate-spin" />}
              Casual
            </button>
          </div>

          <textarea
            value={editedDraft}
            onChange={(e) => setEditedDraft(e.target.value)}
            className="w-full h-full min-h-[200px] p-3 border border-gray-300 dark:border-gray-600 rounded-lg
                     focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none
                     bg-white dark:bg-gray-700 text-gray-900 dark:text-white
                     placeholder-gray-400 dark:placeholder-gray-500"
            placeholder="Your draft will appear here..."
          />

          {/* AI Badge */}
          <div className="mt-2 flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
            <span className="px-2 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-full">
              ✨ AI-Generated
            </span>
            <span>Feel free to edit before sending</span>
          </div>
        </div>

        {/* Actions */}
        <div className="p-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 flex gap-3">
          <button
            onClick={handleCopy}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2
                     border border-gray-300 dark:border-gray-600 rounded-lg
                     hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors
                     text-gray-700 dark:text-gray-300 font-medium"
          >
            {copied ? (
              <>
                <CheckCircle className="w-4 h-4 text-green-600" />
                <span>Copied!</span>
              </>
            ) : (
              <>
                <Copy className="w-4 h-4" />
                <span>Copy to Clipboard</span>
              </>
            )}
          </button>

          <button
            onClick={handleOpenGmail}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2
                     bg-blue-600 hover:bg-blue-700 text-white rounded-lg
                     transition-colors font-medium shadow-sm"
          >
            <ExternalLink className="w-4 h-4" />
            <span>Open in Gmail</span>
          </button>
        </div>

        {/* Help Text */}
        <div className="px-4 pb-3 text-xs text-gray-500 dark:text-gray-400 text-center">
          Tip: Click "Open in Gmail" to send this draft directly from your inbox
        </div>
      </div>
    </div>
  )
}
