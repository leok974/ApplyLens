import { useEffect, useState } from 'react'
import { getGmailStatus, getGmailInbox, initiateGmailAuth, Email, GmailConnectionStatus } from '../lib/api'
import EmailCard from '../components/EmailCard'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { CheckCircle, AlertCircle } from 'lucide-react'

const LABEL_FILTERS = [
  { value: '', label: 'All' },
  { value: 'interview', label: '📅 Interview' },
  { value: 'offer', label: '🎉 Offer' },
  { value: 'rejection', label: '❌ Rejection' },
  { value: 'application_receipt', label: '✅ Application Receipt' },
  { value: 'newsletter_ads', label: '📰 Newsletter/Ads' },
]

export default function Inbox() {
  const [status, setStatus] = useState<GmailConnectionStatus | null>(null)
  const [emails, setEmails] = useState<Email[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [labelFilter, setLabelFilter] = useState('')
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  // Check connection status on mount
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    if (params.get('connected') === 'google') {
      // Just connected, show success
      setErr('✅ Successfully connected to Gmail! Click "Sync Emails" to fetch your messages.')
      setTimeout(() => setErr(null), 5000)
    }

    getGmailStatus()
      .then(setStatus)
      .catch(e => console.error('Status check failed:', e))
  }, [])

  // Fetch emails when filter or page changes
  useEffect(() => {
    if (!status?.connected) return

    setLoading(true)
    getGmailInbox(page, 50, labelFilter || undefined, status.user_email)
      .then(resp => {
        setEmails(resp.emails)
        setTotal(resp.total)
      })
      .catch(e => setErr(String(e)))
      .finally(() => setLoading(false))
  }, [status, page, labelFilter])

  // Note: Sync buttons are now in AppHeader component
  // TODO: Wire up sync functionality through context or props if needed

  if (!status) {
    return <div className="p-4">Loading Gmail status...</div>
  }

  if (!status.connected) {
    return (
      <div className="max-w-2xl mx-auto p-8 text-center">
        <h1 className="text-3xl font-bold mb-4">📬 Gmail Inbox</h1>
        <p className="text-gray-600 mb-6">
          Connect your Gmail account to start tracking job application emails with intelligent labeling.
        </p>
        <button
          onClick={initiateGmailAuth}
          className="bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-blue-700 transition"
        >
          🔐 Connect Gmail
        </button>
        <Card className="mt-8">
          <CardHeader>
            <CardTitle className="text-base">What happens when you connect:</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="list-disc ml-6 text-sm space-y-1">
              <li>Secure OAuth 2.0 authentication (read-only access)</li>
              <li>Automatic email labeling (interviews, offers, rejections)</li>
              <li>Full-text search with autocomplete</li>
              <li>Synonym matching for job search terms</li>
              <li>Your credentials are encrypted and never exposed</li>
            </ul>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="px-3 sm:px-4">
      <div className="pt-4">
        <div className="flex items-start justify-between mb-6">
          <div>
            <h1 className="flex items-center gap-3 text-2xl font-semibold tracking-tight">
              <span role="img" aria-label="inbox">📥</span>
              Gmail Inbox
            </h1>
            <p className="text-sm text-muted-foreground">
              Connected as <strong>{status.user_email}</strong>
            </p>
          </div>
        </div>

          {err && (
            <Alert variant={err.startsWith('✅') ? 'default' : 'destructive'} className="mb-4">
              {err.startsWith('✅') ? (
                <CheckCircle className="h-4 w-4" />
              ) : (
                <AlertCircle className="h-4 w-4" />
              )}
              <AlertDescription>{err}</AlertDescription>
            </Alert>
          )}

          {/* Label Filter Tabs */}
          <div className="flex gap-2 mb-4 overflow-x-auto">
            {LABEL_FILTERS.map(filter => (
              <button
                key={filter.value}
                onClick={() => {
                  setLabelFilter(filter.value)
                  setPage(1)
                }}
                className={`px-4 py-2 rounded whitespace-nowrap transition ${
                  labelFilter === filter.value
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-muted hover:bg-muted/70'
                }`}
              >
                {filter.label}
              </button>
            ))}
          </div>

          {/* Email Count */}
          <div className="mb-4 text-sm text-muted-foreground">
            Showing {emails.length} of {total} emails
            {labelFilter && ` (filtered by ${LABEL_FILTERS.find(f => f.value === labelFilter)?.label})`}
          </div>

          {/* Email List */}
          {loading ? (
            <div className="text-center py-8">Loading emails...</div>
          ) : emails.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              {labelFilter
                ? `No emails found with label "${labelFilter}". Try a different filter.`
                : 'No emails yet. Click "Sync Emails" to fetch from Gmail.'
              }
            </div>
          ) : (
            <div className="space-y-3">
              {emails.map(e => (
                <EmailCard key={e.id} e={e} />
              ))}
            </div>
          )}

          {/* Pagination */}
          {total > 50 && (
            <div className="mt-6 flex justify-center gap-2">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-4 py-2 bg-muted rounded disabled:opacity-50"
              >
                ← Previous
              </button>
              <span className="px-4 py-2">
                Page {page} of {Math.ceil(total / 50)}
              </span>
              <button
                onClick={() => setPage(p => p + 1)}
                disabled={page >= Math.ceil(total / 50)}
                className="px-4 py-2 bg-muted rounded disabled:opacity-50"
              >
                Next →
              </button>
            </div>
          )}
      </div>
    </div>
  )
}
