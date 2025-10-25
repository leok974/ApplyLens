import { useEffect, useState } from 'react'
import {
  fetchActionsInbox,
  explainMessage,
  fetchMessageDetail,
  postArchive,
  postMarkSafe,
  postMarkSuspicious,
  postUnsubscribe,
  ActionRow,
  MessageDetail,
} from '../lib/api'
import { safeFormatDate } from '../lib/date'
import { Alert, AlertDescription } from './ui/alert'
import { Badge } from './ui/badge'
import { Info } from 'lucide-react'
import { cn } from '../lib/utils'

// Helper: ActionButton component
function ActionButton({
  label,
  onClick,
  disabled,
  tone = 'default',
}: {
  label: string
  onClick: (e: React.MouseEvent) => void
  disabled?: boolean
  tone?: 'default' | 'success' | 'warn' | 'danger' | 'ghost'
}) {
  const base =
    'px-2 py-1 rounded text-[11px] border flex items-center gap-1 transition-colors disabled:opacity-50 disabled:cursor-not-allowed'
  const toneClass = {
    default: 'bg-muted/20 hover:bg-muted/30 border-border',
    success:
      'bg-emerald-600/20 text-emerald-200 border-emerald-700 hover:bg-emerald-600/30',
    warn: 'bg-amber-600/20 text-amber-200 border-amber-700 hover:bg-amber-600/30',
    danger:
      'bg-red-700/20 text-red-200 border-red-800 hover:bg-red-700/30',
    ghost:
      'bg-transparent border-border hover:bg-muted/20 text-foreground',
  }[tone]

  return (
    <button
      type="button"
      className={`${base} ${toneClass}`}
      disabled={disabled}
      onClick={onClick}
    >
      {label}
    </button>
  )
}

export default function InboxWithActions() {
  const [rows, setRows] = useState<ActionRow[]>([])
  const [loading, setLoading] = useState(false)
  const [rowLoading, setRowLoading] = useState<Record<string, boolean>>({})
  const [explanations, setExplanations] = useState<Record<string, string>>({})
  const [error, setError] = useState<string | null>(null)

  // Drawer state
  const [openMessageId, setOpenMessageId] = useState<string | null>(null)
  const [messageDetail, setMessageDetail] = useState<
    Record<string, MessageDetail>
  >({})
  const [detailLoading, setDetailLoading] = useState<boolean>(false)

  const loadInbox = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchActionsInbox()
      setRows(data)
    } catch (err) {
      setError('Failed to load inbox: ' + String(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadInbox()
  }, [])

  // Helper: set row busy state
  function setRowBusy(id: string, busy: boolean) {
    setRowLoading(prev => ({ ...prev, [id]: busy }))
  }

  // Handle opening message drawer
  const handleOpenMessage = async (message_id: string) => {
    setOpenMessageId(message_id)

    // Fetch detail if not already loaded
    if (!messageDetail[message_id]) {
      setDetailLoading(true)
      try {
        const detail = await fetchMessageDetail(message_id)
        setMessageDetail(prev => ({ ...prev, [message_id]: detail }))
      } catch (err) {
        setError('Failed to load message detail: ' + String(err))
      } finally {
        setDetailLoading(false)
      }
    }
  }

  // Handle explain action (toggle)
  const handleExplain = async (e: React.MouseEvent, row: ActionRow) => {
    e.stopPropagation()

    // If already showing, collapse it
    if (explanations[row.message_id]) {
      setExplanations(prev => {
        const copy = { ...prev }
        delete copy[row.message_id]
        return copy
      })
      return
    }

    try {
      const result = await explainMessage(row.message_id)
      setExplanations(prev => ({
        ...prev,
        [row.message_id]: result.summary,
      }))
    } catch (err) {
      setError('Explain failed: ' + String(err))
    }
  }

  // Handle archive action
  const handleArchive = async (e: React.MouseEvent, row: ActionRow) => {
    e.stopPropagation()
    setRowBusy(row.message_id, true)
    try {
      const res = await postArchive(row.message_id)
      if (res.ok) {
        setRows(prev => prev.filter(r => r.message_id !== row.message_id))
        if (openMessageId === row.message_id) setOpenMessageId(null)
      }
    } catch (err) {
      setError('Archive failed: ' + String(err))
    } finally {
      setRowBusy(row.message_id, false)
    }
  }

  // Handle mark safe action
  const handleMarkSafe = async (e: React.MouseEvent, row: ActionRow) => {
    e.stopPropagation()
    setRowBusy(row.message_id, true)
    try {
      const res = await postMarkSafe(row.message_id)
      if (res.ok) {
        setRows(prev =>
          prev.map(r => {
            if (r.message_id === row.message_id) {
              return {
                ...r,
                reason: {
                  ...r.reason,
                  risk_score: res.new_risk_score ?? r.reason.risk_score,
                  quarantined: false,
                  signals: ['Manually marked safe', ...r.reason.signals],
                },
              }
            }
            return r
          })
        )
      }
    } catch (err) {
      setError('Mark safe failed: ' + String(err))
    } finally {
      setRowBusy(row.message_id, false)
    }
  }

  // Handle mark suspicious action
  const handleMarkSuspicious = async (
    e: React.MouseEvent,
    row: ActionRow
  ) => {
    e.stopPropagation()
    setRowBusy(row.message_id, true)
    try {
      const res = await postMarkSuspicious(row.message_id)
      if (res.ok) {
        setRows(prev =>
          prev.map(r => {
            if (r.message_id === row.message_id) {
              return {
                ...r,
                reason: {
                  ...r.reason,
                  risk_score: res.new_risk_score ?? r.reason.risk_score,
                  quarantined: res.quarantined ?? true,
                  signals: [
                    'Flagged suspicious by user',
                    ...r.reason.signals,
                  ],
                },
              }
            }
            return r
          })
        )
      }
    } catch (err) {
      setError('Mark suspicious failed: ' + String(err))
    } finally {
      setRowBusy(row.message_id, false)
    }
  }

  // Handle unsubscribe action
  const handleUnsub = async (e: React.MouseEvent, row: ActionRow) => {
    e.stopPropagation()
    setRowBusy(row.message_id, true)
    try {
      const res = await postUnsubscribe(row.message_id)
      if (res.ok) {
        // treat unsubscribe same as archive: remove from actionable list
        setRows(prev => prev.filter(r => r.message_id !== row.message_id))
        if (openMessageId === row.message_id) setOpenMessageId(null)
      }
    } catch (err) {
      setError('Unsubscribe failed: ' + String(err))
    } finally {
      setRowBusy(row.message_id, false)
    }
  }

  // Render action buttons for a given message
  function renderActionButtonsFor(message_id: string | null) {
    if (!message_id) return null
    const row = rows.find(r => r.message_id === message_id)
    if (!row) return null

    const disabled = !!rowLoading[message_id]
    const allow = (action: string) => row.allowed_actions.includes(action)

    return (
      <>
        {allow('archive') && (
          <ActionButton
            label="Archive"
            onClick={e => handleArchive(e, row)}
            disabled={disabled}
            tone="default"
          />
        )}
        {allow('mark_safe') && (
          <ActionButton
            label="Safe"
            onClick={e => handleMarkSafe(e, row)}
            disabled={disabled}
            tone="success"
          />
        )}
        {allow('mark_suspicious') && (
          <ActionButton
            label="Suspicious"
            onClick={e => handleMarkSuspicious(e, row)}
            disabled={disabled}
            tone="warn"
          />
        )}
        {allow('unsubscribe') && (
          <ActionButton
            label="Unsub"
            onClick={e => handleUnsub(e, row)}
            disabled={disabled}
            tone="danger"
          />
        )}
        {allow('explain') && (
          <ActionButton
            label={
              explanations[message_id] ? 'Hide why' : 'Explain why'
            }
            onClick={e => handleExplain(e, row)}
            disabled={false}
            tone="ghost"
          />
        )}
      </>
    )
  }

  // Render detail pane
  function renderDetailPane() {
    if (!openMessageId) {
      return (
        <div className="text-sm text-muted-foreground border border-border rounded-lg p-4">
          Select an email to see details.
        </div>
      )
    }

    const detail = messageDetail[openMessageId]
    const loading = detailLoading && !detail

    return (
      <div className="border border-border rounded-lg bg-card text-card-foreground flex flex-col max-h-[80vh]">
        <div className="p-4 border-b border-border flex flex-col gap-2">
          <div className="text-sm font-semibold">Email Detail</div>
          {loading && (
            <div className="text-xs text-muted-foreground">Loading…</div>
          )}
          {!loading && detail && (
            <>
              <div className="text-xs text-muted-foreground space-y-1">
                <div>
                  <span className="font-medium">From:</span>{' '}
                  {detail.from_name} &lt;{detail.from_email}&gt;
                </div>
                <div>
                  <span className="font-medium">To:</span> {detail.to_email}
                </div>
                <div>
                  <span className="font-medium">Subject:</span>{' '}
                  {detail.subject}
                </div>
                <div>
                  <span className="font-medium">Date:</span>{' '}
                  {safeFormatDate(detail.received_at)}
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-2 text-[10px]">
                {detail.category && (
                  <Badge variant="secondary">{detail.category}</Badge>
                )}
                {typeof detail.risk_score === 'number' && (
                  <Badge variant="outline">Risk: {detail.risk_score}</Badge>
                )}
                {detail.quarantined && (
                  <Badge variant="destructive">Quarantined</Badge>
                )}
              </div>
            </>
          )}
        </div>

        <div className="flex-1 overflow-y-auto p-4 text-xs leading-relaxed bg-background/40">
          {loading && (
            <div className="text-muted-foreground">Loading…</div>
          )}
          {!loading && detail && (
            <>
              {detail.html_body ? (
                <div
                  className="prose prose-invert max-w-none text-sm"
                  dangerouslySetInnerHTML={{ __html: detail.html_body }}
                />
              ) : (
                <pre className="whitespace-pre-wrap text-sm bg-muted/10 p-3 rounded border border-border">
                  {detail.text_body}
                </pre>
              )}
            </>
          )}
        </div>

        <div className="p-4 border-t border-border flex flex-wrap gap-2 text-xs">
          {renderActionButtonsFor(openMessageId)}
        </div>
      </div>
    )
  }

  return (
    <div className="p-4 md:p-6 max-w-[1600px] mx-auto">
      <header className="mb-6">
        <h1 className="text-3xl font-bold mb-2">📧 Inbox Actions</h1>
        <p className="text-sm text-muted-foreground">
          Take quick actions on promotional and bulk emails
        </p>
      </header>

      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {loading && rows.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          Loading inbox...
        </div>
      ) : rows.length === 0 ? (
        <Alert className="max-w-md">
          <Info className="h-4 w-4" />
          <AlertDescription>
            No actionable emails found. All clean! 🎉
          </AlertDescription>
        </Alert>
      ) : (
        <div className="flex gap-4">
          {/* Left: Table */}
          <div className="flex-1 min-w-0">
            <div className="rounded-lg border border-border bg-card overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-muted/50 border-b border-border">
                  <tr>
                    <th className="px-4 py-2 text-left font-medium">From</th>
                    <th className="px-4 py-2 text-left font-medium">
                      Subject
                    </th>
                    <th className="px-4 py-2 text-left font-medium">
                      Received
                    </th>
                    <th className="px-4 py-2 text-left font-medium">
                      Reason
                    </th>
                    <th className="px-4 py-2 text-left font-medium">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map(row => (
                    <>
                      <tr
                        key={row.message_id}
                        onClick={() => handleOpenMessage(row.message_id)}
                        className={cn(
                          'cursor-pointer hover:bg-muted/20 border-b border-border',
                          openMessageId === row.message_id &&
                            'bg-muted/30 ring-1 ring-border'
                        )}
                      >
                        <td className="px-4 py-3">{row.from_name}</td>
                        <td className="px-4 py-3">{row.subject}</td>
                        <td className="px-4 py-3 text-muted-foreground">
                          {safeFormatDate(row.received_at)}
                        </td>
                        <td className="px-4 py-3">
                          <div className="text-xs space-y-1">
                            <div className="font-medium">
                              {row.reason.category}
                            </div>
                            <div className="text-muted-foreground">
                              Risk: {row.reason.risk_score}/100
                              {row.reason.quarantined && (
                                <span className="ml-2 text-red-400">
                                  🔒 Quarantined
                                </span>
                              )}
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex flex-wrap gap-1">
                            {renderActionButtonsFor(row.message_id)}
                          </div>
                        </td>
                      </tr>
                      {explanations[row.message_id] && (
                        <tr className="bg-muted/10">
                          <td
                            colSpan={5}
                            className="px-4 py-3 border-b border-border"
                          >
                            <div className="text-xs rounded-md border border-border bg-background/60 p-3 leading-relaxed">
                              {explanations[row.message_id]}
                            </div>
                          </td>
                        </tr>
                      )}
                    </>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="mt-2 text-xs text-muted-foreground">
              {rows.length} actionable email{rows.length !== 1 ? 's' : ''}
            </div>
          </div>

          {/* Right: Detail pane */}
          <aside className="w-[380px] shrink-0">{renderDetailPane()}</aside>
        </div>
      )}
    </div>
  )
}
